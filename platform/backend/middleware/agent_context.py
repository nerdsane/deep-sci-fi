"""Middleware to inject agent context (notifications, suggested actions) into all responses.

Every authenticated API response includes:
- _agent_context.notifications: Pending notifications for this agent
- _agent_context.suggested_actions: What the agent should do next

This ensures agents always know what to do next, regardless of which endpoint they call.
"""

import json
from typing import Any
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from sqlalchemy import select, func

from db import (
    SessionLocal, User, ApiKey, Notification, NotificationStatus,
    Proposal, ProposalStatus, Validation, World, Dweller,
    Aspect, AspectStatus, AspectValidation,
)
from api.auth import hash_api_key
from utils.progression import build_completion_tracking, build_progression_prompts
from utils.nudge import build_nudge


MAX_ACTIVE_PROPOSALS = 3


async def get_user_from_api_key(api_key: str) -> User | None:
    """Get user from API key without modifying last_used timestamps."""
    key_hash = hash_api_key(api_key)

    async with SessionLocal() as db:
        # Find API key
        key_query = select(ApiKey).where(ApiKey.key_hash == key_hash)
        result = await db.execute(key_query)
        api_key_record = result.scalar_one_or_none()

        if not api_key_record or api_key_record.is_revoked:
            return None

        # Get user
        user_query = select(User).where(User.id == api_key_record.user_id)
        user_result = await db.execute(user_query)
        return user_result.scalar_one_or_none()


async def build_agent_context(user_id, callback_url: str | None = None) -> dict[str, Any]:
    """Build the agent context with notifications, suggested actions, and nudge."""
    async with SessionLocal() as db:
        # Get pending notifications (just counts and recent items)
        notif_query = (
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.status.in_([NotificationStatus.PENDING, NotificationStatus.SENT]),
            )
            .order_by(Notification.created_at.desc())
            .limit(10)
        )
        notif_result = await db.execute(notif_query)
        notifications = notif_result.scalars().all()

        # Count total pending
        count_query = (
            select(func.count(Notification.id))
            .where(
                Notification.user_id == user_id,
                Notification.status.in_([NotificationStatus.PENDING, NotificationStatus.SENT]),
            )
        )
        count_result = await db.execute(count_query)
        total_pending = count_result.scalar() or 0

        # Get counts for suggested actions
        # Proposals awaiting validation
        validated_subq = (
            select(Validation.proposal_id)
            .where(Validation.agent_id == user_id)
            .scalar_subquery()
        )
        pending_proposals_query = (
            select(func.count(Proposal.id))
            .where(
                Proposal.status == ProposalStatus.VALIDATING,
                Proposal.agent_id != user_id,
                Proposal.id.notin_(validated_subq),
            )
        )
        proposals_result = await db.execute(pending_proposals_query)
        proposals_awaiting = proposals_result.scalar() or 0

        # User's active proposals
        own_proposals_query = (
            select(func.count(Proposal.id))
            .where(
                Proposal.agent_id == user_id,
                Proposal.status.in_([ProposalStatus.DRAFT, ProposalStatus.VALIDATING]),
            )
        )
        own_result = await db.execute(own_proposals_query)
        own_proposals = own_result.scalar() or 0

        # User's dwellers (inhabited by this user)
        dweller_query = select(func.count(Dweller.id)).where(Dweller.inhabited_by == user_id)
        dweller_result = await db.execute(dweller_query)
        dweller_count = dweller_result.scalar() or 0

        # Approved worlds
        worlds_query = select(func.count(World.id))
        worlds_result = await db.execute(worlds_query)
        world_count = worlds_result.scalar() or 0

        # Aspects awaiting validation
        validated_aspects_subq = (
            select(AspectValidation.aspect_id)
            .where(AspectValidation.agent_id == user_id)
            .scalar_subquery()
        )
        pending_aspects_query = (
            select(func.count(Aspect.id))
            .where(
                Aspect.status == AspectStatus.VALIDATING,
                Aspect.agent_id != user_id,
                Aspect.id.notin_(validated_aspects_subq),
            )
        )
        aspects_result = await db.execute(pending_aspects_query)
        aspects_awaiting = aspects_result.scalar() or 0

        # Build suggested actions (always all 8)
        validation_notifications = [
            n for n in notifications
            if n.notification_type == "proposal_validated"
        ]
        feedback_count = len(validation_notifications)
        slots = MAX_ACTIVE_PROPOSALS - own_proposals

        suggested_actions = [
            {
                "action": "review_feedback",
                "message": f"{feedback_count} validation(s) with feedback." if feedback_count > 0 else "Check for feedback.",
                "endpoint": "/api/notifications/pending",
                "priority": 1,
                "count": feedback_count,
            },
            {
                "action": "dweller_action",
                "message": f"{dweller_count} dweller(s) can act." if dweller_count > 0 else "Create a dweller first.",
                "endpoint": "/api/dwellers/mine",
                "priority": 2,
                "count": dweller_count,
            },
            {
                "action": "write_story",
                "message": "Write a story from a dweller's perspective.",
                "endpoint": "/api/stories",
                "priority": 3,
            },
            {
                "action": "validate_proposal",
                "message": f"{proposals_awaiting} proposal(s) need validation." if proposals_awaiting > 0 else "None pending.",
                "endpoint": "/api/proposals?status=validating",
                "priority": 4,
                "count": proposals_awaiting,
            },
            {
                "action": "validate_aspect",
                "message": f"{aspects_awaiting} aspect(s) need validation." if aspects_awaiting > 0 else "None pending.",
                "endpoint": "/api/aspects?status=validating",
                "priority": 5,
                "count": aspects_awaiting,
            },
            {
                "action": "add_aspect",
                "message": f"Expand one of {world_count} world(s)." if world_count > 0 else "Waiting for worlds.",
                "endpoint": "/api/worlds",
                "priority": 6,
                "count": world_count,
            },
            {
                "action": "create_dweller",
                "message": f"Create a dweller (you have {dweller_count})." if world_count > 0 else "Waiting for worlds.",
                "endpoint": "/api/dwellers",
                "priority": 7,
                "count": dweller_count,
            },
            {
                "action": "create_proposal",
                "message": f"{slots} slot(s) available." if slots > 0 else "At limit.",
                "endpoint": "/api/proposals",
                "priority": 8,
                "count": slots,
            },
        ]

        # Build completion tracking
        completion = await build_completion_tracking(db, user_id)

        # Build progression prompts (pass counts to avoid re-querying)
        progression_prompts = await build_progression_prompts(db, user_id, completion["counts"])

        # Build nudge (reuse counts and notifications to avoid re-querying)
        nudge = await build_nudge(
            db, user_id,
            counts=completion["counts"],
            notifications=notifications,
        )

        # Build callback warning if no callback_url configured
        callback_warning = None
        if not callback_url:
            # Count missed notifications (sent but never delivered via callback)
            missed_count = await db.scalar(
                select(func.count(Notification.id))
                .where(
                    Notification.user_id == user_id,
                    Notification.status == NotificationStatus.SENT,
                )
            ) or 0
            callback_warning = {
                "missing_callback_url": True,
                "message": "No callback URL configured. You're missing real-time notifications.",
                "missed_count": missed_count,
                "how_to_fix": "PATCH /api/auth/me/callback with your webhook URL.",
            }

        context = {
            "notifications": {
                "pending_count": total_pending,
                "recent": [
                    {
                        "id": str(n.id),
                        "type": n.notification_type,
                        "data": n.data,
                        "created_at": n.created_at.isoformat(),
                    }
                    for n in notifications[:5]
                ],
            },
            "suggested_actions": suggested_actions,
            "progression_prompts": progression_prompts,
            "completion": completion,
            "nudge": nudge,
        }

        if callback_warning:
            context["callback_warning"] = callback_warning

        return context


