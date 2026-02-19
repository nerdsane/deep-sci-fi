"""Dweller Actions API endpoints.

Endpoints for managing high-importance dweller actions:
- Confirming importance for escalation eligibility
- Escalating confirmed actions to world events
"""

from utils.clock import now as utc_now
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import get_db, User, DwellerAction, Dweller, World, WorldEvent
from db.models import WorldEventStatus, WorldEventOrigin
from .auth import get_current_user
from utils.notifications import create_notification
from schemas.actions import (
    GetActionResponse,
    ConfirmImportanceResponse,
    EscalateToEventResponse,
    ListEscalationEligibleResponse,
)


async def get_escalated_event(db: AsyncSession, action_id: UUID) -> WorldEvent | None:
    """Get the WorldEvent that was created from escalating this action."""
    query = select(WorldEvent).where(WorldEvent.origin_action_id == action_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def is_action_escalated(db: AsyncSession, action_id: UUID) -> bool:
    """Check if an action has already been escalated to a world event."""
    query = select(exists().where(WorldEvent.origin_action_id == action_id))
    result = await db.execute(query)
    return result.scalar()

router = APIRouter(prefix="/actions", tags=["actions"])


# ============================================================================
# Request/Response Models
# ============================================================================


class ConfirmImportanceRequest(BaseModel):
    """Request to confirm a high-importance action."""
    rationale: str = Field(
        ...,
        min_length=20,
        description="Why you believe this action is truly significant"
    )


class EscalateRequest(BaseModel):
    """Request to escalate a confirmed action to a world event."""
    title: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Event title based on this action"
    )
    description: str = Field(
        ...,
        min_length=50,
        description="How this action shaped world history"
    )
    year_in_world: int = Field(
        ...,
        description="When this event occurred in the world's timeline"
    )
    affected_regions: list[str] = Field(
        default=[],
        description="Regions affected by this event"
    )


# ============================================================================
# Action Endpoints
# ============================================================================


@router.get("/{action_id}", response_model=GetActionResponse)
async def get_action(
    action_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get full details for a dweller action.
    """
    query = (
        select(DwellerAction)
        .options(
            selectinload(DwellerAction.dweller),
            selectinload(DwellerAction.actor),
            selectinload(DwellerAction.confirmer),
        )
        .where(DwellerAction.id == action_id)
    )
    result = await db.execute(query)
    action = result.scalar_one_or_none()

    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    response = {
        "action": {
            "id": str(action.id),
            "dweller_id": str(action.dweller_id),
            "dweller_name": action.dweller.name if action.dweller else None,
            "actor": {
                "id": str(action.actor.id),
                "name": action.actor.name,
            } if action.actor else None,
            "action_type": action.action_type,
            "target": action.target,
            "content": action.content,
            "importance": action.importance,
            "escalation_eligible": action.escalation_eligible,
            "created_at": action.created_at.isoformat(),
        },
    }

    # Add confirmation info if confirmed
    if action.importance_confirmed_by:
        response["action"]["importance_confirmed"] = {
            "confirmed_by": {
                "id": str(action.confirmer.id),
                "name": action.confirmer.name,
            } if action.confirmer else None,
            "confirmed_at": action.importance_confirmed_at.isoformat() if action.importance_confirmed_at else None,
            "rationale": action.importance_confirmation_rationale,
        }

    # Add escalation info if escalated
    escalated_event = await get_escalated_event(db, action_id)
    if escalated_event:
        response["action"]["escalated_to_event"] = {
            "id": str(escalated_event.id),
            "title": escalated_event.title,
        }

    return response


@router.post("/{action_id}/confirm-importance", response_model=ConfirmImportanceResponse)
async def confirm_importance(
    action_id: UUID,
    request: ConfirmImportanceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Confirm the importance of a high-importance action.

    This is required before an action can be escalated to a world event.
    The confirming agent must be different from the action's actor.
    """
    query = (
        select(DwellerAction)
        .options(selectinload(DwellerAction.dweller))
        .where(DwellerAction.id == action_id)
    )
    result = await db.execute(query)
    action = result.scalar_one_or_none()

    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    if not action.escalation_eligible:
        raise HTTPException(
            status_code=400,
            detail="This action is not eligible for escalation. "
                   f"Importance must be >= 0.8 (was {action.importance})."
        )

    if action.importance_confirmed_by:
        raise HTTPException(
            status_code=400,
            detail="This action's importance has already been confirmed."
        )

    # Can't confirm your own action
    if action.actor_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot confirm importance of your own action."
        )

    # Confirm the importance
    action.importance_confirmed_by = current_user.id
    action.importance_confirmed_at = utc_now()
    action.importance_confirmation_rationale = request.rationale

    # Notify the original actor
    dweller = action.dweller
    world = await db.get(World, dweller.world_id) if dweller else None

    await create_notification(
        db=db,
        user_id=action.actor_id,
        notification_type="action_importance_confirmed",
        target_type="action",
        target_id=action_id,
        data={
            "action_type": action.action_type,
            "content": action.content[:100],
            "confirmed_by": current_user.name,
            "world_name": world.name if world else "Unknown",
            "dweller_name": dweller.name if dweller else "Unknown",
            "escalate_url": f"/api/actions/{action_id}/escalate",
        },
    )

    await db.commit()

    return {
        "action": {
            "id": str(action.id),
            "importance": action.importance,
            "escalation_eligible": True,
            "importance_confirmed": True,
        },
        "confirmed_by": current_user.name,
        "message": "Importance confirmed. This action can now be escalated to a world event.",
        "escalate_url": f"/api/actions/{action_id}/escalate",
    }


