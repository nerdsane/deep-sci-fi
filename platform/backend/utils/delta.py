"""Delta calculation for dweller perception.

Computes what has changed in the world since a dweller's last action.
This enables agents to perceive only new events rather than re-processing
the entire world state every time.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import Dweller, DwellerAction, Aspect, WorldEvent, AspectStatus, WorldEventStatus


async def calculate_dweller_delta(
    db: AsyncSession,
    dweller: Dweller,
    since: datetime | None = None
) -> dict[str, Any]:
    """
    Calculate what has changed in the world since the dweller's last action.

    Args:
        db: Database session
        dweller: The dweller to calculate delta for
        since: Timestamp to calculate delta from (defaults to dweller.last_action_at)

    Returns:
        Delta dictionary with new actions, dweller movements, canon changes, etc.
    """
    # Use provided timestamp or dweller's last action time
    # If dweller has never acted, use their creation time
    delta_since = since or dweller.last_action_at or dweller.created_at

    delta = {
        "since": delta_since.isoformat(),
        "new_actions_in_region": [],
        "arrived_dwellers": [],
        "departed_dwellers": [],
        "canon_changes": [],
        "new_conversations": 0,
        "world_events": [],
    }

    # 1. New actions in the world (excluding own actions)
    new_actions_query = (
        select(DwellerAction)
        .options(selectinload(DwellerAction.dweller))
        .where(
            # In the same world
            DwellerAction.dweller_id.in_(
                select(Dweller.id).where(Dweller.world_id == dweller.world_id)
            ),
            # Created since last action
            DwellerAction.created_at > delta_since,
            # Not this dweller's own actions
            DwellerAction.dweller_id != dweller.id,
        )
        .order_by(DwellerAction.created_at.desc())
        .limit(50)  # Cap to avoid huge deltas
    )

    result = await db.execute(new_actions_query)
    new_actions = result.scalars().all()

    # Group by action type and format
    for action in new_actions:
        delta["new_actions_in_region"].append({
            "id": str(action.id),
            "dweller_name": action.dweller.name if action.dweller else "unknown",
            "action_type": action.action_type,
            "summary": action.content[:200] if action.content else "",
            "target": action.target,
            "created_at": action.created_at.isoformat(),
        })

    # 2. Track dweller movements (who arrived/departed in this dweller's region)
    # This requires comparing current region to a historical snapshot
    # For now, we'll detect movements by looking at "move" actions
    if dweller.current_region:
        move_actions = [a for a in new_actions if a.action_type == "move"]

        for move in move_actions:
            # Check if they moved TO or FROM this dweller's region
            # Parse the move action content to determine destination
            # For simplicity, we'll use the action's target field if available
            if move.target and dweller.current_region.lower() in move.target.lower():
                delta["arrived_dwellers"].append({
                    "id": str(move.dweller_id),
                    "name": move.dweller.name if move.dweller else "unknown",
                    "region": dweller.current_region,
                })

    # 3. New conversations involving this dweller
    # Count speak actions where this dweller is the target
    new_speak_to_me = [
        a for a in new_actions
        if a.action_type == "speak"
        and a.target
        and a.target.lower() == dweller.name.lower()
    ]
    delta["new_conversations"] = len(new_speak_to_me)

    # 4. Canon changes (newly approved aspects)
    approved_aspects_query = (
        select(Aspect)
        .where(
            Aspect.world_id == dweller.world_id,
            Aspect.status == AspectStatus.APPROVED,
            Aspect.updated_at > delta_since,
        )
        .order_by(Aspect.updated_at.desc())
        .limit(10)
    )

    aspects_result = await db.execute(approved_aspects_query)
    approved_aspects = aspects_result.scalars().all()

    for aspect in approved_aspects:
        delta["canon_changes"].append({
            "type": "aspect_approved",
            "aspect_type": aspect.aspect_type,
            "title": aspect.title,
            "summary": aspect.premise[:200] if aspect.premise else "",
            "approved_at": aspect.updated_at.isoformat(),
        })

    # 5. New world events
    new_events_query = (
        select(WorldEvent)
        .where(
            WorldEvent.world_id == dweller.world_id,
            WorldEvent.status == WorldEventStatus.APPROVED,
            WorldEvent.approved_at > delta_since if WorldEvent.approved_at else WorldEvent.created_at > delta_since,
        )
        .order_by(WorldEvent.created_at.desc())
        .limit(10)
    )

    events_result = await db.execute(new_events_query)
    world_events = events_result.scalars().all()

    for event in world_events:
        delta["world_events"].append({
            "id": str(event.id),
            "title": event.title,
            "description": event.description[:200] if event.description else "",
            "year_in_world": event.year_in_world,
            "approved_at": event.approved_at.isoformat() if event.approved_at else None,
        })

    return delta
