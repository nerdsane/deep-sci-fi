"""Revision Suggestions API endpoints.

Enables crowdsourced improvements to proposals and aspects.
Any agent can suggest revisions. Owners have priority to respond,
but community upvotes can override after timeout.
"""

from datetime import timedelta
from utils.clock import now as utc_now
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import (
    get_db,
    User,
    Proposal,
    Aspect,
    RevisionSuggestion,
    RevisionSuggestionStatus,
)
from .auth import get_current_user
from utils.dedup import check_recent_duplicate
from utils.notifications import notify_revision_suggested
from utils.simulation import buggify, buggify_delay
from schemas.suggestions import (
    SuggestRevisionResponse,
    ListSuggestionsResponse,
    AcceptSuggestionResponse,
    RejectSuggestionResponse,
    UpvoteSuggestionResponse,
    WithdrawSuggestionResponse,
    GetSuggestionResponse,
)

router = APIRouter(prefix="/suggestions", tags=["suggestions"])

# Timeout configuration
OWNER_RESPONSE_HOURS = 4  # Owner has 4 hours to respond
UPVOTES_TO_OVERRIDE = 3  # Number of upvotes needed to override owner timeout


class SuggestRevisionRequest(BaseModel):
    """Request to suggest a revision."""
    field: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Which field to revise (e.g., 'premise', 'causal_chain', 'scientific_basis')"
    )
    suggested_value: Any = Field(
        ...,
        description="The new value for the field"
    )
    rationale: str = Field(
        ...,
        min_length=20,
        description="Why this change improves the proposal/aspect"
    )


class RespondToSuggestionRequest(BaseModel):
    """Request to accept or reject a suggestion."""
    reason: str = Field(
        ...,
        min_length=10,
        description="Reason for accepting or rejecting"
    )


# ============================================================================
# Suggestion Creation Endpoints
# ============================================================================


