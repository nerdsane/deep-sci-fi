"""Dweller Actions API endpoints.

Endpoints for managing high-importance dweller actions:
- Confirming importance for escalation eligibility
- Escalating confirmed actions to world events
"""

import asyncio
import logging
from utils.clock import now as utc_now
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import exists, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from utils.deterministic import deterministic_uuid4
from db import (
    get_db,
    User,
    DwellerAction,
    Dweller,
    World,
    WorldEvent,
    WorldEventPropagation,
    ActionCompositionQueue,
    IdempotencyKey,
)
from db.models import WorldEventStatus, WorldEventOrigin
from services.action_resilience import (
    ACTION_IDEMPOTENCY_ENDPOINT,
    ActionSubmissionPayload,
    build_action_response,
    create_action_record,
    get_recent_idempotency_record,
    parse_stored_idempotency_response,
    prune_expired_idempotency_keys,
)
from .auth import get_current_user
from utils.deployment import get_forced_deployment_status, get_retry_after_seconds
from utils.notifications import create_notification
from schemas.actions import (
    GetActionResponse,
    ConfirmImportanceResponse,
    EscalateToEventResponse,
    ListEscalationEligibleResponse,
    NominateActionResponse,
)

logger = logging.getLogger(__name__)


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


def _normalized_escalation_status(action: DwellerAction) -> str:
    """Normalize nullable legacy statuses to the default workflow state."""
    return action.escalation_status or "eligible"


def _format_world_event_core_memory(event: WorldEvent) -> str:
    """Format a concise world fact string for core memory storage."""
    description = " ".join((event.description or "").split())
    if len(description) > 240:
        description = f"{description[:237].rstrip()}..."
    if description:
        return f"World fact: {event.title} ({event.year_in_world}). {description}"
    return f"World fact: {event.title} ({event.year_in_world})."


router = APIRouter(prefix="/actions", tags=["actions"])

# Keep strong references to fire-and-forget tasks so they're not GC'd before completion
_background_tasks: set[asyncio.Task[Any]] = set()


async def propagate_world_event_to_core_memories(world_event_id: UUID) -> None:
    """Fan out an escalated world event into all dwellers' core memories."""
    from db.database import SessionLocal

    try:
        async with SessionLocal() as db:
            event = await db.get(WorldEvent, world_event_id)
            if event is None:
                return

            dwellers_result = await db.execute(
                select(Dweller)
                .where(Dweller.world_id == event.world_id)
                .order_by(Dweller.created_at.asc(), Dweller.id.asc())
            )
            propagation_dwellers = dwellers_result.scalars().all()
            if not propagation_dwellers:
                return

            fact_text = _format_world_event_core_memory(event)
            propagated_at = utc_now()

            for dweller in propagation_dwellers:
                propagation_stmt = (
                    pg_insert(WorldEventPropagation.__table__)
                    .values(
                        id=deterministic_uuid4(),
                        world_event_id=event.id,
                        dweller_id=dweller.id,
                        propagated_at=propagated_at,
                    )
                    .on_conflict_do_nothing(index_elements=["world_event_id", "dweller_id"])
                    .returning(WorldEventPropagation.id)
                )
                inserted_id = (await db.execute(propagation_stmt)).scalar_one_or_none()
                if inserted_id is None:
                    continue

                core_memories = list(dweller.core_memories or [])
                if fact_text not in core_memories:
                    core_memories.append(fact_text)
                    dweller.core_memories = core_memories

            await db.commit()
    except Exception:
        logger.exception("Failed to propagate world event %s to core memories", world_event_id)


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


class ActionSubmitRequest(BaseModel):
    """Request to submit or compose a dweller action."""

    dweller_id: UUID = Field(..., description="Dweller taking the action")
    action_type: str = Field(..., min_length=1, max_length=50)
    content: str = Field(..., min_length=1)
    target: str | None = Field(default=None)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    dialogue: str | None = Field(default=None)
    stage_direction: str | None = Field(default=None)
    in_reply_to_action_id: UUID | None = Field(default=None)


def _raise_if_deploying() -> None:
    """Block action writes during deployment windows."""
    if get_forced_deployment_status() != "deploying":
        return
    retry_after = get_retry_after_seconds()
    raise HTTPException(
        status_code=503,
        detail={
            "error": "Action submission unavailable during deployment",
            "blocker_type": "deployment",
            "deployment_status": "deploying",
            "retry_after_seconds": retry_after,
            "how_to_fix": f"Deployment is in progress. Wait {retry_after} seconds, then retry your request.",
            "next_steps": [
                f"Wait {retry_after} seconds",
                "Retry the action submission",
                "Check GET /api/health for deployment_status == 'stable' before retrying",
            ],
        },
        headers={"Retry-After": str(retry_after)},
    )


def _resolve_idempotency_key(
    *,
    idempotency_key: str | None,
    x_idempotency_key: str | None,
) -> str | None:
    return idempotency_key or x_idempotency_key


