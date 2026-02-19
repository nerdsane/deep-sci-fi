# PROP-028 Implementation Prompt

Read `.progress/PROP-028-arch.md` for the full architecture. Implement it exactly.

## Summary of what to build

1. **Migration** `alembic/versions/0025_feed_events_table.py` — creates `platform_feed_events` table with JSONB payload, indexes on `created_at DESC` and `event_type`

2. **Model** in `db/models.py` — add `FeedEvent` class

3. **Helper** `utils/feed_events.py` — `emit_feed_event(db, event_type, payload, ...)` function

4. **Write-path hooks** — In each API file, after the primary entity is created/committed, call `emit_feed_event()` with the denormalized payload. The payload shape MUST match what the current `get_feed_stream` function builds per event type. Read the existing code in `api/feed.py` to see the exact JSON structure per type.

   Files to modify:
   - `api/stories.py` — story_created, story_revised
   - `api/dwellers.py` — dweller_action, dweller_created
   - `api/proposals.py` — proposal_submitted, proposal_revised, proposal_validated, proposal_graduated, world_created
   - `api/aspects.py` — aspect_proposed, aspect_approved
   - `api/auth.py` — agent_registered
   - `api/reviews.py` — review_submitted, story_reviewed, feedback_resolved

5. **New read path** in `api/feed.py` — Replace the entire SSE endpoint with a single query against `platform_feed_events`. Keep SSE format identical so frontend doesn't change.

6. **Remove old code** from `api/feed.py` — delete ALL `_fetch_*` functions, cache layer, old streaming logic. The file should shrink from ~1300 lines to ~100.

7. **Backfill script** `scripts/backfill_feed_events.py` — populate from existing data. Use `statement_cache_size=0` for Supabase. Make it idempotent.

## Critical constraints

- **Payload format must be IDENTICAL to what the frontend parses.** Read the existing event-building code in feed.py before writing payloads.
- **Import FeedEvent in db/__init__.py** if needed for re-export.
- **Do NOT change any frontend code.**
- **Use existing db session patterns** — look at how other API files use `db: AsyncSession = Depends(get_db)`.

## After implementation

1. Run tests: `cd platform/backend && python -m pytest tests/ -x -q 2>&1 | tail -20`
2. Commit to staging: `git checkout staging && git add -A && git commit -m "feat: PROP-028 denormalized feed events table — single query, sub-50ms cold loads"`
3. Merge to main: `git checkout main && git merge staging && git push origin main`

## Showboat

```bash
uvx showboat init reports/PROP-028-complete.md "PROP-028: Denormalized Feed Events"
uvx showboat note reports/PROP-028-complete.md "Replaced 15-query feed assembly with single denormalized table. One query, one connection, sub-50ms cold loads."
uvx showboat exec reports/PROP-028-complete.md bash "wc -l platform/backend/api/feed.py"
uvx showboat exec reports/PROP-028-complete.md bash "cd platform/backend && python -m pytest tests/test_e2e_feed.py -x -q 2>&1 | tail -10"
```

DO NOT COMMIT until showboat doc exists.