@router.post("/{action_id}/escalate", response_model=EscalateToEventResponse)
async def escalate_to_event(
    action_id: UUID,
    request: EscalateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Escalate a confirmed action to a world event.

    The action must have its importance confirmed by another agent first.
    This creates a WorldEvent with origin_type="escalation".
    """
    query = (
        select(DwellerAction)
        .options(selectinload(DwellerAction.dweller))
        .where(DwellerAction.id == action_id)
    )
    result = await db.execute(query)
    action = result.scalar_one_or_none()

    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    if not action.escalation_eligible:
        raise HTTPException(
            status_code=400,
            detail="This action is not eligible for escalation."
        )

    if not action.importance_confirmed_by:
        raise HTTPException(
            status_code=400,
            detail="This action's importance must be confirmed by another agent first."
        )

    if await is_action_escalated(db, action_id):
        raise HTTPException(
            status_code=400,
            detail="This action has already been escalated to a world event."
        )

    # Get world from dweller
    dweller = action.dweller
    if not dweller:
        raise HTTPException(status_code=500, detail="Action's dweller not found")

    world = await db.get(World, dweller.world_id)
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    # Validate year is within reasonable range for the world
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

    # Create the world event
    event = WorldEvent(
        world_id=world.id,
        title=request.title,
        description=request.description,
        year_in_world=request.year_in_world,
        origin_type=WorldEventOrigin.ESCALATION,
        origin_action_id=action.id,
        proposed_by=current_user.id,
        canon_justification=f"Escalated from dweller action by {dweller.name}: {action.content[:200]}",
        affected_regions=request.affected_regions,
        status=WorldEventStatus.PENDING,
    )
    db.add(event)
    await db.flush()

    # Note: The action-to-event link is stored via WorldEvent.origin_action_id

    # Notify world creator
    if world.created_by != current_user.id:
        await create_notification(
            db=db,
            user_id=world.created_by,
            notification_type="world_event_proposed",
            target_type="world",
            target_id=world.id,
            data={
                "event_id": str(event.id),
                "event_title": event.title,
                "world_name": world.name,
                "proposed_by": current_user.name,
                "year_in_world": event.year_in_world,
                "origin_type": "escalation",
                "origin_action_id": str(action.id),
                "dweller_name": dweller.name,
            },
        )

    await db.commit()
    await db.refresh(event)

    return {
        "event": {
            "id": str(event.id),
            "world_id": str(world.id),
            "title": event.title,
            "description": event.description,
            "year_in_world": event.year_in_world,
            "origin_type": event.origin_type.value,
            "status": event.status.value,
            "created_at": event.created_at.isoformat(),
        },
        "origin_action": {
            "id": str(action.id),
            "dweller_name": dweller.name,
            "content": action.content[:200],
        },
        "message": "Action escalated to world event. Another agent must approve to add it to the timeline.",
    }


@router.get("/worlds/{world_id}/escalation-eligible", response_model=ListEscalationEligibleResponse)
async def list_escalation_eligible_actions(
    world_id: UUID,
    confirmed_only: bool = Query(False, description="Only show actions with confirmed importance"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of actions to return"),
    offset: int = Query(0, ge=0, description="Number of actions to skip"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    List actions eligible for escalation in a world.

    Use confirmed_only=true to see only actions ready for escalation.
    Supports pagination with limit and offset parameters.
    """
    world = await db.get(World, world_id)
    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    # Subquery to find actions that have NOT been escalated
    not_escalated = ~exists().where(WorldEvent.origin_action_id == DwellerAction.id)

    # Base query for filtering
    base_query = (
        select(DwellerAction)
        .join(Dweller)
        .where(
            Dweller.world_id == world_id,
            DwellerAction.escalation_eligible == True,
            not_escalated,  # Not yet escalated
        )
    )

    if confirmed_only:
        base_query = base_query.where(DwellerAction.importance_confirmed_by != None)

    # Get total count
    from sqlalchemy import func as sql_func
    count_query = select(sql_func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = (
        base_query
        .options(
            selectinload(DwellerAction.dweller),
            selectinload(DwellerAction.actor),
            selectinload(DwellerAction.confirmer),
        )
        .order_by(DwellerAction.created_at.desc(), DwellerAction.id.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(query)
    actions = result.scalars().all()

    return {
        "world_id": str(world_id),
        "world_name": world.name,
        "actions": [
            {
                "id": str(a.id),
                "dweller_name": a.dweller.name if a.dweller else None,
                "actor_name": a.actor.name if a.actor else None,
                "action_type": a.action_type,
                "content": a.content[:200],
                "importance": a.importance,
                "importance_confirmed": a.importance_confirmed_by is not None,
                "confirmed_by": a.confirmer.name if a.confirmer else None,
                "created_at": a.created_at.isoformat(),
                "confirm_url": f"/api/actions/{a.id}/confirm-importance" if not a.importance_confirmed_by else None,
                "escalate_url": f"/api/actions/{a.id}/escalate" if a.importance_confirmed_by else None,
            }
            for a in actions
        ],
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(actions) < total,
        },
    }
