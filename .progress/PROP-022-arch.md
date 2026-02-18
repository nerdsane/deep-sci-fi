# PROP-022: Materialize Relationships & Arcs — Compute on Write, Serve from Table

## Problem

Both PROP-009 (Dweller Relationships) and PROP-011 (Story Arcs) compute everything on every HTTP request:
- Relationships: scans ALL stories, does string matching for every dweller pair → O(stories × dwellers²)
- Arcs: loads all stories per dweller, computes embeddings cosine similarity, clusters → O(stories²)

At 20 stories this is fine. At 1,000 it's slow. At 10,000 the pages don't load.

Additionally:
- Relationships use string co-occurrence only (fragile — misses unnamed references, thematic connections)
- Arcs use an arbitrary 7-day window instead of semantic similarity

## Solution

### 1. New table: `dweller_relationships`

Migration 0023:

```sql
CREATE TABLE dweller_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dweller_a_id UUID NOT NULL REFERENCES platform_dwellers(id) ON DELETE CASCADE,
    dweller_b_id UUID NOT NULL REFERENCES platform_dwellers(id) ON DELETE CASCADE,
    co_occurrence_count INTEGER NOT NULL DEFAULT 0,
    semantic_similarity FLOAT,
    combined_score FLOAT NOT NULL DEFAULT 0,
    shared_story_ids UUID[] NOT NULL DEFAULT '{}',
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    UNIQUE(dweller_a_id, dweller_b_id),
    CHECK(dweller_a_id < dweller_b_id)  -- canonical ordering, no duplicates
);
CREATE INDEX idx_dweller_rel_a ON dweller_relationships(dweller_a_id);
CREATE INDEX idx_dweller_rel_b ON dweller_relationships(dweller_b_id);
CREATE INDEX idx_dweller_rel_score ON dweller_relationships(combined_score DESC);
```

### 2. Update `story_arcs` to be write-populated

The table already exists from migration 0022. Currently unused (arcs computed in memory). Change arc_service to write to it on story creation.

### 3. Compute-on-write hook in story creation

In `platform/backend/api/stories.py`, after a story is successfully created:

```python
# Post-save: update materialized views
from services.relationship_service import update_relationships_for_story
from services.arc_service import assign_story_to_arc

await update_relationships_for_story(db, story)
await assign_story_to_arc(db, story)
```

### 4. Rewrite `relationship_service.py`

Replace the current "scan all stories on every request" with:

**`update_relationships_for_story(db, story)`** — called on story creation:
1. Extract dweller names mentioned in story (existing word-boundary matching)
2. For each pair of mentioned dwellers:
   - Upsert into `dweller_relationships`: increment `co_occurrence_count`, append story_id to `shared_story_ids`
   - Compute `semantic_similarity` between dwellers if both have embeddings (optional, can be None)
   - Set `combined_score = 0.6 * normalized_co_occurrence + 0.4 * (semantic_similarity or 0)`
3. Normalize co_occurrence across all pairs so the scale is 0-1

**`get_relationship_graph(db)`** — called on GET request:
1. Query `dweller_relationships` WHERE `combined_score > 0`
2. Join with `platform_dwellers` for names, portraits, world info
3. Return nodes + edges — zero computation, just a read

### 5. Rewrite `arc_service.py`

Replace the current "cluster all stories on every request" with:

**`assign_story_to_arc(db, story)`** — called on story creation:
1. Get story's `content_embedding` (already generated at creation time)
2. Query existing arcs for this dweller from `story_arcs`
3. For each existing arc, compute average embedding of its stories
4. If cosine similarity to any arc centroid > 0.75 → add story to that arc
5. Else → create new arc
6. NO time window. Arcs are semantic, not temporal.

**`get_arcs(db)`** — called on GET request:
1. Query `story_arcs` joined with stories and dwellers
2. Group by arc_id
3. Return — zero clustering computation

### 6. Backfill script

`scripts/materialize_relationships_and_arcs.py`:
1. For relationships: iterate all stories, call `update_relationships_for_story` for each
2. For arcs: iterate all stories ordered by created_at, call `assign_story_to_arc` for each (order matters — earlier stories seed arcs, later ones join)
3. Idempotent — can be re-run safely

### 7. Nightly consistency cron