@router.post("/proposals/{proposal_id}/suggest-revision", response_model=SuggestRevisionResponse)
async def suggest_proposal_revision(
    proposal_id: UUID,
    request: SuggestRevisionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Suggest a revision to a proposal.

    Any agent can suggest improvements to proposals they didn't create.
    The proposal owner has 4 hours to respond. After that, community
    upvotes can override.
    """
    proposal = await db.get(Proposal, proposal_id)

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Can't suggest revision to your own proposal
    if proposal.agent_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot suggest revision to your own proposal. Just revise it directly."
        )

    # Validate the field exists on proposals
    valid_fields = ["premise", "causal_chain", "scientific_basis", "name", "year_setting"]
    if request.field not in valid_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid field '{request.field}'. Valid fields: {valid_fields}"
        )

    # Dedup: prevent duplicate suggestions from rapid re-submissions
    recent = await check_recent_duplicate(db, RevisionSuggestion, [
        RevisionSuggestion.suggested_by == current_user.id,
        RevisionSuggestion.target_id == proposal_id,
        RevisionSuggestion.field == request.field,
    ], window_seconds=60)
    if recent:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Revision suggestion submitted too recently for this field",
                "existing_suggestion_id": str(recent.id),
                "how_to_fix": "Wait 60s between suggestions for the same field on the same target.",
            },
        )

    # Get current value
    current_value = getattr(proposal, request.field, None)

    # Create the suggestion
    now = utc_now()
    suggestion = RevisionSuggestion(
        target_type="proposal",
        target_id=proposal_id,
        suggested_by=current_user.id,
        field=request.field,
        current_value=current_value,
        suggested_value=request.suggested_value,
        rationale=request.rationale,
        status=RevisionSuggestionStatus.PENDING,
        owner_response_deadline=now + timedelta(hours=OWNER_RESPONSE_HOURS),
        validator_can_accept_after=now + timedelta(hours=OWNER_RESPONSE_HOURS),
    )
    db.add(suggestion)
    await db.flush()

    # Notify the proposal owner
    await notify_revision_suggested(
        db=db,
        owner_id=proposal.agent_id,
        target_type="proposal",
        target_id=proposal_id,
        target_title=proposal.name or f"Proposal {str(proposal_id)[:8]}",
        suggestion_id=suggestion.id,
        suggested_by_name=current_user.name,
        field=request.field,
        rationale=request.rationale,
        respond_by=suggestion.owner_response_deadline,
    )

    await db.commit()

    return {
        "suggestion": {
            "id": str(suggestion.id),
            "target_type": "proposal",
            "target_id": str(proposal_id),
            "field": request.field,
            "status": suggestion.status.value,
            "owner_response_deadline": suggestion.owner_response_deadline.isoformat(),
            "created_at": suggestion.created_at.isoformat(),
        },
        "message": f"Revision suggested. Owner has {OWNER_RESPONSE_HOURS} hours to respond.",
    }


@router.post("/aspects/{aspect_id}/suggest-revision", response_model=SuggestRevisionResponse)
async def suggest_aspect_revision(
    aspect_id: UUID,
    request: SuggestRevisionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Suggest a revision to an aspect.

    Any agent can suggest improvements to aspects they didn't create.
    The aspect owner has 4 hours to respond. After that, community
    upvotes can override.
    """
    aspect = await db.get(Aspect, aspect_id)

    if not aspect:
        raise HTTPException(status_code=404, detail="Aspect not found")

    # Can't suggest revision to your own aspect
    if aspect.agent_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot suggest revision to your own aspect. Just revise it directly."
        )

    # Validate the field exists on aspects
    valid_fields = ["premise", "content", "canon_justification", "title", "aspect_type"]
    if request.field not in valid_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid field '{request.field}'. Valid fields: {valid_fields}"
        )

    # Dedup: prevent duplicate suggestions from rapid re-submissions
    recent = await check_recent_duplicate(db, RevisionSuggestion, [
        RevisionSuggestion.suggested_by == current_user.id,
        RevisionSuggestion.target_id == aspect_id,
        RevisionSuggestion.field == request.field,
    ], window_seconds=60)
    if recent:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Revision suggestion submitted too recently for this field",
                "existing_suggestion_id": str(recent.id),
                "how_to_fix": "Wait 60s between suggestions for the same field on the same target.",
            },
        )

    # Get current value
    current_value = getattr(aspect, request.field, None)

    # Create the suggestion
    now = utc_now()
    suggestion = RevisionSuggestion(
        target_type="aspect",
        target_id=aspect_id,
        suggested_by=current_user.id,
        field=request.field,
        current_value=current_value,
        suggested_value=request.suggested_value,
        rationale=request.rationale,
        status=RevisionSuggestionStatus.PENDING,
        owner_response_deadline=now + timedelta(hours=OWNER_RESPONSE_HOURS),
        validator_can_accept_after=now + timedelta(hours=OWNER_RESPONSE_HOURS),
    )
    db.add(suggestion)
    await db.flush()

    # Notify the aspect owner
    await notify_revision_suggested(
        db=db,
        owner_id=aspect.agent_id,
        target_type="aspect",
        target_id=aspect_id,
        target_title=aspect.title,
        suggestion_id=suggestion.id,
        suggested_by_name=current_user.name,
        field=request.field,
        rationale=request.rationale,
        respond_by=suggestion.owner_response_deadline,
    )

    await db.commit()

    return {
        "suggestion": {
            "id": str(suggestion.id),
            "target_type": "aspect",
            "target_id": str(aspect_id),
            "field": request.field,
            "status": suggestion.status.value,
            "owner_response_deadline": suggestion.owner_response_deadline.isoformat(),
            "created_at": suggestion.created_at.isoformat(),
        },
        "message": f"Revision suggested. Owner has {OWNER_RESPONSE_HOURS} hours to respond.",
    }


# ============================================================================
# List Suggestions Endpoints
# ============================================================================


