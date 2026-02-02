"""Feed API endpoints."""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import get_db, World, Dweller, DwellerAction

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("")
async def get_feed(
    cursor: datetime | None = Query(None, description="Pagination cursor (ISO timestamp)"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get mixed feed of new worlds and dweller activity.

    Returns items sorted by recency, with pagination via cursor.
    """
    cutoff = cursor or (datetime.utcnow() - timedelta(days=7))

    # Fetch new worlds
    worlds_query = (
        select(World)
        .where(
            and_(
                World.is_active == True,
                World.created_at >= cutoff,
            )
        )
        .order_by(World.created_at.desc())
        .limit(limit)
    )
    worlds_result = await db.execute(worlds_query)
    new_worlds = worlds_result.scalars().all()

    # Fetch recent dweller activity
    activity_query = (
        select(DwellerAction)
        .options(selectinload(DwellerAction.dweller).selectinload(Dweller.world))
        .where(DwellerAction.created_at >= cutoff)
        .order_by(DwellerAction.created_at.desc())
        .limit(limit)
    )
    activity_result = await db.execute(activity_query)
    recent_activity = activity_result.scalars().all()

    # Build feed items
    feed_items: list[dict[str, Any]] = []

    for world in new_worlds:
        feed_items.append({
            "type": "world_created",
            "sort_date": world.created_at.isoformat(),
            "id": str(world.id),
            "name": world.name,
            "premise": world.premise,
            "year_setting": world.year_setting,
            "causal_chain": world.causal_chain,
            "created_at": world.created_at.isoformat(),
            "dweller_count": world.dweller_count,
            "follower_count": world.follower_count,
        })

    for action in recent_activity:
        feed_items.append({
            "type": "dweller_action",
            "sort_date": action.created_at.isoformat(),
            "id": str(action.id),
            "action_type": action.action_type,
            "content": action.content,
            "target": action.target,
            "created_at": action.created_at.isoformat(),
            "dweller": {
                "id": str(action.dweller.id),
                "name": action.dweller.name,
                "role": action.dweller.role,
            },
            "world": {
                "id": str(action.dweller.world.id),
                "name": action.dweller.world.name,
                "year_setting": action.dweller.world.year_setting,
            },
        })

    # Sort by date and paginate
    feed_items.sort(key=lambda x: x["sort_date"], reverse=True)
    paginated = feed_items[:limit]

    next_cursor = None
    if len(paginated) == limit:
        next_cursor = paginated[-1]["sort_date"]

    return {
        "items": paginated,
        "next_cursor": next_cursor,
    }
