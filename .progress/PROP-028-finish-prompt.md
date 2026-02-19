# PROP-028 — Finish Implementation

A previous session partially implemented PROP-028. The following are ALREADY DONE:
- Migration `alembic/versions/0025_feed_events_table.py` ✅
- Model `FeedEvent` in `db/models.py` ✅
- Helper `utils/feed_events.py` with `emit_feed_event()` ✅
- Write hooks in `api/stories.py` (story_created) ✅
- Write hooks in `api/dwellers.py` (dweller_action) ✅

## What remains — do these IN ORDER:

### 1. Add remaining write hooks

Add `emit_feed_event()` calls in these files. Pattern: after the primary entity is committed, call emit with a denormalized payload.

**Read `api/feed.py` first** to understand the exact payload shape the frontend expects per event type. The `_fetch_*` functions show what fields are included. Match those EXACTLY.

Files to add hooks:
- `api/proposals.py` — proposal_submitted, proposal_revised, proposal_validated, proposal_graduated (world_created)
- `api/aspects.py` — aspect_proposed, aspect_approved  
- `api/auth.py` — agent_registered
- `api/reviews.py` — review_submitted, feedback_resolved

For each: `from utils.feed_events import emit_feed_event` at top, then call after commit.

### 2. Rewrite the read path in `api/feed.py`

Replace the entire SSE endpoint with a single query against `platform_feed_events`:

```python
@router.get("/stream")
async def get_feed_stream(
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    import json
    from fastapi.responses import StreamingResponse

    async def generate():
        query = select(FeedEvent).order_by(FeedEvent.created_at.desc()).limit(limit)
        if cursor:
            from datetime import datetime
            query = query.where(FeedEvent.created_at < datetime.fromisoformat(cursor))
        
        result = await db.execute(query)
        events = result.scalars().all()
        
        items = []
        for event in events:
            item = dict(event.payload)
            item["type"] = event.event_type
            item["sort_date"] = event.created_at.isoformat()
            items.append(item)
        
        yield f"event: feed_items\ndata: {json.dumps({'items': items, 'partial': False})}\n\n"
        
        next_cursor = items[-1]["sort_date"] if items else None
        yield f"event: feed_complete\ndata: {json.dumps({'next_cursor': next_cursor, 'total_items': len(items)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
```

**Delete ALL old code**: every `_fetch_*` function, the cache layer (`_get_cached_feed`, `_set_cached_feed`, `_feed_cache`), the old `get_feed_stream`, and the old `get_feed` if it still exists. The file should go from ~1300 lines to ~100.

Keep: router setup, imports needed for the new code, any non-feed endpoints.

### 3. Backfill script

Create `scripts/backfill_feed_events.py`. Use asyncpg directly (NOT SQLAlchemy) for Supabase compatibility:

```python
import asyncio, asyncpg, json, os, ssl

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://...")

async def main():
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    
    conn = await asyncpg.connect(DATABASE_URL, ssl=ssl_ctx, statement_cache_size=0)
    
    # Clear existing feed events (idempotent)
    await conn.execute("DELETE FROM platform_feed_events")
    
    # Backfill from stories
    stories = await conn.fetch("""
        SELECT s.id, s.title, s.summary, s.perspective, s.cover_image_url, s.video_url, 
               s.thumbnail_url, s.reaction_count, s.comment_count, s.created_at,
               w.id as world_id, w.name as world_name, w.year_setting,
               u.id as agent_id, u.username, u.name as agent_name
        FROM platform_stories s
        JOIN platform_worlds w ON s.world_id = w.id
        JOIN platform_users u ON s.author_id = u.id
    """)
    for s in stories:
        payload = json.dumps({
            "id": str(s["id"]),
            "created_at": s["created_at"].isoformat(),
            "story": {
                "id": str(s["id"]), "title": s["title"], "summary": s["summary"],
                "perspective": s["perspective"], "cover_image_url": s["cover_image_url"],
                "video_url": s["video_url"], "thumbnail_url": s["thumbnail_url"],
                "reaction_count": s["reaction_count"] or 0, "comment_count": s["comment_count"] or 0,
            },
            "world": {"id": str(s["world_id"]), "name": s["world_name"], "year_setting": s["year_setting"]},
            "agent": {"id": str(s["agent_id"]), "username": f"@{s['username']}", "name": s["agent_name"]},
        })
        await conn.execute("""
            INSERT INTO platform_feed_events (event_type, created_at, payload, world_id, agent_id, story_id)
            VALUES ('story_created', $1, $2::jsonb, $3, $4, $5)
        """, s["created_at"], payload, s["world_id"], s["agent_id"], s["id"])
    
    # Backfill from dweller_actions
    actions = await conn.fetch("""
        SELECT a.id, a.action_type, a.content, a.dialogue, a.stage_direction, a.target, a.created_at,
               d.id as dweller_id, d.name as dweller_name, d.role, d.portrait_url, d.world_id,
               w.name as world_name, w.year_setting,
               u.id as agent_id, u.username, u.name as agent_name
        FROM platform_dweller_actions a
        JOIN platform_dwellers d ON a.dweller_id = d.id
        JOIN platform_worlds w ON d.world_id = w.id
        JOIN platform_users u ON a.author_id = u.id
    """)
    for a in actions:
        payload = json.dumps({
            "id": str(a["id"]),
            "created_at": a["created_at"].isoformat(),
            "action": {"type": a["action_type"], "content": a["content"], "dialogue": a["dialogue"],
                       "stage_direction": a["stage_direction"], "target": a["target"]},
            "dweller": {"id": str(a["dweller_id"]), "name": a["dweller_name"], "role": a["role"],
                        "portrait_url": a["portrait_url"]},
            "world": {"id": str(a["world_id"]), "name": a["world_name"], "year_setting": a["year_setting"]},
            "agent": {"id": str(a["agent_id"]), "username": f"@{a['username']}", "name": a["agent_name"]},
        })
        await conn.execute("""
            INSERT INTO platform_feed_events (event_type, created_at, payload, world_id, agent_id, dweller_id)
            VALUES ('dweller_action', $1, $2::jsonb, $3, $4, $5)
        """, a["created_at"], payload, a["world_id"], a["agent_id"], a["dweller_id"])
    
    # Add similar blocks for: proposals, aspects, reviews
    # (Check what tables exist and what the feed currently shows)
    
    total = await conn.fetchval("SELECT count(*) FROM platform_feed_events")
    print(f"Backfilled {total} feed events")
    await conn.close()

asyncio.run(main())
```

Extend this to also backfill proposals, aspects, and reviews from their respective tables.

### 4. Run tests

```bash
cd platform/backend && python -m pytest tests/ -x -q 2>&1 | tail -20
```

### 5. Showboat proof-of-work

This is BLOCKING. Do NOT commit until this exists.

```bash
uvx showboat init reports/PROP-028-complete.md "PROP-028: Denormalized Feed Events Table"
uvx showboat note reports/PROP-028-complete.md "Replaced 15-query feed assembly with single denormalized table. One connection, one query, cursor-streamed, sub-50ms cold loads."
uvx showboat exec reports/PROP-028-complete.md bash "wc -l platform/backend/api/feed.py"
uvx showboat exec reports/PROP-028-complete.md bash "wc -l platform/backend/utils/feed_events.py"
uvx showboat exec reports/PROP-028-complete.md bash "cd platform/backend && python -m pytest tests/ -x -q 2>&1 | tail -20"
```

### 6. Commit and push

```bash
git add -A
git commit -m "feat: PROP-028 denormalized feed events table — single query, sub-50ms cold loads"
git push origin staging
```
