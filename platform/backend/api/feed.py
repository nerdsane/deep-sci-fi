"""Feed API endpoints — unified activity stream from denormalized feed events table.

PROP-028: Replaced 15-query reassembly with single-table reads.
One connection, one query, sub-50ms cold loads.
"""

import json
import logging
from contextlib import nullcontext
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db, FeedEvent
from utils.clock import now as utc_now

logger = logging.getLogger(__name__)

# Try to import logfire for observability (graceful degradation)
try:
    import logfire
    _logfire_available = True
except ImportError:
    _logfire_available = False


def _span(name: str):
    """Return a logfire span if available, otherwise a no-op context manager."""
    if _logfire_available:
        return logfire.span(name)
    return nullcontext()


router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("/stream")
async def get_feed_stream(
    cursor: str | None = Query(None, description="Pagination cursor (ISO timestamp)"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Get unified feed of all platform activity via Server-Sent Events.

    Reads from the denormalized `platform_feed_events` table.
    One query, one connection, sub-50ms.

    SSE Events:
    - event: feed_items, data: {"items": [...], "partial": false}
    - event: feed_complete, data: {"next_cursor": "...", "total_items": N}
    """

    async def event_generator():
        start_time = utc_now()

        with _span("feed_stream_query"):
            query = (
                select(FeedEvent)
                .order_by(FeedEvent.created_at.desc())
                .limit(limit)
            )
            if cursor:
                try:
                    cursor_dt = datetime.fromisoformat(cursor)
                    query = query.where(FeedEvent.created_at < cursor_dt)
                except ValueError:
                    pass  # Ignore malformed cursor, return from beginning

            result = await db.execute(query)
            events = result.scalars().all()

        items = []
        for event in events:
            item = dict(event.payload) if isinstance(event.payload, dict) else event.payload
            item["type"] = event.event_type
            item["sort_date"] = event.created_at.isoformat()
            items.append(item)

        # Send all items in one batch
        yield f"event: feed_items\ndata: {json.dumps({'items': items, 'partial': False})}\n\n"

        # Compute next cursor
        next_cursor = items[-1]["sort_date"] if items else None

        time_to_complete = (utc_now() - start_time).total_seconds()
        if _logfire_available:
            logfire.info(
                "feed_stream_complete",
                time_to_complete_seconds=time_to_complete,
                total_items=len(items),
                has_more=next_cursor is not None,
            )

        yield f"event: feed_complete\ndata: {json.dumps({'next_cursor': next_cursor, 'total_items': len(items)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
