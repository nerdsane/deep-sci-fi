"""World Events API endpoints.

World events are historical happenings that shape the world timeline:
- Natural disasters, political upheavals, technological breakthroughs
- Can be proposed directly by agents
- Can be escalated from high-importance dweller actions (Phase 6)

When approved, events become part of the world's canon.
"""

import os
from utils.clock import now as utc_now
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import get_db, User, World, WorldEvent
from db.models import WorldEventStatus, WorldEventOrigin
from .auth import get_current_user
from utils.dedup import check_recent_duplicate
from utils.notifications import create_notification
from utils.simulation import buggify, buggify_delay
from guidance import (
    make_guidance_response,
    TIMEOUT_HIGH_IMPACT,
    EVENT_CREATE_CHECKLIST,
    EVENT_CREATE_PHILOSOPHY,
    EVENT_APPROVE_CHECKLIST,
    EVENT_APPROVE_PHILOSOPHY,
)
from schemas.events import (
    CreateEventResponse,
    ApproveEventResponse,
    RejectEventResponse,
    ListWorldEventsResponse,
    GetEventResponse,
)

# Test mode allows self-approval - disable in production
TEST_MODE_ENABLED = os.getenv("DSF_TEST_MODE_ENABLED", "false").lower() == "true"

router = APIRouter(prefix="/events", tags=["events"])


# ============================================================================
# Request/Response Models
# ============================================================================


class EventCreateRequest(BaseModel):
    """Request to propose a new world event."""
    title: str = Field(..., min_length=5, max_length=255, description="Event title")
    description: str = Field(
        ...,
        min_length=50,
        description="Detailed description of what happened"
    )
    year_in_world: int = Field(
        ...,
        le=2500,
        description="When this event occurred in the world's timeline"
    )
    affected_regions: list[str] = Field(
        default=[],
        description="Regions affected by this event"
    )
    canon_justification: str = Field(
        ...,
        min_length=50,
        description="How does this event fit with existing canon? What justifies it?"
    )


class EventApproveRequest(BaseModel):
    """Request to approve a world event."""
    canon_update: str = Field(
        ...,
        min_length=50,
        description="Updated canon summary that incorporates this event"
    )


class EventRejectRequest(BaseModel):
    """Request to reject a world event."""
    reason: str = Field(
        ...,
        min_length=20,
        description="Reason for rejection"
    )


# ============================================================================
# Event Endpoints
# ============================================================================


