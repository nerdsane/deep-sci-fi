# PROP-013B: Feed Latency Phase 2 — Connection Pool Optimization

## Summary
Replaced NullPool (fresh TCP+SSL connection per query) with a proper async connection pool for the feed engine. The feed runs 15 concurrent queries via `asyncio.gather()` — NullPool meant 15 fresh connections to Supabase pooler every request, with ~1.6s connection setup overhead each. The pool keeps connections alive and reuses them.

Also added a cache warming cron (every 4 min) that keeps the 5-min cache always warm, eliminating cold misses for users entirely.

## Logfire Data (Before — NullPool)
Per-query timing from 24h of Logfire spans (all 15 `feed_fetch_*` functions):

| Query | Avg Duration |
|-------|-------------|
| feed_fetch_graduated_worlds | 3.24s |
| feed_fetch_stories | 2.89s |
| feed_fetch_aspects | 2.83s |
| feed_fetch_story_reviews | 2.75s |
| feed_fetch_proposals | 2.71s |
| feed_fetch_actions | 2.61s |
| feed_fetch_resolved_feedback | 2.57s |
| feed_fetch_revised_stories | 2.57s |
| feed_fetch_review_feedbacks | 2.55s |
| feed_fetch_dwellers | 2.54s |
| feed_fetch_worlds | 2.38s |
| feed_fetch_revised_proposals | 2.26s |
| feed_fetch_validations | 1.79s |
| feed_fetch_agents | 1.67s |
| feed_fetch_revised_aspects | 1.66s |

Floor of ~1.66s = connection setup overhead (TCP + SSL handshake to Supabase).

## Changes
```
 platform/backend/api/feed.py | 40 +++++++++++++++++++++++++++++-----------
 1 file changed, 29 insertions(+), 11 deletions(-)
```

### Key change in feed.py:
```python
# Before: NullPool — fresh connection every checkout
_feed_engine = create_async_engine(DATABASE_URL, poolclass=NullPool, ...)

# After: Persistent pool — connections reused across requests
_feed_engine = create_async_engine(
    DATABASE_URL,
    pool_size=15,       # matches 15 concurrent queries
    max_overflow=5,     # burst capacity
    pool_pre_ping=True, # detect stale connections
    pool_recycle=300,   # refresh every 5 min (Supabase pooler compat)
    ...
)
```

Test mode still uses NullPool (event loop mismatch with pytest).

## Cache Warming Cron
- ID: `50a04943`
- Schedule: every 4 minutes
- Isolated session, delivery: none (silent)
- Hits `GET /api/feed?limit=20`
- With 5-min cache TTL, cache is always warm → users never see cold miss

## Verification
- Tests: 86 pass, 7 pre-existing failures (identical to main)
- TypeScript: clean
- No migration, no schema change

## Expected Impact
Individual query times should drop from 1.6-3.2s (connection setup) to 0.05-0.5s (pool checkout + query). Total feed cold miss from ~3s to sub-1s. Warm hits unchanged at 0.14s.

**Logfire "after" data will be captured in next patrol cycle once production deploys.**
