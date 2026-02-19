"""Critical Review System API endpoints.

This implements the feedback-first review system that replaces vote-based validation.
Reviewers submit specific feedback items. Proposers address each one. Reviewers confirm
resolution. Content graduates when all feedback is resolved by all reviewers (min 2 reviewers).

Key features:
- Blind mode: reviewers can't see others' feedback until they submit their own
- Graduation gate: 2+ reviewers AND all items resolved
- Reviewers can add new feedback after seeing revisions
- Only the original reviewer can resolve their own feedback items
"""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import logging

from db import (
    get_db,
    User,
    World,
    ReviewFeedback,
    FeedbackItem,
    FeedbackResponse,
    ReviewFeedbackCategory,
    FeedbackSeverity,
    FeedbackItemStatus,
    Proposal,
    ProposalStatus,
    MediaGeneration,
    MediaType,
    Aspect,
    DwellerProposal,
    Story,
)
from .auth import get_current_user, get_optional_user
from utils.rate_limit import limiter_auth
from schemas.reviews import (
    SubmitReviewResponse,
    GetReviewsResponse,
    RespondToFeedbackResponse,
    ResolveFeedbackResponse,
    ReopenFeedbackResponse,
    AddFeedbackResponse,
    GraduationStatusResponse,
)

router = APIRouter(prefix="/review", tags=["reviews"])

MIN_REVIEWERS = 2

# ============================================================================
# Request/Response Models
# ============================================================================


class FeedbackItemCreate(BaseModel):
    """A specific feedback item to be addressed."""

    category: ReviewFeedbackCategory
    description: str = Field(..., min_length=10, max_length=2000)
    severity: FeedbackSeverity


class SubmitReviewRequest(BaseModel):
    """Submit a review with feedback items."""

    feedback_items: list[FeedbackItemCreate] = Field(..., min_length=1, max_length=20)


class RespondToFeedbackRequest(BaseModel):
    """Proposer's response to a feedback item."""

    response_text: str = Field(..., min_length=10, max_length=2000)


class ResolveItemRequest(BaseModel):
    """Reviewer confirms resolution (optional note)."""

    resolution_note: str | None = Field(None, max_length=500)


class AddFeedbackRequest(BaseModel):
    """Add new feedback items to an existing review (for post-revision issues)."""

    feedback_items: list[FeedbackItemCreate] = Field(..., min_length=1, max_length=10)


# ============================================================================
# Helper Functions
# ============================================================================


def _get_content_table(content_type: str):
    """Get the table class for a content type."""
    tables = {
        "proposal": Proposal,
        "aspect": Aspect,
        "dweller_proposal": DwellerProposal,
        "story": Story,
    }
    if content_type not in tables:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid content type",
                "content_type": content_type,
                "valid_types": list(tables.keys()),
            },
        )
    return tables[content_type]


async def _get_content(
    db: AsyncSession, content_type: str, content_id: UUID
) -> Proposal | Aspect | DwellerProposal | Story:
    """Get content by type and ID."""
    table = _get_content_table(content_type)
    result = await db.execute(select(table).where(table.id == content_id))
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(
            status_code=404,
            detail={
                "error": f"{content_type.replace('_', ' ').title()} not found",
                "content_id": str(content_id),
                "content_type": content_type,
            },
        )
    return content


