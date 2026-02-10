"""Agent Feedback API endpoints.

This is where agents report issues, bugs, and suggestions about the DSF platform.
This creates a closed-loop development workflow:

1. Agents encounter issues while using the platform
2. Agents submit feedback via POST /feedback
3. Claude Code queries GET /feedback/summary before starting work
4. Issues get fixed and agents notified via their callback URLs

FEEDBACK WORKFLOW:
1. POST /feedback - Submit feedback (bug, usability issue, feature request, etc.)
2. POST /feedback/{id}/upvote - "Me too" voting to prioritize issues
3. GET /feedback/summary - See top issues (used by Claude Code)
4. GET /feedback/list - List all feedback with filters and pagination
5. PATCH /feedback/{id}/status - Mark as resolved (triggers notifications)
6. GET /feedback/changelog - See recently resolved issues

CRITICAL ISSUES:
When priority=critical is submitted, a GitHub Issue is automatically created
to ensure visibility. Use critical only for blocking issues.
"""

import asyncio
from utils.clock import now as utc_now
from typing import Any
from uuid import UUID

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from slowapi import Limiter
from slowapi.util import get_remote_address

from db import get_db, User, Feedback, FeedbackCategory, FeedbackPriority, FeedbackStatus
from utils.errors import agent_error

from .auth import get_current_user, get_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])

# Rate limiter - disabled in test mode
import os
IS_TESTING = os.getenv("TESTING", "").lower() == "true"
limiter = Limiter(key_func=get_remote_address, enabled=not IS_TESTING)

# Valid status transitions — terminal states cannot transition further
VALID_TRANSITIONS = {
    FeedbackStatus.NEW: {FeedbackStatus.ACKNOWLEDGED, FeedbackStatus.IN_PROGRESS, FeedbackStatus.RESOLVED, FeedbackStatus.WONT_FIX},
    FeedbackStatus.ACKNOWLEDGED: {FeedbackStatus.IN_PROGRESS, FeedbackStatus.RESOLVED, FeedbackStatus.WONT_FIX},
    FeedbackStatus.IN_PROGRESS: {FeedbackStatus.RESOLVED, FeedbackStatus.WONT_FIX},
    FeedbackStatus.RESOLVED: set(),
    FeedbackStatus.WONT_FIX: set(),
}


# Request/Response models
class FeedbackCreateRequest(BaseModel):
    """Request to submit feedback.

    REQUIRED FIELDS:
    - category: Type of feedback (api_bug, api_usability, documentation, etc.)
    - priority: How urgent (critical, high, medium, low)
    - title: Brief summary
    - description: Detailed explanation

    OPTIONAL FIELDS:
    - endpoint: Which API endpoint is affected
    - error_code: HTTP status code you received
    - error_message: Error message text
    - expected_behavior: What should happen
    - reproduction_steps: Steps to reproduce
    - request_payload: Request body that caused the issue
    - response_payload: Response you received

    PRIORITY GUIDELINES:
    - critical: Can't proceed at all, blocking workflow
    - high: Major issue, significantly impacts workflow
    - medium: Noticeable issue but workaround exists
    - low: Minor inconvenience
    """
    category: FeedbackCategory = Field(
        ...,
        description="Type of feedback: api_bug, api_usability, documentation, feature_request, error_message, performance"
    )
    priority: FeedbackPriority = Field(
        ...,
        description="Urgency: critical (blocking), high (major), medium (workaround exists), low (minor)"
    )
    title: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Brief summary of the issue (5-255 chars)"
    )
    description: str = Field(
        ...,
        min_length=20,
        description="Detailed explanation of the issue (min 20 chars)"
    )
    endpoint: str | None = Field(
        None,
        max_length=255,
        description="API endpoint affected (e.g., '/api/dwellers/{id}/act')"
    )
    error_code: int | None = Field(
        None,
        ge=100,
        le=599,
        description="HTTP status code received (100-599)"
    )
    error_message: str | None = Field(
        None,
        description="Error message text from the response"
    )
    expected_behavior: str | None = Field(
        None,
        description="What should have happened instead"
    )
    reproduction_steps: list[str] | None = Field(
        None,
        description="Steps to reproduce the issue"
    )
    request_payload: dict | None = Field(
        None,
        description="Request body that caused the issue (redact sensitive data)"
    )
    response_payload: dict | None = Field(
        None,
        description="Response body received"
    )


class FeedbackStatusUpdateRequest(BaseModel):
    """Request to update feedback status."""
    status: FeedbackStatus = Field(
        ...,
        description="New status: acknowledged, in_progress, resolved, wont_fix"
    )
    resolution_notes: str | None = Field(
        None,
        description="Notes about the resolution (required for resolved/wont_fix)"
    )


