"""World signals aggregation for agent heartbeat.

Provides aggregate statistics about world activity to help agents understand
where attention is needed. No LLM interpretation - just raw counts and patterns
that the agent's OpenClaw LLM can interpret.
"""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db import (
    Dweller,
    DwellerAction,
    World,
    Aspect,
    AspectStatus,
    WorldEvent,
    WorldEventStatus,
    ReviewFeedback,
    User,
)


async def build_world_signals(
    db: AsyncSession,
    user_id: UUID,
    since: datetime | None = None
) -> dict[str, Any]:
    """
    Build aggregate signals for all worlds where the user has created content.

    Args:
        db: Database session
        user_id: The user to build signals for
        since: Time period to aggregate over (defaults to last 24 hours)

    Returns:
        Dictionary mapping world_id to aggregate signals
    """
    # Default to last 24 hours
    if since is None:
        since = datetime.utcnow() - timedelta(hours=24)

    # Find all worlds where this user has created content
    # (proposals, aspects, dwellers, stories, or is a validator)
    worlds_query = (
        select(World)
        .distinct()
        .outerjoin(Aspect, Aspect.world_id == World.id)
        .outerjoin(Dweller, Dweller.world_id == World.id)
        .where(
            (World.created_by == user_id)
            | (Aspect.agent_id == user_id)
            | (Dweller.created_by == user_id)
            | (Dweller.inhabited_by == user_id)
        )
    )

    result = await db.execute(worlds_query)
    worlds = result.scalars().all()

    signals: dict[str, Any] = {}

    for world in worlds:
        # Action counts by region
        actions_by_region_query = (
            select(
                Dweller.current_region,
                func.count(DwellerAction.id).label("count")
            )
            .select_from(DwellerAction)
            .join(Dweller, DwellerAction.dweller_id == Dweller.id)
            .where(
                Dweller.world_id == world.id,
                DwellerAction.created_at >= since,
                Dweller.current_region.isnot(None),
            )
            .group_by(Dweller.current_region)
        )

        region_result = await db.execute(actions_by_region_query)
        actions_by_region = {row[0]: row[1] for row in region_result.all()}

        # Action counts by type
        actions_by_type_query = (
            select(
                DwellerAction.action_type,
                func.count(DwellerAction.id).label("count")
            )
            .select_from(DwellerAction)
            .join(Dweller, DwellerAction.dweller_id == Dweller.id)
            .where(
                Dweller.world_id == world.id,
                DwellerAction.created_at >= since,
            )
            .group_by(DwellerAction.action_type)
        )

        type_result = await db.execute(actions_by_type_query)
        actions_by_type = {row[0]: row[1] for row in type_result.all()}

        # Total action count
        total_actions = sum(actions_by_type.values())

        # Active dwellers (those who acted in the period)
        active_dwellers_query = (
            select(func.count(func.distinct(DwellerAction.dweller_id)))
            .select_from(DwellerAction)
            .join(Dweller, DwellerAction.dweller_id == Dweller.id)
            .where(
                Dweller.world_id == world.id,
                DwellerAction.created_at >= since,
            )
        )

        active_result = await db.execute(active_dwellers_query)
        active_dwellers = active_result.scalar() or 0

        # Active conversations (speak actions with in_reply_to)
        conversations_query = (
            select(func.count(func.distinct(DwellerAction.in_reply_to_action_id)))
            .select_from(DwellerAction)
            .join(Dweller, DwellerAction.dweller_id == Dweller.id)
            .where(
                Dweller.world_id == world.id,
                DwellerAction.action_type == "speak",
                DwellerAction.in_reply_to_action_id.isnot(None),
                DwellerAction.created_at >= since,
            )
        )

        conv_result = await db.execute(conversations_query)
        active_conversations = conv_result.scalar() or 0

        # Pending reviews
        pending_reviews_query = (
            select(func.count(Aspect.id))
            .where(
                Aspect.world_id == world.id,
                Aspect.status == AspectStatus.VALIDATING,
            )
        )

        pending_result = await db.execute(pending_reviews_query)
        pending_reviews = pending_result.scalar() or 0

        # Recent canon changes
        canon_changes_query = (
            select(func.count(Aspect.id))
            .where(
                Aspect.world_id == world.id,
                Aspect.status == AspectStatus.APPROVED,
                Aspect.updated_at >= since,
            )
        )

        canon_result = await db.execute(canon_changes_query)
        recent_canon_changes = canon_result.scalar() or 0

        signals[str(world.id)] = {
            "world_name": world.name,
            "period": f"last_{int((datetime.utcnow() - since).total_seconds() / 3600)}h",
            "action_count": total_actions,
            "active_dwellers": active_dwellers,
            "actions_by_region": actions_by_region,
            "actions_by_type": actions_by_type,
            "active_conversations": active_conversations,
            "pending_reviews": pending_reviews,
            "recent_canon_changes": recent_canon_changes,
        }

    return signals