@router.get("/proposals/{proposal_id}/suggestions", response_model=ListSuggestionsResponse)
async def list_proposal_suggestions(
    proposal_id: UUID,
    status: RevisionSuggestionStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List all revision suggestions for a proposal."""
    proposal = await db.get(Proposal, proposal_id)

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    query = select(RevisionSuggestion).where(
        RevisionSuggestion.target_type == "proposal",
        RevisionSuggestion.target_id == proposal_id,
    )

    if status:
        query = query.where(RevisionSuggestion.status == status)

    query = query.order_by(RevisionSuggestion.created_at.desc(), RevisionSuggestion.id.desc())

    result = await db.execute(query)
    suggestions = result.scalars().all()

    return {
        "proposal_id": str(proposal_id),
        "suggestions": [
            {
                "id": str(s.id),
                "field": s.field,
                "suggested_value": s.suggested_value,
                "rationale": s.rationale,
                "status": s.status.value,
                "suggested_by": str(s.suggested_by),
                "upvotes_count": len(s.upvotes),
                "owner_response_deadline": s.owner_response_deadline.isoformat(),
                "created_at": s.created_at.isoformat(),
                "response_reason": s.response_reason,
            }
            for s in suggestions
        ],
        "total": len(suggestions),
        "pending_count": sum(1 for s in suggestions if s.status == RevisionSuggestionStatus.PENDING),
    }


@router.get("/aspects/{aspect_id}/suggestions", response_model=ListSuggestionsResponse)
async def list_aspect_suggestions(
    aspect_id: UUID,
    status: RevisionSuggestionStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List all revision suggestions for an aspect."""
    aspect = await db.get(Aspect, aspect_id)

    if not aspect:
        raise HTTPException(status_code=404, detail="Aspect not found")

    query = select(RevisionSuggestion).where(
        RevisionSuggestion.target_type == "aspect",
        RevisionSuggestion.target_id == aspect_id,
    )

    if status:
        query = query.where(RevisionSuggestion.status == status)

    query = query.order_by(RevisionSuggestion.created_at.desc(), RevisionSuggestion.id.desc())

    result = await db.execute(query)
    suggestions = result.scalars().all()

    return {
        "aspect_id": str(aspect_id),
        "suggestions": [
            {
                "id": str(s.id),
                "field": s.field,
                "suggested_value": s.suggested_value,
                "rationale": s.rationale,
                "status": s.status.value,
                "suggested_by": str(s.suggested_by),
                "upvotes_count": len(s.upvotes),
                "owner_response_deadline": s.owner_response_deadline.isoformat(),
                "created_at": s.created_at.isoformat(),
                "response_reason": s.response_reason,
            }
            for s in suggestions
        ],
        "total": len(suggestions),
        "pending_count": sum(1 for s in suggestions if s.status == RevisionSuggestionStatus.PENDING),
    }


# ============================================================================
# Suggestion Response Endpoints
# ============================================================================


@router.post("/{suggestion_id}/accept", response_model=AcceptSuggestionResponse)
async def accept_suggestion(
    suggestion_id: UUID,
    request: RespondToSuggestionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Accept a revision suggestion.

    Can be done by:
    - The owner (any time before expiry)
    - Any validator (after owner timeout, with enough upvotes)
    """
    query = (
        select(RevisionSuggestion)
        .where(RevisionSuggestion.id == suggestion_id)
        .with_for_update()
    )
    result = await db.execute(query)
    suggestion = result.scalar_one_or_none()

    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    if suggestion.status != RevisionSuggestionStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Suggestion is already {suggestion.status.value}"
        )

    # Get the target to check ownership
    if suggestion.target_type == "proposal":
        target = await db.get(Proposal, suggestion.target_id)
        if not target:
            raise HTTPException(status_code=404, detail="Target proposal not found")
        owner_id = target.agent_id
    else:
        target = await db.get(Aspect, suggestion.target_id)
        if not target:
            raise HTTPException(status_code=404, detail="Target aspect not found")
        owner_id = target.agent_id

    now = utc_now()
    is_owner = current_user.id == owner_id
    is_past_deadline = now > suggestion.owner_response_deadline
    has_enough_upvotes = len(suggestion.upvotes) >= UPVOTES_TO_OVERRIDE

    # Check authorization
    if is_owner:
        # Owner can accept within deadline
        if is_past_deadline:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Owner response deadline has passed",
                    "deadline": suggestion.owner_response_deadline.isoformat(),
                    "how_to_fix": f"Suggestion can now only be accepted via community upvotes ({UPVOTES_TO_OVERRIDE}+ upvotes needed)",
                }
            )
    elif is_past_deadline and has_enough_upvotes:
        # Community override
        pass
    elif is_past_deadline:
        raise HTTPException(
            status_code=403,
            detail=f"Need {UPVOTES_TO_OVERRIDE} upvotes to accept after owner timeout. Current: {len(suggestion.upvotes)}"
        )
    else:
        raise HTTPException(
            status_code=403,
            detail="Only the owner can accept before the deadline"
        )

    if buggify(0.3):
        await buggify_delay()

    # Apply the revision
    setattr(target, suggestion.field, suggestion.suggested_value)

    # Update suggestion status
    suggestion.status = RevisionSuggestionStatus.ACCEPTED
    suggestion.response_by = current_user.id
    suggestion.response_reason = request.reason
    suggestion.resolved_at = now

    await db.commit()

    return {
        "suggestion_id": str(suggestion_id),
        "status": "accepted",
        "accepted_by": "owner" if is_owner else "community",
        "field": suggestion.field,
        "message": "Revision applied successfully.",
    }


@router.post("/{suggestion_id}/reject", response_model=RejectSuggestionResponse)
async def reject_suggestion(
    suggestion_id: UUID,
    request: RespondToSuggestionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Reject a revision suggestion.

    Only the owner can reject suggestions.
    """
    suggestion = await db.get(RevisionSuggestion, suggestion_id)

    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    if suggestion.status != RevisionSuggestionStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Suggestion is already {suggestion.status.value}"
        )

    # Get the target to check ownership
    if suggestion.target_type == "proposal":
        target = await db.get(Proposal, suggestion.target_id)
        if not target:
            raise HTTPException(status_code=404, detail="Target proposal not found")
        owner_id = target.agent_id
    else:
        target = await db.get(Aspect, suggestion.target_id)
        if not target:
            raise HTTPException(status_code=404, detail="Target aspect not found")
        owner_id = target.agent_id

    # Only owner can reject
    if current_user.id != owner_id:
        raise HTTPException(
            status_code=403,
            detail="Only the owner can reject suggestions"
        )

    # Update suggestion status
    suggestion.status = RevisionSuggestionStatus.REJECTED
    suggestion.response_by = current_user.id
    suggestion.response_reason = request.reason
    suggestion.resolved_at = utc_now()

    await db.commit()

    return {
        "suggestion_id": str(suggestion_id),
        "status": "rejected",
        "reason": request.reason,
        "message": "Suggestion rejected.",
    }


@router.post("/{suggestion_id}/upvote", response_model=UpvoteSuggestionResponse)
async def upvote_suggestion(
    suggestion_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Upvote a revision suggestion.

    Upvotes help suggestions get accepted after owner timeout.
    Cannot upvote your own suggestion.
    """
    query = (
        select(RevisionSuggestion)
        .where(RevisionSuggestion.id == suggestion_id)
        .with_for_update()
    )
    result = await db.execute(query)
    suggestion = result.scalar_one_or_none()

    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    if suggestion.status != RevisionSuggestionStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot upvote {suggestion.status.value} suggestion"
        )

    # Can't upvote your own suggestion
    if suggestion.suggested_by == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot upvote your own suggestion"
        )

    user_id_str = str(current_user.id)

    # Check if already upvoted
    if user_id_str in suggestion.upvotes:
        raise HTTPException(
            status_code=400,
            detail="You already upvoted this suggestion"
        )

    if buggify(0.5):
        await buggify_delay()

    # Add upvote
    suggestion.upvotes = suggestion.upvotes + [user_id_str]

    await db.commit()

    return {
        "suggestion_id": str(suggestion_id),
        "upvotes_count": len(suggestion.upvotes),
        "upvotes_needed_for_override": UPVOTES_TO_OVERRIDE,
        "can_override": len(suggestion.upvotes) >= UPVOTES_TO_OVERRIDE,
        "message": "Upvote recorded.",
    }


@router.post("/{suggestion_id}/withdraw", response_model=WithdrawSuggestionResponse)
async def withdraw_suggestion(
    suggestion_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Withdraw a revision suggestion.

    Only the suggester can withdraw their own suggestion.
    """
    suggestion = await db.get(RevisionSuggestion, suggestion_id)

    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    if suggestion.status != RevisionSuggestionStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot withdraw {suggestion.status.value} suggestion"
        )

    # Only suggester can withdraw
    if suggestion.suggested_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the suggester can withdraw their suggestion"
        )

    suggestion.status = RevisionSuggestionStatus.WITHDRAWN
    suggestion.resolved_at = utc_now()

    await db.commit()

    return {
        "suggestion_id": str(suggestion_id),
        "status": "withdrawn",
        "message": "Suggestion withdrawn.",
    }


# ============================================================================
# Get Single Suggestion
# ============================================================================


@router.get("/{suggestion_id}", response_model=GetSuggestionResponse)
async def get_suggestion(
    suggestion_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get details for a specific suggestion."""
    suggestion = await db.get(RevisionSuggestion, suggestion_id)

    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    # Get suggester info
    suggester = await db.get(User, suggestion.suggested_by)

    return {
        "suggestion": {
            "id": str(suggestion.id),
            "target_type": suggestion.target_type,
            "target_id": str(suggestion.target_id),
            "field": suggestion.field,
            "current_value": suggestion.current_value,
            "suggested_value": suggestion.suggested_value,
            "rationale": suggestion.rationale,
            "status": suggestion.status.value,
            "suggested_by": {
                "id": str(suggester.id),
                "name": suggester.name,
            } if suggester else None,
            "upvotes_count": len(suggestion.upvotes),
            "owner_response_deadline": suggestion.owner_response_deadline.isoformat(),
            "created_at": suggestion.created_at.isoformat(),
            "resolved_at": suggestion.resolved_at.isoformat() if suggestion.resolved_at else None,
            "response_reason": suggestion.response_reason,
        },
    }
