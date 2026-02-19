# PROP-013B: Feed Latency Phase 2 — Connection Pool Optimization

## Context
The feed endpoint runs 15 concurrent queries via `asyncio.gather()`. Each uses NullPool (fresh connection per query) to avoid shared-connection conflicts. But Logfire data shows:
- Slowest query: `graduated_worlds` at 3.24s avg
- Fastest query: `agents` at 1.67s avg  
- All queries take 1.6-3.2s — the floor is ~1.6s which is almost certainly connection setup overhead

The NullPool was needed because a shared pool caused "another operation in progress" errors. But NullPool means 15 fresh TCP+SSL connections to Supabase pooler per feed request.

## The Fix
Replace NullPool with a properly configured async connection pool that uses **separate connections per checkout** (not shared). The key insight: `pool_size=15, max_overflow=5` with `pool_pre_ping=True` should work because `asyncio.gather()` checks out 15 connections simultaneously — each gets its own connection from the pool, no sharing.

### Steps

1. **In `platform/backend/api/feed.py`**, replace:
```python
_feed_engine = create_async_engine(DATABASE_URL, poolclass=NullPool, ...)
```
with:
```python
_feed_engine = create_async_engine(
    DATABASE_URL,
    pool_size=15,
    max_overflow=5, 
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={'ssl': ssl_ctx, 'statement_cache_size': 0}  # keep existing SSL args
)
```

2. Keep `_FeedSession` as-is — it already uses `_feed_engine`.

3. **Test**: Run `python -m pytest tests/ -x -q` to make sure nothing breaks.

4. **Measure**: The cache warming cron hits `/api/feed` every 4 min. After deploy, check Logfire spans — individual query times should drop from 1.6-3.2s to 0.1-0.5s because connections are pre-established.

## Important
- Do NOT touch the main engine (`engine` in `db.py`) — that's for the rest of the app
- Only modify `_feed_engine` in `feed.py`
- If the pool causes "another operation" errors again, revert to NullPool and try `pool_size=20, max_overflow=0` instead
- Run showboat: `uvx showboat init PROP-013B-complete.md "Feed Latency Phase 2: Connection Pool"`
- Use `uvx showboat exec PROP-013B-complete.md bash "command"` for captured outputs
- Merge to staging when done

## Branch
`perf/feed-latency-phase2b`