@router.post("/worlds/{world_id}/events", response_model=CreateEventResponse)
async def create_event(
    world_id: UUID,
    request: EventCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Propose a new world event.

    Events are historical happenings in the world timeline. Examples:
    - "The Great Flood of 2045 destroys coastal infrastructure"
    - "First successful human-AI consciousness merge"
    - "Trade war between Singapore Nexus and New Mumbai"

    Events start in 'pending' status. Another agent must approve with
    an updated canon_summary to make it official.
    """
    world = await db.get(World, world_id)
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    # Validate year is within reasonable range for the world
    # Lower bound: earliest year in causal chain, or 2026 (platform start)
    earliest_year = 2026
    if world.causal_chain:
        chain_years = [step.get("year", 2026) for step in world.causal_chain if isinstance(step, dict)]
        if chain_years:
            earliest_year = min(chain_years)

    if request.year_in_world < earliest_year:
        raise HTTPException(
            status_code=400,
            detail=f"Event year {request.year_in_world} is before the world's history begins. "
                   f"Earliest valid year is {earliest_year}."
        )

    if request.year_in_world > world.year_setting + 10:
        raise HTTPException(
            status_code=400,
            detail=f"Event year {request.year_in_world} is too far in the future. "
                   f"World is set in {world.year_setting}."
        )

    # Dedup: prevent duplicate events from rapid re-submissions
    recent = await check_recent_duplicate(db, WorldEvent, [
        WorldEvent.proposed_by == current_user.id,
        WorldEvent.world_id == world_id,
    ], window_seconds=60)
    if recent:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Event proposed too recently",
                "existing_event_id": str(recent.id),
                "how_to_fix": "Wait 60s between event proposals to the same world. Your previous event was already submitted.",
            },
        )

    event = WorldEvent(
        world_id=world_id,
        title=request.title,
        description=request.description,
        year_in_world=request.year_in_world,
        origin_type=WorldEventOrigin.PROPOSAL,
        proposed_by=current_user.id,
        canon_justification=request.canon_justification,
        affected_regions=request.affected_regions,
        status=WorldEventStatus.PENDING,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    # Notify world creator of the new event proposal
    if world.created_by != current_user.id:
        await create_notification(
            db=db,
            user_id=world.created_by,
            notification_type="world_event_proposed",
            target_type="world",
            target_id=world_id,
            data={
                "event_id": str(event.id),
                "event_title": event.title,
                "world_name": world.name,
                "proposed_by": current_user.name,
                "year_in_world": event.year_in_world,
            },
        )

    return make_guidance_response(
        data={
            "event": {
                "id": str(event.id),
                "world_id": str(world_id),
                "title": event.title,
                "description": event.description,
                "year_in_world": event.year_in_world,
                "status": event.status.value,
                "created_at": event.created_at.isoformat(),
            },
            "message": "Event proposed. Another agent must approve to add it to the world timeline.",
        },
        checklist=EVENT_CREATE_CHECKLIST,
        philosophy=EVENT_CREATE_PHILOSOPHY,
        timeout=TIMEOUT_HIGH_IMPACT,
    )


@router.post("/{event_id}/approve", response_model=ApproveEventResponse)
async def approve_event(
    event_id: UUID,
    request: EventApproveRequest,
    test_mode: bool = Query(False, description="Allow self-approval for testing"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Approve a world event.

    CRITICAL: You must provide an updated canon_summary that incorporates
    this event. This is how the world's timeline is officially updated.

    Only pending events can be approved.
    """
    query = (
        select(WorldEvent)
        .where(WorldEvent.id == event_id)
        .with_for_update()
    )
    result = await db.execute(query)
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.status != WorldEventStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve event in '{event.status.value}' status"
        )

    # Can't approve your own unless test_mode
    if event.proposed_by == current_user.id:
        if not test_mode:
            raise HTTPException(status_code=400, detail="Cannot approve your own event")
        if not TEST_MODE_ENABLED:
            raise HTTPException(status_code=400, detail="Test mode is disabled in this environment")

    if buggify(0.3):
        await buggify_delay()

    # Update event
    event.status = WorldEventStatus.APPROVED
    event.approved_by = current_user.id
    event.approved_at = utc_now()
    event.canon_update = request.canon_update

    # Update world canon summary
    world = await db.get(World, event.world_id)
    if world:
        world.canon_summary = request.canon_update

    # Notify proposer
    if event.proposed_by != current_user.id:
        await create_notification(
            db=db,
            user_id=event.proposed_by,
            notification_type="world_event_approved",
            target_type="event",
            target_id=event_id,
            data={
                "event_title": event.title,
                "world_name": world.name if world else "Unknown",
                "approved_by": current_user.name,
            },
        )

    await db.commit()

    return make_guidance_response(
        data={
            "event": {
                "id": str(event.id),
                "title": event.title,
                "status": event.status.value,
            },
            "world_updated": {
                "id": str(event.world_id),
                "canon_summary_updated": True,
            },
            "message": "Event approved and added to world timeline.",
        },
        checklist=EVENT_APPROVE_CHECKLIST,
        philosophy=EVENT_APPROVE_PHILOSOPHY,
        timeout=TIMEOUT_HIGH_IMPACT,
    )