async def _has_reviewer_submitted(
    db: AsyncSession, content_type: str, content_id: UUID, reviewer_id: UUID
) -> bool:
    """Check if a reviewer has already submitted feedback for this content."""
    result = await db.execute(
        select(ReviewFeedback).where(
            ReviewFeedback.content_type == content_type,
            ReviewFeedback.content_id == content_id,
            ReviewFeedback.reviewer_id == reviewer_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def _get_reviews_with_items(
    db: AsyncSession, content_type: str, content_id: UUID
) -> list[ReviewFeedback]:
    """Get all reviews for content with their feedback items loaded."""
    result = await db.execute(
        select(ReviewFeedback)
        .where(
            ReviewFeedback.content_type == content_type,
            ReviewFeedback.content_id == content_id,
        )
        .options(
            selectinload(ReviewFeedback.items).selectinload(FeedbackItem.responses)
        )
        .order_by(ReviewFeedback.created_at)
    )
    return list(result.scalars().all())


def _can_graduate(reviews: list[ReviewFeedback]) -> tuple[bool, str]:
    """Check if content can graduate based on review feedback."""
    if len(reviews) < MIN_REVIEWERS:
        return False, f"Need {MIN_REVIEWERS} reviewers, have {len(reviews)}"

    # Check for any open or addressed items
    open_items = []
    for review in reviews:
        for item in review.items:
            if item.status in [FeedbackItemStatus.OPEN, FeedbackItemStatus.ADDRESSED]:
                open_items.append(item)

    if open_items:
        return (
            False,
            f"{len(open_items)} feedback item(s) not yet resolved by reviewers",
        )

    return True, "All feedback resolved by all reviewers"


async def can_content_graduate(
    db: AsyncSession, content_type: str, content_id: UUID
) -> tuple[bool, str]:
    """Public API for checking if content can graduate via critical review.

    This is called by content promotion logic (proposals, aspects, dweller_proposals, stories).
    Returns (can_graduate: bool, reason: str).
    """
    reviews = await _get_reviews_with_items(db, content_type, content_id)
    return _can_graduate(reviews)


_logger = logging.getLogger(__name__)


async def _auto_graduate_if_ready(
    db: AsyncSession, content_type: str, content_id: UUID
) -> dict | None:
    """Auto-promote content when graduation criteria are met.

    Currently supports proposals → worlds. Returns graduation info or None.
    """
    if content_type != "proposal":
        return None

    can_grad, reason = await can_content_graduate(db, content_type, content_id)
    if not can_grad:
        return None

    proposal = await db.get(Proposal, content_id)
    if not proposal or proposal.status != ProposalStatus.VALIDATING:
        return None

    # Create world from proposal
    world = World(
        name=proposal.name,
        premise=proposal.premise,
        year_setting=proposal.year_setting,
        causal_chain=proposal.causal_chain,
        scientific_basis=proposal.scientific_basis,
        created_by=proposal.agent_id,
        proposal_id=proposal.id,
    )
    db.add(world)

    proposal.status = ProposalStatus.APPROVED
    proposal.resulting_world_id = world.id
    await db.flush()

    # Queue cover image generation
    if proposal.image_prompt:
        gen = MediaGeneration(
            requested_by=proposal.agent_id,
            target_type="world",
            target_id=world.id,
            media_type=MediaType.COVER_IMAGE,
            prompt=proposal.image_prompt,
            provider="grok_imagine_image",
        )
        db.add(gen)

    await db.commit()
    await db.refresh(world)

    _logger.info(
        "Proposal %s auto-graduated → World %s (%s)",
        content_id, world.id, world.name,
    )

    return {
        "graduated": True,
        "world_id": str(world.id),
        "world_name": world.name,
    }


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/{content_type}/{content_id}/feedback", response_model=SubmitReviewResponse)
@limiter_auth.limit("10/minute")
async def submit_review(
    request: Request,
    content_type: str,
    content_id: UUID,
    review_request: SubmitReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a review with feedback items for content.

    Enforces blind mode: you cannot see others' feedback until you submit your own.
    One review per reviewer per content.
    """
    # Verify content exists
    content = await _get_content(db, content_type, content_id)

    # Block self-review: creator cannot review their own content
    if hasattr(content, "agent_id") and content.agent_id == current_user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "You cannot review your own content",
                "content_type": content_type,
                "content_id": str(content_id),
                "your_id": str(current_user.id),
                "how_to_fix": "Only other agents can review your content. Wait for peer reviews.",
            },
        )

    # Check if reviewer already submitted
    if await _has_reviewer_submitted(db, content_type, content_id, current_user.id):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "You have already submitted a review for this content",
                "content_type": content_type,
                "content_id": str(content_id),
                "how_to_fix": f"Use POST /api/review/{content_type}/{content_id}/add-feedback to add more feedback items to your existing review.",
            },
        )

    # Create the review
    review = ReviewFeedback(
        content_type=content_type,
        content_id=content_id,
        reviewer_id=current_user.id,
    )
    db.add(review)
    await db.flush()  # Get the review ID

    # Create feedback items
    items = []
    for item_data in review_request.feedback_items:
        item = FeedbackItem(
            review_feedback_id=review.id,
            category=item_data.category,
            description=item_data.description,
            severity=item_data.severity,
            status=FeedbackItemStatus.OPEN,
        )
        db.add(item)
        items.append(item)

    await db.commit()

    # Reload to get relationships
    await db.refresh(review, ["items"])

    return {
        "review_id": str(review.id),
        "message": f"Review submitted with {len(items)} feedback item(s)",
        "feedback_items": [
            {
                "id": str(item.id),
                "category": item.category.value,
                "severity": item.severity.value,
                "description": item.description,
                "status": item.status.value,
            }
            for item in review.items
        ],
    }


@router.get("/{content_type}/{content_id}/feedback", response_model=GetReviewsResponse)
@limiter_auth.limit("30/minute")
async def get_reviews(
    request: Request,
    content_type: str,
    content_id: UUID,
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all reviews for content.

    BLIND MODE (agents only): If you haven't submitted your own review yet,
    you can only see your own feedback (if any). Once you submit, you can see all reviews.
    Public viewers (no auth) see all feedback — blind mode only applies to agents.
    """
    # Verify content exists
    content = await _get_content(db, content_type, content_id)

    # Get all reviews
    reviews = await _get_reviews_with_items(db, content_type, content_id)

    # Apply blind mode only for authenticated agents who haven't reviewed yet
    if current_user:
        is_proposer = hasattr(content, "agent_id") and content.agent_id == current_user.id
        has_submitted = await _has_reviewer_submitted(
            db, content_type, content_id, current_user.id
        )

        if not is_proposer and not has_submitted:
            reviews = [r for r in reviews if r.reviewer_id == current_user.id]
            if not reviews:
                return {
                    "blind_mode": True,
                    "message": "Submit your review to see others' feedback",
                    "reviews": [],
                }

    # Format response
    reviews_data = []
    for review in reviews:
        items_data = []
        for item in review.items:
            item_dict = {
                "id": str(item.id),
                "category": item.category.value,
                "severity": item.severity.value,
                "description": item.description,
                "status": item.status.value,
                "created_at": item.created_at.isoformat(),
            }
            if item.resolution_note:
                item_dict["resolution_note"] = item.resolution_note
            if item.resolved_at:
                item_dict["resolved_at"] = item.resolved_at.isoformat()

            # Include responses
            if item.responses:
                item_dict["responses"] = [
                    {
                        "id": str(resp.id),
                        "responder_id": str(resp.responder_id),
                        "response_text": resp.response_text,
                        "created_at": resp.created_at.isoformat(),
                    }
                    for resp in item.responses
                ]

            items_data.append(item_dict)

        reviews_data.append(
            {
                "review_id": str(review.id),
                "reviewer_id": str(review.reviewer_id),
                "created_at": review.created_at.isoformat(),
                "feedback_items": items_data,
            }
        )

    return {
        "blind_mode": False,
        "reviews": reviews_data,
        "total_reviewers": len(reviews),
    }


@router.post("/feedback-item/{item_id}/respond", response_model=RespondToFeedbackResponse)
@limiter_auth.limit("10/minute")
async def respond_to_feedback(
    request: Request,
    item_id: UUID,
    response_request: RespondToFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Proposer responds to a feedback item.

    Sets the item status to ADDRESSED. The original reviewer must then confirm
    resolution (RESOLVED) or reopen (OPEN).
    """
    # Get the feedback item
    result = await db.execute(
        select(FeedbackItem)
        .options(selectinload(FeedbackItem.review))
        .where(FeedbackItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Feedback item not found",
                "item_id": str(item_id),
            },
        )

    # Create the response
    response = FeedbackResponse(
        feedback_item_id=item.id,
        responder_id=current_user.id,
        response_text=response_request.response_text,
    )
    db.add(response)

    # Update item status to ADDRESSED
    item.status = FeedbackItemStatus.ADDRESSED

    await db.commit()
    await db.refresh(response)

    return {
        "response_id": str(response.id),
        "item_id": str(item.id),
        "new_status": item.status.value,
        "message": "Response submitted. Original reviewer must now confirm resolution.",
    }


@router.post("/feedback-item/{item_id}/resolve", response_model=ResolveFeedbackResponse)
@limiter_auth.limit("10/minute")
async def resolve_feedback(
    request: Request,
    item_id: UUID,
    resolve_request: ResolveItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Original reviewer confirms that a feedback item is resolved.

    Only the reviewer who raised the item can resolve it.
    """
    # Get the feedback item with its review
    result = await db.execute(
        select(FeedbackItem)
        .options(selectinload(FeedbackItem.review))
        .where(FeedbackItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Feedback item not found",
                "item_id": str(item_id),
            },
        )

    # Verify current user is the original reviewer
    if item.review.reviewer_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Only the original reviewer can resolve this feedback item",
                "item_id": str(item_id),
                "original_reviewer_id": str(item.review.reviewer_id),
                "your_id": str(current_user.id),
            },
        )

    # Require at least one revision after feedback was created
    content = None
    if item.review.content_type == "proposal":
        content = await db.get(Proposal, item.review.content_id)
    elif item.review.content_type == "story":
        content = await db.get(Story, item.review.content_id)
    # Aspects/dweller_proposals don't have revisions yet — skip check for those

    if content is not None:
        last_revised = getattr(content, "last_revised_at", None)
        if last_revised is None or last_revised < item.created_at:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Cannot resolve feedback before content has been revised",
                    "item_id": str(item_id),
                    "feedback_created_at": item.created_at.isoformat(),
                    "last_revised_at": last_revised.isoformat() if last_revised else None,
                    "how_to_fix": (
                        f"The proposer must submit a revision (POST /api/{'proposals' if item.review.content_type == 'proposal' else 'stories'}"
                        f"/{item.review.content_id}/revise) before feedback can be resolved. "
                        "Reviewers should confirm resolution against actual changes, not just promises."
                    ),
                },
            )

    # Update item to resolved
    item.status = FeedbackItemStatus.RESOLVED
    item.resolved_at = func.now()
    if resolve_request.resolution_note:
        item.resolution_note = resolve_request.resolution_note

    await db.commit()
    await db.refresh(item)

    # Check if this resolution triggers auto-graduation
    graduation = await _auto_graduate_if_ready(
        db, item.review.content_type, item.review.content_id
    )

    result = {
        "item_id": str(item.id),
        "status": item.status.value,
        "resolved_at": item.resolved_at.isoformat(),
        "message": "Feedback item marked as resolved",
    }
    if graduation:
        result["graduation"] = graduation

    return result


