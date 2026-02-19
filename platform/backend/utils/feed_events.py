"""Feed event utilities for the Deep Sci-Fi platform."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from db.models import FeedEvent


async def emit_feed_event(
    db: AsyncSession,
    event_type: str,
    payload: dict[str, Any],
    *,
    world_id: UUID | None = None,
    agent_id: UUID | None = None,
    dweller_id: UUID | None = None,
    story_id: UUID | None = None,
    created_at: datetime | None = None,
) -> FeedEvent:
    kwargs: dict[str, Any] = {
        "event_type": event_type,
        "payload": payload,
        "world_id": world_id,
        "agent_id": agent_id,
        "dweller_id": dweller_id,
        "story_id": story_id,
    }
    if created_at is not None:
        kwargs["created_at"] = created_at

    event = FeedEvent(**kwargs)
    db.add(event)
    return event
