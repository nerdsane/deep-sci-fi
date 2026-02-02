"""Feed API endpoints."""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import get_db, World, Story, Conversation, ConversationMessage, Dweller

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("")
async def get_feed(
    cursor: datetime | None = Query(None, description="Pagination cursor (ISO timestamp)"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get mixed feed of stories, conversations, and new worlds.

    Returns items sorted by recency, with pagination via cursor.
    """
    cutoff = cursor or (datetime.utcnow() - timedelta(days=7))

    # Fetch recent stories with world info
    stories_query = (
        select(Story)
        .options(selectinload(Story.world))
        .where(Story.created_at >= cutoff)
        .order_by(Story.created_at.desc())
        .limit(limit)
    )
    stories_result = await db.execute(stories_query)
    stories = stories_result.scalars().all()

    # Fetch active conversations with world info
    conversations_query = (
        select(Conversation)
        .options(
            selectinload(Conversation.world),
            selectinload(Conversation.messages),
        )
        .where(
            and_(
                Conversation.is_active == True,
                Conversation.updated_at >= cutoff,
            )
        )
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )
    conversations_result = await db.execute(conversations_query)
    conversations = conversations_result.scalars().all()

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
        .limit(10)
    )
    worlds_result = await db.execute(worlds_query)
    new_worlds = worlds_result.scalars().all()

    # Get dwellers for conversations
    all_participant_ids: set[str] = set()
    for conv in conversations:
        all_participant_ids.update(conv.participants)

    dwellers_map: dict[str, Dweller] = {}
    if all_participant_ids:
        dwellers_query = select(Dweller).where(
            Dweller.id.in_([UUID(p) for p in all_participant_ids])
        )
        dwellers_result = await db.execute(dwellers_query)
        for dweller in dwellers_result.scalars().all():
            dwellers_map[str(dweller.id)] = dweller

    # Build feed items
    feed_items: list[dict[str, Any]] = []

    for story in stories:
        feed_items.append({
            "type": "story",
            "sort_date": story.created_at.isoformat(),
            "data": {
                "id": str(story.id),
                "world_id": str(story.world_id),
                "type": story.type.value,
                "title": story.title,
                "description": story.description,
                "video_url": story.video_url,
                "thumbnail_url": story.thumbnail_url,
                "duration_seconds": story.duration_seconds,
                "created_at": story.created_at.isoformat(),
                "view_count": story.view_count,
                "reaction_counts": story.reaction_counts,
            },
            "world": {
                "id": str(story.world.id),
                "name": story.world.name,
                "year_setting": story.world.year_setting,
            },
        })

    for conv in conversations:
        conv_dwellers = [
            {
                "id": str(dwellers_map[p].id),
                "name": dwellers_map[p].name,
                "role": dwellers_map[p].role,
            }
            for p in conv.participants
            if p in dwellers_map
        ]

        feed_items.append({
            "type": "conversation",
            "sort_date": conv.updated_at.isoformat(),
            "data": {
                "id": str(conv.id),
                "world_id": str(conv.world_id),
                "participants": conv.participants,
                "messages": [
                    {
                        "id": str(msg.id),
                        "dweller_id": str(msg.dweller_id),
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat(),
                    }
                    for msg in sorted(conv.messages, key=lambda m: m.timestamp)[-5:]
                ],
                "updated_at": conv.updated_at.isoformat(),
            },
            "world": {
                "id": str(conv.world.id),
                "name": conv.world.name,
                "year_setting": conv.world.year_setting,
            },
            "dwellers": conv_dwellers,
        })

    for world in new_worlds:
        feed_items.append({
            "type": "world_created",
            "sort_date": world.created_at.isoformat(),
            "data": {
                "id": str(world.id),
                "name": world.name,
                "premise": world.premise,
                "year_setting": world.year_setting,
                "causal_chain": world.causal_chain,
                "created_at": world.created_at.isoformat(),
                "dweller_count": world.dweller_count,
                "follower_count": world.follower_count,
            },
        })

    # Sort by date and paginate
    feed_items.sort(key=lambda x: x["sort_date"], reverse=True)
    paginated = feed_items[:limit]

    next_cursor = None
    if len(paginated) == limit:
        next_cursor = paginated[-1]["sort_date"]

    return {
        "items": [
            {"type": item["type"], **item.get("data", {}), **{k: v for k, v in item.items() if k not in ("type", "sort_date", "data")}}
            for item in paginated
        ],
        "next_cursor": next_cursor,
    }
