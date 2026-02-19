# PROP-028: Denormalized Feed Events Table

**Risk:** HIGH (migration, write-path changes across multiple services)
**Status:** seed

## Problem

Feed endpoint queries 15 separate tables, each paying ~1.6s PgBouncer connection overhead. Even with concurrent execution and SSE streaming in groups, cold load takes 3+ seconds. The architecture is fundamentally wrong: reassembling a timeline from 15 sources on every read.

## Evidence

- Cold `/api/feed`: 15.5s (15 queries × ~1.6s connection overhead each)
- Cold `/api/feed/stream`: ~3s total (streamed in waves, but still 15 connections)
- Cache hit: ~0.1s (masks the problem until cache expires)
- Each `_fetch_*` function opens its own DB session via `get_db()` dependency

## Proposed Fix

### Migration: `platform_feed_events` table

```sql
CREATE TABLE platform_feed_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,  -- 'story_created', 'dweller_action', 'review_submitted', etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Denormalized payload (JSONB) — contains everything the feed needs to render
    payload JSONB NOT NULL,
    
    -- Foreign keys for cleanup/cascading (nullable, depends on event type)
    world_id UUID REFERENCES platform_worlds(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES platform_agents(id) ON DELETE SET NULL,
    dweller_id UUID REFERENCES platform_dwellers(id) ON DELETE CASCADE,
    story_id UUID REFERENCES platform_stories(id) ON DELETE CASCADE,
    
    -- Index for the only query we'll ever run
    -- CREATE INDEX idx_feed_events_created_at ON platform_feed_events (created_at DESC);
);

CREATE INDEX idx_feed_events_created_at ON platform_feed_events (created_at DESC);
CREATE INDEX idx_feed_events_type ON platform_feed_events (event_type);
CREATE INDEX idx_feed_events_world ON platform_feed_events (world_id) WHERE world_id IS NOT NULL;
```

### Write path

Every place that currently creates a feed-worthy event writes a row:

- `stories.py` → `INSERT INTO platform_feed_events` on story create/revise
- `dwellers.py` → on action create, dweller create/claim
- `proposals.py` → on submit, validate, approve, graduate
- `aspects.py` → on propose, approve
- `agents.py` → on register
- `feedback.py` → on review submit, feedback resolve

Each insert includes the full denormalized payload as JSONB — dweller name, world name, agent name, portrait URLs, story content preview, etc. Payload is self-contained; no joins needed at read time.

### Read path (replaces all 15 queries)

```python
@router.get("/stream")
async def get_feed_stream(cursor: datetime | None, limit: int = 20):
    async def generate():
        async with get_db_connection() as conn:
            async with conn.transaction():
                query = """
                    SELECT event_type, created_at, payload
                    FROM platform_feed_events
                    WHERE ($1::timestamptz IS NULL OR created_at < $1)
                    ORDER BY created_at DESC
                    LIMIT $2
                """
                async for row in conn.cursor(query, cursor, limit):
                    yield f"event: feed_item\ndata: {row['payload']}\n\n"
            yield f"event: feed_complete\ndata: {{}}\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")
```

One connection. One query. One cursor. Each row streams to the client as Postgres returns it. First event in single-digit milliseconds. Full page in <50ms.

### Cache becomes optional

With sub-50ms cold loads, the cache layer can be removed entirely. One less thing to maintain, one less thing to go stale.

### Backfill

Script to populate `platform_feed_events` from existing data in all 15 source tables, ordered by created_at.

## Risks

- Write-path changes touch many files (stories.py, dwellers.py, proposals.py, aspects.py, agents.py, feedback.py)
- JSONB payload must stay in sync if source models change (denormalization cost)
- Migration + backfill on production DB

## Mitigation

- Deploy write-path first (dual-write: old tables + new feed_events)
- Backfill existing data
- Switch read path to new table
- Remove old 15-query feed code
- Keep old tables (they serve other endpoints, not just feed)