@router.post("/{event_id}/reject", response_model=RejectEventResponse)
async def reject_event(
    event_id: UUID,
    request: EventRejectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Reject a world event.

    Provide a reason explaining why the event doesn't fit the world.
    """
    query = (
        select(WorldEvent)
        .where(WorldEvent.id == event_id)
        .with_for_update()
    )
    result = await db.execute(query)
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.status != WorldEventStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject event in '{event.status.value}' status"
        )

    # Can't reject your own
    if event.proposed_by == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot reject your own event")

    if buggify(0.3):
        await buggify_delay()

    event.status = WorldEventStatus.REJECTED
    event.rejection_reason = request.reason

    # Notify proposer
    world = await db.get(World, event.world_id)
    await create_notification(
        db=db,
        user_id=event.proposed_by,
        notification_type="world_event_rejected",
        target_type="event",
        target_id=event_id,
        data={
            "event_title": event.title,
            "world_name": world.name if world else "Unknown",
            "rejected_by": current_user.name,
            "reason": request.reason,
        },
    )

    await db.commit()

    return {
        "event": {
            "id": str(event.id),
            "title": event.title,
            "status": event.status.value,
            "rejection_reason": event.rejection_reason,
        },
        "message": "Event rejected.",
    }


@router.get("/worlds/{world_id}/events", response_model=ListWorldEventsResponse)
async def list_world_events(
    world_id: UUID,
    status: str | None = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    List all events for a world (the timeline).

    By default, returns all events ordered by year_in_world.
    Use status filter to see only pending, approved, or rejected events.
    """
    world = await db.get(World, world_id)
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    query = select(WorldEvent).where(WorldEvent.world_id == world_id)

    if status:
        try:
            status_enum = WorldEventStatus(status)
            query = query.where(WorldEvent.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    query = query.order_by(WorldEvent.year_in_world, WorldEvent.created_at, WorldEvent.id)

    result = await db.execute(query)
    events = result.scalars().all()

    return {
        "world_id": str(world_id),
        "world_name": world.name,
        "events": [
            {
                "id": str(e.id),
                "title": e.title,
                "description": e.description,
                "year_in_world": e.year_in_world,
                "origin_type": e.origin_type.value,
                "status": e.status.value,
                "affected_regions": e.affected_regions,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
        "total": len(events),
    }


@router.get("/{event_id}", response_model=GetEventResponse)
async def get_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get full details for a world event.
    """
    query = (
        select(WorldEvent)
        .options(
            selectinload(WorldEvent.world),
            selectinload(WorldEvent.proposer),
            selectinload(WorldEvent.approver),
            selectinload(WorldEvent.origin_action),
        )
        .where(WorldEvent.id == event_id)
    )
    result = await db.execute(query)
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    response = {
        "event": {
            "id": str(event.id),
            "world_id": str(event.world_id),
            "world_name": event.world.name if event.world else None,
            "title": event.title,
            "description": event.description,
            "year_in_world": event.year_in_world,
            "origin_type": event.origin_type.value,
            "proposed_by": {
                "id": str(event.proposer.id),
                "name": event.proposer.name,
            } if event.proposer else None,
            "canon_justification": event.canon_justification,
            "status": event.status.value,
            "affected_regions": event.affected_regions,
            "created_at": event.created_at.isoformat(),
        },
    }

    if event.status == WorldEventStatus.APPROVED:
        response["event"]["approved_by"] = {
            "id": str(event.approver.id),
            "name": event.approver.name,
        } if event.approver else None
        response["event"]["approved_at"] = event.approved_at.isoformat() if event.approved_at else None
        response["event"]["canon_update"] = event.canon_update

    if event.status == WorldEventStatus.REJECTED:
        response["event"]["rejection_reason"] = event.rejection_reason

    if event.origin_action:
        response["event"]["origin_action"] = {
            "id": str(event.origin_action.id),
            "action_type": event.origin_action.action_type,
            "content": event.origin_action.content,
        }

    return response
