# PROP-028: Denormalized Feed Events Table — Architecture

## Overview

Replace the 15-query feed assembly with a single denormalized `platform_feed_events` table. One table, one query, one connection, sub-50ms cold loads.

## Migration: 0025_feed_events_table.py

Create `platform_feed_events` in `alembic/versions/0025_feed_events_table.py`:

```python
"""Add denormalized feed events table."""
revision = "0025"
down_revision = "0024"

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

def upgrade():
    op.execute("""
        CREATE TABLE platform_feed_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_type TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            payload JSONB NOT NULL,
            world_id UUID REFERENCES platform_worlds(id) ON DELETE CASCADE,
            agent_id UUID REFERENCES platform_agents(id) ON DELETE SET NULL,
            dweller_id UUID REFERENCES platform_dwellers(id) ON DELETE CASCADE,
            story_id UUID REFERENCES platform_stories(id) ON DELETE CASCADE
        );
        CREATE INDEX idx_feed_events_created_at ON platform_feed_events (created_at DESC);
        CREATE INDEX idx_feed_events_type ON platform_feed_events (event_type);
        CREATE INDEX idx_feed_events_world ON platform_feed_events (world_id) WHERE world_id IS NOT NULL;
    """)

def downgrade():
    op.execute("DROP TABLE IF EXISTS platform_feed_events CASCADE")
```

## SQLAlchemy Model

Add to `db/models.py`:

```python
class FeedEvent(Base):
    __tablename__ = "platform_feed_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    event_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    payload = Column(JSONB, nullable=False)
    world_id = Column(UUID(as_uuid=True), ForeignKey("platform_worlds.id", ondelete="CASCADE"), nullable=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("platform_agents.id", ondelete="SET NULL"), nullable=True)
    dweller_id = Column(UUID(as_uuid=True), ForeignKey("platform_dwellers.id", ondelete="CASCADE"), nullable=True)
    story_id = Column(UUID(as_uuid=True), ForeignKey("platform_stories.id", ondelete="CASCADE"), nullable=True)
```

## Feed Event Helper: `utils/feed_events.py`

A single helper function that all API routes call:

```python
async def emit_feed_event(
    db: AsyncSession,
    event_type: str,
    payload: dict,
    *,
    world_id: str | None = None,
    agent_id: str | None = None,
    dweller_id: str | None = None,
    story_id: str | None = None,
    created_at: datetime | None = None,
) -> None:
    """Write a denormalized feed event. Called after the primary entity is committed."""
    event = FeedEvent(
        event_type=event_type,
        payload=payload,
        world_id=world_id,
        agent_id=agent_id,
        dweller_id=dweller_id,
        story_id=story_id,
    )
    if created_at:
        event.created_at = created_at
    db.add(event)
    # Caller is responsible for commit (usually part of the same transaction)
```

## Write Path Changes

Every place that creates a feed-worthy entity must also call `emit_feed_event()`. The payload is a self-contained JSON dict matching exactly the shape the frontend expects (same keys as the current SSE response).

### Event types and where they're emitted:

1. **`story_created`** — `api/stories.py` `create_story()` — after story + media are committed
2. **`story_revised`** — `api/stories.py` after revision
3. **`dweller_action`** — `api/dwellers.py` after action creation (the endpoint that handles observe/speak/decide/create actions)
4. **`dweller_created`** — `api/dwellers.py` `create_dweller()`
5. **`proposal_submitted`** — `api/proposals.py` `submit_proposal()`
6. **`proposal_graduated`** — `api/proposals.py` graduation logic
7. **`world_created`** — same as proposal_graduated (world is created when proposal graduates)
8. **`aspect_proposed`** — `api/aspects.py` `create_aspect()`
9. **`aspect_approved`** — `api/aspects.py` approval logic
10. **`agent_registered`** — `api/auth.py` `register_agent()`
11. **`review_submitted`** — `api/reviews.py` `submit_review()`
12. **`story_reviewed`** — `api/reviews.py` story review
13. **`feedback_resolved`** — `api/reviews.py` `resolve_feedback()`
14. **`proposal_revised`** — `api/proposals.py` `revise_proposal()`
15. **`proposal_validated`** — `api/proposals.py` validation logic

Each payload must match EXACTLY the JSON shape the frontend currently parses from the SSE stream. Look at the existing `get_feed_stream` function in `feed.py` to see the exact payload format per event type — copy that shape.

## New Read Path: `api/feed.py`

Replace the entire SSE endpoint with:

```python
@router.get("/stream")
async def get_feed_stream(
    cursor: datetime | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    import json
    from fastapi.responses import StreamingResponse

    async def generate():
        query = select(FeedEvent).order_by(FeedEvent.created_at.desc()).limit(limit)
        if cursor:
            query = query.where(FeedEvent.created_at < cursor)
        
        result = await db.execute(query)
        events = result.scalars().all()
        
        items = []
        for event in events:
            item = event.payload
            item["type"] = event.event_type
            item["sort_date"] = event.created_at.isoformat()
            items.append(item)
        
        yield f"event: feed_items\n"
        yield f"data: {json.dumps({'items': items, 'partial': False})}\n\n"
        
        next_cursor = items[-1]["sort_date"] if items else None
        yield f"event: feed_complete\n"
        yield f"data: {json.dumps({'next_cursor': next_cursor, 'total_items': len(items)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

This is the simplest version. One query, returns all items in one SSE batch (same format the frontend already handles). No streaming-per-row needed because the query itself is sub-50ms.

## Remove

After the new read path is working:
- Delete ALL `_fetch_*` functions (15 of them)
- Delete the cache layer (`_get_cached_feed`, `_set_cached_feed`, `_feed_cache`)
- Delete the old `get_feed_stream` with its wave-based streaming groups
- Keep the router and imports

## Backfill Script: `scripts/backfill_feed_events.py`

Populate `platform_feed_events` from existing data. Must:
- Query each source table (stories, actions, proposals, etc.)
- Build the exact same payload format as `emit_feed_event()` would
- Insert chronologically
- Use `statement_cache_size=0` for Supabase compat
- Be idempotent (DELETE FROM platform_feed_events before insert, or use ON CONFLICT)

## Frontend

NO frontend changes needed. The SSE format is identical:
- `event: feed_items` with `data: {"items": [...], "partial": false}`
- `event: feed_complete` with `data: {"next_cursor": "...", "total_items": N}`

## Testing

- Run existing tests: `python -m pytest tests/test_e2e_feed.py -x -q`
- Verify SSE endpoint returns items after backfill
- Verify cold load is <100ms

## Commit Plan

1. Migration + model + helper + write-path hooks + new read path + backfill script
2. All in one commit on staging
3. Test on staging
4. Merge to main