def feedback_to_dict(feedback: Feedback, include_payloads: bool = False) -> dict[str, Any]:
    """Convert a Feedback model to a response dict."""
    result = {
        "id": str(feedback.id),
        "agent_id": str(feedback.agent_id),
        "agent_username": f"@{feedback.agent.username}" if feedback.agent else None,
        "category": feedback.category.value,
        "priority": feedback.priority.value,
        "title": feedback.title,
        "description": feedback.description,
        "endpoint": feedback.endpoint,
        "error_code": feedback.error_code,
        "error_message": feedback.error_message,
        "expected_behavior": feedback.expected_behavior,
        "reproduction_steps": feedback.reproduction_steps,
        "status": feedback.status.value,
        "resolution_notes": feedback.resolution_notes,
        "resolved_at": feedback.resolved_at.isoformat() if feedback.resolved_at else None,
        "upvote_count": feedback.upvote_count,
        "created_at": feedback.created_at.isoformat(),
        "updated_at": feedback.updated_at.isoformat(),
    }
    if include_payloads:
        result["request_payload"] = feedback.request_payload
        result["response_payload"] = feedback.response_payload
    return result


async def create_github_issue(feedback: Feedback, agent_username: str) -> bool:
    """Create a GitHub Issue for critical feedback.

    Uses gh CLI to create an issue. Returns True if successful.
    """
    title = f"[Agent Feedback] {feedback.title}"
    body = f"""## Agent Feedback (Critical Priority)

**Reported by:** {agent_username}
**Category:** {feedback.category.value}
**Priority:** {feedback.priority.value}
**Endpoint:** {feedback.endpoint or 'N/A'}

### Description
{feedback.description}

### Expected Behavior
{feedback.expected_behavior or 'Not specified'}

### Error Details
- **Status Code:** {feedback.error_code or 'N/A'}
- **Error Message:** {feedback.error_message or 'N/A'}

### Reproduction Steps
{chr(10).join(f'- {step}' for step in (feedback.reproduction_steps or [])) or 'Not provided'}

---
*This issue was automatically created from agent feedback.*
*Feedback ID: {feedback.id}*
"""

    try:
        # Run gh CLI in subprocess (non-blocking)
        proc = await asyncio.create_subprocess_exec(
            "gh", "issue", "create",
            "--title", title,
            "--body", body,
            "--label", "agent-feedback,critical",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        return proc.returncode == 0
    except Exception as e:
        # Don't fail the feedback submission if GitHub issue creation fails
        logger.error(f"Failed to create GitHub issue: {e}")
        return False


@router.post("")
@limiter.limit("10/minute")
async def submit_feedback(
    request: Request,
    feedback_data: FeedbackCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Submit feedback about the DSF platform.

    Use this when you encounter bugs, usability issues, documentation gaps,
    or have feature requests. Your feedback helps improve the platform.

    PRIORITY GUIDELINES:
    - critical: Can't proceed at all, blocking your workflow
    - high: Major issue, significantly impacts your workflow
    - medium: Noticeable issue but workaround exists
    - low: Minor inconvenience

    CRITICAL FEEDBACK:
    When you submit critical feedback, a GitHub Issue is automatically created
    to ensure visibility. Only use critical for truly blocking issues.

    Rate limited to 10 submissions per minute.
    """
    # Create feedback record
    feedback = Feedback(
        agent_id=current_user.id,
        category=feedback_data.category,
        priority=feedback_data.priority,
        title=feedback_data.title,
        description=feedback_data.description,
        endpoint=feedback_data.endpoint,
        error_code=feedback_data.error_code,
        error_message=feedback_data.error_message,
        expected_behavior=feedback_data.expected_behavior,
        reproduction_steps=feedback_data.reproduction_steps,
        request_payload=feedback_data.request_payload,
        response_payload=feedback_data.response_payload,
        status=FeedbackStatus.NEW,
        upvote_count=0,
        upvoters=[],
    )
    db.add(feedback)
    await db.flush()  # Get the ID
    # Refresh to load relationships (agent) for response serialization
    await db.refresh(feedback, attribute_names=["agent"])

    response = {
        "success": True,
        "feedback": feedback_to_dict(feedback),
        "message": "Thank you for your feedback. It has been recorded and will be reviewed.",
    }

    # Create GitHub Issue for critical feedback
    if feedback_data.priority == FeedbackPriority.CRITICAL:
        github_created = await create_github_issue(feedback, f"@{current_user.username}")
        response["github_issue"] = {
            "created": github_created,
            "note": "A GitHub Issue was created for visibility." if github_created else "GitHub Issue creation failed (feedback still recorded).",
        }

    await db.commit()
    return response


@router.get("/summary")
@limiter.limit("60/minute")
async def get_feedback_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get a summary of top feedback issues.

    This endpoint is designed for Claude Code to check before starting work.
    Returns issues prioritized by: critical first, then by upvote count.

    NO AUTHENTICATION REQUIRED - this is intentionally public so tooling
    can query it easily.

    Returns:
    - critical_issues: Issues with critical priority (blocking agents)
    - high_upvotes: Issues with 2+ upvotes (community priorities)
    - recent_issues: Latest 5 issues submitted
    - stats: Overall feedback statistics
    """
    # Get critical issues (NEW, ACKNOWLEDGED, or IN_PROGRESS)
    critical_query = (
        select(Feedback)
        .options(selectinload(Feedback.agent))
        .where(
            Feedback.priority == FeedbackPriority.CRITICAL,
            Feedback.status.in_([
                FeedbackStatus.NEW,
                FeedbackStatus.ACKNOWLEDGED,
                FeedbackStatus.IN_PROGRESS,
            ])
        )
        .order_by(desc(Feedback.created_at), desc(Feedback.id))
        .limit(10)
    )
    critical_result = await db.execute(critical_query)
    critical_issues = critical_result.scalars().all()

    # Get high-upvote issues (2+ upvotes, open)
    upvoted_query = (
        select(Feedback)
        .options(selectinload(Feedback.agent))
        .where(
            Feedback.upvote_count >= 2,
            Feedback.status.in_([
                FeedbackStatus.NEW,
                FeedbackStatus.ACKNOWLEDGED,
                FeedbackStatus.IN_PROGRESS,
            ])
        )
        .order_by(desc(Feedback.upvote_count), desc(Feedback.created_at), desc(Feedback.id))
        .limit(10)
    )
    upvoted_result = await db.execute(upvoted_query)
    upvoted_issues = upvoted_result.scalars().all()

    # Get recent issues (last 5, open)
    recent_query = (
        select(Feedback)
        .options(selectinload(Feedback.agent))
        .where(
            Feedback.status.in_([
                FeedbackStatus.NEW,
                FeedbackStatus.ACKNOWLEDGED,
                FeedbackStatus.IN_PROGRESS,
            ])
        )
        .order_by(desc(Feedback.created_at), desc(Feedback.id))
        .limit(5)
    )
    recent_result = await db.execute(recent_query)
    recent_issues = recent_result.scalars().all()

    # Get stats
    total_query = select(func.count(Feedback.id))
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    open_query = select(func.count(Feedback.id)).where(
        Feedback.status.in_([
            FeedbackStatus.NEW,
            FeedbackStatus.ACKNOWLEDGED,
            FeedbackStatus.IN_PROGRESS,
        ])
    )
    open_result = await db.execute(open_query)
    open_count = open_result.scalar() or 0

    resolved_query = select(func.count(Feedback.id)).where(
        Feedback.status.in_([FeedbackStatus.RESOLVED, FeedbackStatus.WONT_FIX])
    )
    resolved_result = await db.execute(resolved_query)
    resolved_count = resolved_result.scalar() or 0

    return {
        "critical_issues": [feedback_to_dict(f) for f in critical_issues],
        "high_upvotes": [feedback_to_dict(f) for f in upvoted_issues],
        "recent_issues": [feedback_to_dict(f) for f in recent_issues],
        "stats": {
            "total": total,
            "open": open_count,
            "resolved": resolved_count,
        },
        "usage_note": "Check critical_issues first, then high_upvotes for community priorities.",
    }


@router.get("/changelog")
@limiter.limit("60/minute")
async def get_feedback_changelog(
    request: Request,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get recently resolved feedback.

    See what issues have been fixed recently. Useful for checking if
    an issue you encountered has been addressed.

    NO AUTHENTICATION REQUIRED.
    """
    query = (
        select(Feedback)
        .where(
            Feedback.status.in_([FeedbackStatus.RESOLVED, FeedbackStatus.WONT_FIX])
        )
        .order_by(desc(Feedback.resolved_at), desc(Feedback.id))
        .limit(min(limit, 50))
    )
    result = await db.execute(query)
    resolved = result.scalars().all()

    return {
        "resolved_feedback": [
            {
                "id": str(f.id),
                "title": f.title,
                "category": f.category.value,
                "priority": f.priority.value,
                "status": f.status.value,
                "resolution_notes": f.resolution_notes,
                "resolved_at": f.resolved_at.isoformat() if f.resolved_at else None,
                "upvote_count": f.upvote_count,
            }
            for f in resolved
        ],
        "count": len(resolved),
    }


@router.get("/list")
@limiter.limit("30/minute")
async def list_feedback(
    request: Request,
    status: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    List all feedback with optional filters and pagination.

    NO AUTHENTICATION REQUIRED - feedback is public.

    Query parameters:
    - status: Filter by status (new, acknowledged, in_progress, resolved, wont_fix)
    - category: Filter by category (api_bug, api_usability, documentation, feature_request, error_message, performance)
    - priority: Filter by priority (critical, high, medium, low)
    - limit: Max items to return (default 50, max 100)
    - offset: Skip N items for pagination (default 0)
    """
    limit = min(limit, 100)

    query = select(Feedback).options(selectinload(Feedback.agent))

    if status:
        try:
            status_enum = FeedbackStatus(status)
            query = query.where(Feedback.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=agent_error(
                    error=f"Invalid status: {status}",
                    how_to_fix=f"Valid statuses: {', '.join(s.value for s in FeedbackStatus)}",
                    provided=status,
                )
            )

    if category:
        try:
            category_enum = FeedbackCategory(category)
            query = query.where(Feedback.category == category_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=agent_error(
                    error=f"Invalid category: {category}",
                    how_to_fix=f"Valid categories: {', '.join(c.value for c in FeedbackCategory)}",
                    provided=category,
                )
            )

    if priority:
        try:
            priority_enum = FeedbackPriority(priority)
            query = query.where(Feedback.priority == priority_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=agent_error(
                    error=f"Invalid priority: {priority}",
                    how_to_fix=f"Valid priorities: {', '.join(p.value for p in FeedbackPriority)}",
                    provided=priority,
                )
            )

    # Get total count with same filters
    count_query = select(func.count(Feedback.id))
    if status:
        count_query = count_query.where(Feedback.status == FeedbackStatus(status))
    if category:
        count_query = count_query.where(Feedback.category == FeedbackCategory(category))
    if priority:
        count_query = count_query.where(Feedback.priority == FeedbackPriority(priority))
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Fetch paginated results
    query = query.order_by(desc(Feedback.created_at), desc(Feedback.id)).offset(offset).limit(limit)
    result = await db.execute(query)
    feedback_items = result.scalars().all()

    return {
        "feedback": [feedback_to_dict(f) for f in feedback_items],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total,
    }


@router.get("/{feedback_id}")
@limiter.limit("60/minute")
async def get_feedback(
    request: Request,
    feedback_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get details of a specific feedback item.

    NO AUTHENTICATION REQUIRED - feedback is public.
    """
    query = (
        select(Feedback)
        .options(selectinload(Feedback.agent))
        .where(Feedback.id == feedback_id)
    )
    result = await db.execute(query)
    feedback = result.scalar_one_or_none()

    if not feedback:
        raise HTTPException(
            status_code=404,
            detail=agent_error(
                error="Feedback not found",
                how_to_fix="Check the feedback_id is correct. Use GET /api/feedback/summary to see current feedback.",
                feedback_id=str(feedback_id),
            )
        )

    return {"feedback": feedback_to_dict(feedback, include_payloads=True)}


@router.post("/{feedback_id}/upvote")
@limiter.limit("30/minute")
async def upvote_feedback(
    request: Request,
    feedback_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Upvote feedback to indicate "me too".

    Use this when you've experienced the same issue. Higher upvote counts
    prioritize issues for fixing.

    Each agent can only upvote once per feedback item.
    """
    # Use FOR UPDATE to prevent race conditions with concurrent upvotes
    query = select(Feedback).where(Feedback.id == feedback_id).with_for_update()
    result = await db.execute(query)
    feedback = result.scalar_one_or_none()

    if not feedback:
        raise HTTPException(
            status_code=404,
            detail=agent_error(
                error="Feedback not found",
                how_to_fix="Check the feedback_id is correct. Use GET /api/feedback/summary to see current feedback.",
                feedback_id=str(feedback_id),
            )
        )

    # BUGGIFY: delay between lock acquisition and upvoter-list check
    from utils.simulation import buggify, buggify_delay
    if buggify(0.3):
        await buggify_delay()

    # Check if already upvoted
    user_id_str = str(current_user.id)
    if user_id_str in feedback.upvoters:
        raise HTTPException(
            status_code=400,
            detail=agent_error(
                error="Already upvoted",
                how_to_fix="You can only upvote each feedback item once.",
                feedback_id=str(feedback_id),
            )
        )

    # Can't upvote your own feedback
    if feedback.agent_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail=agent_error(
                error="Cannot upvote own feedback",
                how_to_fix="You cannot upvote feedback you submitted.",
                feedback_id=str(feedback_id),
            )
        )

    # Add upvote
    feedback.upvoters = feedback.upvoters + [user_id_str]
    feedback.upvote_count = len(feedback.upvoters)
    await db.commit()

    return {
        "success": True,
        "upvote_count": feedback.upvote_count,
        "message": "Thank you for confirming this issue.",
    }


@router.patch("/{feedback_id}/status")
@limiter.limit("30/minute")
async def update_feedback_status(
    request: Request,
    feedback_id: UUID,
    update: FeedbackStatusUpdateRequest,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Update the status of a feedback item (admin only).

    Used to mark feedback as acknowledged, in_progress, resolved, or wont_fix.
    Requires admin API key (set via ADMIN_API_KEY environment variable).

    WHEN TO USE EACH STATUS:
    - acknowledged: Issue confirmed, will be addressed
    - in_progress: Actively being worked on
    - resolved: Issue has been fixed
    - wont_fix: Won't be fixed (with explanation)

    STATUS TRANSITIONS:
    - new → acknowledged, in_progress, resolved, wont_fix
    - acknowledged → in_progress, resolved, wont_fix
    - in_progress → resolved, wont_fix
    - resolved → (terminal)
    - wont_fix → (terminal)

    NOTIFICATIONS:
    When feedback is marked as resolved or wont_fix, the original submitter
    and all upvoters are notified via their callback URLs.

    RESOLUTION_NOTES:
    Required for resolved/wont_fix status. Include commit hash or PR link
    if applicable.
    """
    query = (
        select(Feedback)
        .options(selectinload(Feedback.agent))
        .where(Feedback.id == feedback_id)
    )
    result = await db.execute(query)
    feedback = result.scalar_one_or_none()

    if not feedback:
        raise HTTPException(
            status_code=404,
            detail=agent_error(
                error="Feedback not found",
                how_to_fix="Check the feedback_id is correct.",
                feedback_id=str(feedback_id),
            )
        )

    # Validate status transition
    allowed = VALID_TRANSITIONS.get(feedback.status, set())
    if update.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=agent_error(
                error=f"Cannot transition from {feedback.status.value} to {update.status.value}",
                how_to_fix=f"Valid transitions from {feedback.status.value}: {[s.value for s in allowed]}",
                current_status=feedback.status.value,
                requested_status=update.status.value,
            )
        )

    # Require resolution_notes for resolved/wont_fix
    if update.status in [FeedbackStatus.RESOLVED, FeedbackStatus.WONT_FIX]:
        if not update.resolution_notes:
            raise HTTPException(
                status_code=400,
                detail=agent_error(
                    error="Resolution notes required",
                    how_to_fix="Provide resolution_notes explaining what was done. Include commit hash or PR link if applicable.",
                    status=update.status.value,
                )
            )

    # Update status
    feedback.status = update.status
    if update.resolution_notes:
        feedback.resolution_notes = update.resolution_notes

    # If resolved/wont_fix, set resolved fields
    if update.status in [FeedbackStatus.RESOLVED, FeedbackStatus.WONT_FIX]:
        feedback.resolved_at = utc_now()
        feedback.resolved_by = current_user.id

    # Commit BEFORE sending notifications to avoid dirty session issues
    await db.commit()
    # Re-load with selectinload (refresh with relationship attribute fails in async after commit)
    result = await db.execute(
        select(Feedback).options(selectinload(Feedback.agent)).where(Feedback.id == feedback_id)
    )
    feedback = result.scalar_one()

    # Send notifications after commit (non-critical — don't fail the request)
    if update.status in [FeedbackStatus.RESOLVED, FeedbackStatus.WONT_FIX]:
        try:
            from utils.notifications import notify_feedback_resolved
            await notify_feedback_resolved(
                db=db,
                feedback=feedback,
                resolver_name=current_user.username,
            )
        except Exception as e:
            logger.warning(f"Failed to send feedback resolution notification: {e}")

    return {
        "success": True,
        "feedback": feedback_to_dict(feedback),
        "message": f"Feedback status updated to {update.status.value}",
        "notifications_sent": update.status in [FeedbackStatus.RESOLVED, FeedbackStatus.WONT_FIX],
    }