def _validate_idempotency_key(value: str) -> None:
    try:
        UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key must be a valid UUID",
        ) from exc


# ============================================================================
# Action Endpoints
# ============================================================================


@router.post("/compose", responses={200: {"description": "Queued action composition result"}})
async def compose_action(
    request: ActionSubmitRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Buffer an action for resilient background submission."""
    _raise_if_deploying()

    try:
        payload = ActionSubmissionPayload.from_dict(request.model_dump(mode="json"))
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": str(exc),
                "blocker_type": "validation",
                "how_to_fix": "Fix the invalid field value and resubmit.",
                "next_steps": ["Review the error message", "Correct the field and retry"],
            },
        ) from exc
    key = _resolve_idempotency_key(
        idempotency_key=idempotency_key,
        x_idempotency_key=x_idempotency_key,
    ) or str(uuid4())
    _validate_idempotency_key(key)

    existing_result = await db.execute(
        select(ActionCompositionQueue).where(ActionCompositionQueue.idempotency_key == key)
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        return {
            "queue_id": str(existing.id),
            "status": "queued" if existing.submitted_at is None else "submitted",
            "idempotency_key": existing.idempotency_key,
            "composed_at": existing.composed_at.isoformat(),
            "submitted_at": existing.submitted_at.isoformat() if existing.submitted_at else None,
            "submission_attempts": existing.submission_attempts,
        }

    dweller = await db.get(Dweller, payload.dweller_id)
    if not dweller:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Dweller not found",
                "blocker_type": "not_found",
                "dweller_id": str(payload.dweller_id),
                "how_to_fix": "Verify the dweller_id is correct.",
                "next_steps": [
                    "Check the dweller_id in your request",
                    "List your dwellers via GET /api/dwellers/worlds/{world_id}/dwellers",
                ],
            },
        )
    if dweller.inhabited_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "You are not inhabiting this dweller",
                "blocker_type": "auth",
                "dweller_id": str(payload.dweller_id),
                "how_to_fix": "Claim this dweller first, or use a dweller you already inhabit.",
                "next_steps": [
                    f"POST /api/dwellers/{payload.dweller_id}/claim to claim this dweller",
                    "Or list your claimed dwellers and use one of those IDs",
                ],
            },
        )

    queue_item = ActionCompositionQueue(
        agent_id=current_user.id,
        dweller_id=payload.dweller_id,
        action_type=payload.action_type,
        payload=payload.to_json_dict(),
        idempotency_key=key,
        next_attempt_at=utc_now(),
    )
    db.add(queue_item)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        race_result = await db.execute(
            select(ActionCompositionQueue).where(ActionCompositionQueue.idempotency_key == key)
        )
        race_item = race_result.scalar_one_or_none()
        if race_item is None:
            raise
        return {
            "queue_id": str(race_item.id),
            "status": "queued" if race_item.submitted_at is None else "submitted",
            "idempotency_key": race_item.idempotency_key,
            "composed_at": race_item.composed_at.isoformat(),
            "submitted_at": race_item.submitted_at.isoformat() if race_item.submitted_at else None,
            "submission_attempts": race_item.submission_attempts,
        }

    await db.refresh(queue_item)
    return {
        "queue_id": str(queue_item.id),
        "status": "queued",
        "idempotency_key": queue_item.idempotency_key,
        "composed_at": queue_item.composed_at.isoformat(),
        "submitted_at": None,
        "submission_attempts": queue_item.submission_attempts,
    }


@router.post("", responses={200: {"description": "Submitted action result"}})
async def submit_action(
    request: ActionSubmitRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Submit a dweller action with 24-hour idempotent replay support."""
    _raise_if_deploying()

    try:
        payload = ActionSubmissionPayload.from_dict(request.model_dump(mode="json"))
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": str(exc),
                "blocker_type": "validation",
                "how_to_fix": "Fix the invalid field value and resubmit.",
                "next_steps": ["Review the error message", "Correct the field and retry"],
            },
        ) from exc
    key = _resolve_idempotency_key(
        idempotency_key=idempotency_key,
        x_idempotency_key=x_idempotency_key,
    )
    if key is not None:
        _validate_idempotency_key(key)

    await prune_expired_idempotency_keys(db)

    idempotency_record: IdempotencyKey | None = None
    if key is not None:
        existing_any_endpoint = await db.get(IdempotencyKey, key)
        if existing_any_endpoint and existing_any_endpoint.endpoint != ACTION_IDEMPOTENCY_ENDPOINT:
            if existing_any_endpoint.created_at >= utc_now() - timedelta(hours=24):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "Idempotency-Key already used for another endpoint within 24 hours",
                        "blocker_type": "conflict",
                        "idempotency_key": key,
                        "how_to_fix": "Use a new unique UUID as your Idempotency-Key.",
                        "next_steps": [
                            "Generate a fresh UUID for your Idempotency-Key header",
                            "Resubmit with the new key",
                        ],
                    },
                )
            await db.delete(existing_any_endpoint)
            await db.flush()

        idempotency_record = await get_recent_idempotency_record(db, key=key)

        if idempotency_record and idempotency_record.status == "completed":
            replay = parse_stored_idempotency_response(idempotency_record.response_body)
            if replay is not None:
                return JSONResponse(
                    status_code=200,
                    content=replay,
                    headers={"X-Idempotent-Replay": "true"},
                )

        if idempotency_record and idempotency_record.status == "in_progress":
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "Request is already in progress for this Idempotency-Key",
                    "blocker_type": "conflict",
                    "idempotency_key": key,
                    "how_to_fix": "Wait a moment and retry; the in-progress request will complete shortly.",
                    "next_steps": [
                        "Wait 1-2 seconds for the in-progress request to complete",
                        "Retry with the same Idempotency-Key to get the cached response",
                    ],
                },
            )

        if idempotency_record is None:
            idempotency_record = IdempotencyKey(
                key=key,
                user_id=current_user.id,
                endpoint=ACTION_IDEMPOTENCY_ENDPOINT,
                status="in_progress",
                created_at=utc_now(),
            )
            db.add(idempotency_record)
        else:
            idempotency_record.status = "in_progress"
            idempotency_record.response_status = None
            idempotency_record.response_body = None
            idempotency_record.completed_at = None

    action, dweller = await create_action_record(
        db,
        actor_id=current_user.id,
        payload=payload,
    )
    await db.flush()
    await db.refresh(action)

    response_payload = build_action_response(
        action=action,
        dweller=dweller,
        idempotency_key=key,
    )

    if idempotency_record is not None:
        idempotency_record.status = "completed"
        idempotency_record.response_status = 201
        idempotency_record.response_body = response_payload
        idempotency_record.completed_at = utc_now()

    await db.commit()
    return JSONResponse(status_code=201, content=response_payload)


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
            "escalation_status": _normalized_escalation_status(action),
            "nominated_at": action.nominated_at.isoformat() if action.nominated_at else None,
            "nomination_count": action.nomination_count or 0,
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

    status = _normalized_escalation_status(action)
    if status in {"rejected", "expired"}:
        raise HTTPException(
            status_code=400,
            detail=f"This action cannot be confirmed because escalation_status is '{status}'.",
        )
    if status == "accepted":
        raise HTTPException(
            status_code=400,
            detail="This action has already been escalated and accepted.",
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
            "escalation_status": _normalized_escalation_status(action),
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

    status = _normalized_escalation_status(action)
    if status in {"rejected", "expired"}:
        raise HTTPException(
            status_code=400,
            detail=f"This action cannot be escalated because escalation_status is '{status}'.",
        )
    if status == "accepted":
        raise HTTPException(
            status_code=400,
            detail="This action has already been escalated to a world event.",
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
    action.escalation_status = "accepted"

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

    # Propagate in background so escalation latency is not tied to world size.
    task = asyncio.create_task(propagate_world_event_to_core_memories(event.id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

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


@router.post("/{action_id}/nominate", response_model=NominateActionResponse)
async def nominate_action_for_escalation(
    action_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Nominate your own escalation-eligible action for community escalation review."""
    query = (
        select(DwellerAction)
        .options(selectinload(DwellerAction.dweller))
        .where(DwellerAction.id == action_id)
    )
    result = await db.execute(query)
    action = result.scalar_one_or_none()

    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    if action.actor_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only nominate your own actions for escalation review.",
        )

    if not action.escalation_eligible:
        raise HTTPException(
            status_code=400,
            detail=(
                "This action is not eligible for nomination. "
                "Importance must be >= 0.8."
            ),
        )

    status = _normalized_escalation_status(action)
    if status == "accepted":
        raise HTTPException(
            status_code=400,
            detail="This action is already accepted and escalated.",
        )
    if status in {"rejected", "expired"}:
        raise HTTPException(
            status_code=400,
            detail=f"This action cannot be nominated because escalation_status is '{status}'.",
        )

    action.nomination_count = (action.nomination_count or 0) + 1
    action.nominated_at = utc_now()
    action.escalation_status = "nominated"

    await db.commit()

    if status == "eligible":
        message = "Action nominated for escalation review."
    else:
        message = "Action nomination refreshed and prioritized for escalation review."

    return {
        "success": True,
        "action_id": str(action.id),
        "escalation_status": action.escalation_status,
        "nomination_count": action.nomination_count,
        "nominated_at": action.nominated_at.isoformat(),
        "message": message,
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
    active_status = or_(
        DwellerAction.escalation_status.is_(None),
        DwellerAction.escalation_status.in_(["eligible", "nominated"]),
    )

    # Base query for filtering
    base_query = (
        select(DwellerAction)
        .join(Dweller)
        .where(
            Dweller.world_id == world_id,
            DwellerAction.escalation_eligible == True,
            not_escalated,  # Not yet escalated
            active_status,
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
                "escalation_status": _normalized_escalation_status(a),
                "nominated_at": a.nominated_at.isoformat() if a.nominated_at else None,
                "nomination_count": a.nomination_count or 0,
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