Background job (can be an OpenClaw cron or a simple script):
1. Recompute all relationships from scratch
2. Recompute all arcs from scratch  
3. Compare with stored values, log any drift
4. Overwrite with fresh values

This is the safety net — the write-path should keep things current, but the nightly pass catches anything missed.

## Files to change

- `platform/backend/migrations/0023_materialize_relationships.py` — new table
- `platform/backend/models.py` — add `DwellerRelationship` model
- `platform/backend/services/relationship_service.py` — rewrite: update_on_write + read_from_table
- `platform/backend/services/arc_service.py` — rewrite: assign_on_write + read_from_table
- `platform/backend/api/stories.py` — add post-save hooks
- `platform/backend/api/dweller_graph.py` — update to read from table
- `platform/backend/api/arcs.py` — update to read from table
- `scripts/materialize_relationships_and_arcs.py` — backfill script

## Risk

**High** — touches migrations, models, story creation API (critical write path), two service rewrites.

## Testing

1. Unit tests for `update_relationships_for_story`:
   - Story mentioning 2 dwellers → relationship created with count=1
   - Second story with same pair → count incremented to 2
   - Story mentioning 3 dwellers → 3 relationships (A-B, A-C, B-C)

2. Unit tests for `assign_story_to_arc`:
   - First story → new arc created
   - Similar story (cosine > 0.75) → added to existing arc
   - Dissimilar story → new arc created
   - NO time-window dependency

3. Integration tests:
   - `POST /api/stories` → verify `dweller_relationships` table updated
   - `POST /api/stories` → verify `story_arcs` table updated
   - `GET /api/dwellers/graph` → returns data from table (not computed)
   - `GET /api/arcs` → returns data from table (not computed)
   - `GET /api/dwellers/graph` with no stories → empty graph, 200

4. Backfill test:
   - Run backfill on test DB with known stories → verify expected relationships and arcs

## Showboat Documentation

Use showboat throughout:

```bash
# Init at start
uvx showboat init reports/PROP-022-complete.md "PROP-022: Materialize Relationships & Arcs"

# Capture migration
uvx showboat exec reports/PROP-022-complete.md bash "cd platform/backend && python3 -m alembic upgrade head 2>&1 | tail -5"

# Capture test results
uvx showboat exec reports/PROP-022-complete.md bash "cd platform/backend && python3 -m pytest tests/test_relationships.py tests/test_arcs.py -v 2>&1 | tail -30"

# Capture API responses proving endpoints work
uvx showboat exec reports/PROP-022-complete.md bash "curl -s https://api-staging.deep-sci-fi.world/api/dwellers/graph | python3 -m json.tool | head -30"
uvx showboat exec reports/PROP-022-complete.md bash "curl -s https://api-staging.deep-sci-fi.world/api/arcs | python3 -m json.tool | head -30"

# Screenshot frontend pages with Rodney
rodney start
rodney open "https://staging.deep-sci-fi.world/web"
rodney waitstable
rodney screenshot -w 1280 -h 900 /tmp/prop022-web-desktop.png
uvx showboat image reports/PROP-022-complete.md /tmp/prop022-web-desktop.png "Relationship graph — desktop"
rodney open "https://staging.deep-sci-fi.world/web" -w 375
rodney waitstable  
rodney screenshot -w 375 -h 812 /tmp/prop022-web-mobile.png
uvx showboat image reports/PROP-022-complete.md /tmp/prop022-web-mobile.png "Relationship graph — mobile"
rodney open "https://staging.deep-sci-fi.world/arcs"
rodney waitstable
rodney screenshot -w 1280 -h 900 /tmp/prop022-arcs-desktop.png
uvx showboat image reports/PROP-022-complete.md /tmp/prop022-arcs-desktop.png "Story arcs — desktop"

# Finalize
uvx showboat note reports/PROP-022-complete.md "## Summary\n- Migration 0023 applied\n- Both services rewritten to compute-on-write\n- Post-save hooks in story creation\n- Backfill script run\n- All endpoints return stored data, zero per-request computation"
```

## What NOT to do

- Do NOT remove the `content_embedding` column or change how embeddings are generated — that's working fine
- Do NOT change the frontend components — `DwellerGraphCanvas.tsx` and the arcs page consume the same API shape
- Do NOT add a time window to arc detection — arcs are semantic, not temporal
- Do NOT compute dweller embeddings (not needed yet — co-occurrence + story embeddings are sufficient for v1)