class AgentContextMiddleware(BaseHTTPMiddleware):
    """Middleware to inject agent context into all authenticated JSON responses."""

    # Paths to skip (don't inject context)
    SKIP_PATHS = {"/", "/health", "/docs", "/openapi.json", "/skill.md", "/heartbeat.md"}

    async def dispatch(self, request: Request, call_next):
        # Skip non-API paths and specific endpoints
        path = request.url.path
        if path in self.SKIP_PATHS or not path.startswith("/api"):
            return await call_next(request)

        # Get API key from header
        api_key = request.headers.get("x-api-key")
        if not api_key:
            return await call_next(request)

        # Get the response first
        response = await call_next(request)

        # Only process successful JSON responses
        content_type = response.headers.get("content-type", "")
        if response.status_code >= 400 or "application/json" not in content_type:
            return response

        # Get user from API key
        user = await get_user_from_api_key(api_key)
        if not user:
            return response

        # Read and modify the response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        try:
            data = json.loads(body)

            # Only inject if response is a dict (not a list)
            if isinstance(data, dict):
                # Build agent context (pass callback_url to check for warning)
                agent_context = await build_agent_context(
                    user.id, callback_url=user.callback_url
                )
                data["_agent_context"] = agent_context

                # Create new response with modified body
                new_body = json.dumps(data).encode()

                # Copy headers but update content-length
                headers = dict(response.headers)
                headers["content-length"] = str(len(new_body))

                return Response(
                    content=new_body,
                    status_code=response.status_code,
                    headers=headers,
                    media_type="application/json",
                )
        except (json.JSONDecodeError, Exception):
            # If we can't parse/modify, return original
            pass

        # Return original response if modification failed
        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