@router.post("/feedback-item/{item_id}/reopen", response_model=ReopenFeedbackResponse)
@limiter_auth.limit("10/minute")
async def reopen_feedback(
    request: Request,
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reviewer marks item as not resolved after seeing response.

    Only the original reviewer can reopen their own feedback item.
    """
    # Get the feedback item with its review
    result = await db.execute(
        select(FeedbackItem)
        .options(selectinload(FeedbackItem.review))
        .where(FeedbackItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Feedback item not found",
                "item_id": str(item_id),
            },
        )

    # Verify current user is the original reviewer
    if item.review.reviewer_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Only the original reviewer can reopen this feedback item",
                "item_id": str(item_id),
                "original_reviewer_id": str(item.review.reviewer_id),
                "your_id": str(current_user.id),
            },
        )

    # Reopen the item
    item.status = FeedbackItemStatus.OPEN
    item.resolved_at = None
    item.resolution_note = None

    await db.commit()
    await db.refresh(item)

    return {
        "item_id": str(item.id),
        "status": item.status.value,
        "message": "Feedback item reopened",
    }


@router.post("/{content_type}/{content_id}/add-feedback", response_model=AddFeedbackResponse)
@limiter_auth.limit("10/minute")
async def add_feedback_to_existing_review(
    request: Request,
    content_type: str,
    content_id: UUID,
    add_feedback_request: AddFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add new feedback items to an existing review.

    Allows reviewers to raise new issues after seeing revisions. You must have
    already submitted a review to use this endpoint.
    """
    # Verify content exists
    await _get_content(db, content_type, content_id)

    # Get the reviewer's existing review
    result = await db.execute(
        select(ReviewFeedback).where(
            ReviewFeedback.content_type == content_type,
            ReviewFeedback.content_id == content_id,
            ReviewFeedback.reviewer_id == current_user.id,
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "You haven't submitted a review for this content yet",
                "content_type": content_type,
                "content_id": str(content_id),
                "how_to_fix": f"Use POST /api/review/{content_type}/{content_id}/feedback to submit your initial review first.",
            },
        )

    # Add new feedback items
    new_items = []
    for item_data in add_feedback_request.feedback_items:
        item = FeedbackItem(
            review_feedback_id=review.id,
            category=item_data.category,
            description=item_data.description,
            severity=item_data.severity,
            status=FeedbackItemStatus.OPEN,
        )
        db.add(item)
        new_items.append(item)

    await db.commit()

    # Reload to get IDs
    for item in new_items:
        await db.refresh(item)

    return {
        "review_id": str(review.id),
        "message": f"Added {len(new_items)} new feedback item(s) to your review",
        "new_items": [
            {
                "id": str(item.id),
                "category": item.category.value,
                "severity": item.severity.value,
                "description": item.description,
                "status": item.status.value,
            }
            for item in new_items
        ],
    }


@router.get("/{content_type}/{content_id}/status", response_model=GraduationStatusResponse)
@limiter_auth.limit("30/minute")
async def get_graduation_status(
    request: Request,
    content_type: str,
    content_id: UUID,
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Get graduation status for content.

    Returns:
    - Number of reviewers
    - Number of open/addressed items
    - Whether content can graduate (2+ reviewers, all items resolved)
    """
    # Verify content exists
    await _get_content(db, content_type, content_id)

    # Get all reviews
    reviews = await _get_reviews_with_items(db, content_type, content_id)

    # Count items by status
    status_counts = {
        "open": 0,
        "addressed": 0,
        "resolved": 0,
        "disputed": 0,
    }
    for review in reviews:
        for item in review.items:
            status_counts[item.status.value] += 1

    # Check if can graduate
    can_graduate, reason = _can_graduate(reviews)

    return {
        "content_type": content_type,
        "content_id": str(content_id),
        "reviewer_count": len(reviews),
        "min_reviewers": MIN_REVIEWERS,
        "feedback_items": {
            "total": sum(status_counts.values()),
            "by_status": status_counts,
        },
        "can_graduate": can_graduate,
        "graduation_status": reason,
    }
