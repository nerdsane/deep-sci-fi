# Remove legacy JSON feed endpoint

The old `GET /api/feed` (non-streaming) endpoint is unused — the frontend uses `GET /api/feed/stream` (SSE) exclusively. Remove the old one so nobody gets confused by its 15s cold load time.

## Steps

1. In `platform/backend/api/feed.py`:
   - Find the `@router.get("")` decorator above `async def get_feed(...)` (around line 643)
   - Remove the entire `get_feed` function and its route decorator
   - Keep the SSE `get_feed_stream` endpoint and ALL helper functions (`_fetch_*`, `_get_cached_feed`, `_set_cached_feed`, etc.) — the SSE endpoint uses them
   - Keep all the `_fetch_*` functions, cache functions, and utility functions intact

2. Check if anything else references the old endpoint:
   - `grep -rn "api/feed[^/]" platform/ --include="*.ts" --include="*.tsx" | grep -v feed/stream | grep -v node_modules | grep -v .next`
   - `grep -rn "/api/feed\"" platform/backend/ --include="*.py" | grep -v feed/stream`
   - If anything references it, update to use `/api/feed/stream` or remove the reference

3. Run tests: `cd platform/backend && python -m pytest tests/ -x -q 2>&1 | tail -20`

4. Commit to staging: `git checkout staging && git add -A && git commit -m "cleanup: remove unused JSON feed endpoint (SSE is the only feed path)"`

5. Merge to main: `git checkout main && git merge staging && git push origin main`

Do NOT remove:
- The `get_feed_stream` function or its route
- Any `_fetch_*` helper functions
- Any cache functions
- Any imports used by the remaining code
