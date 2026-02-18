# PROP-011: Story Arc Detection & Threading — Architecture

## Overview
Detect narrative arcs across stories and surface them in the UI so readers can follow a dweller's story thread.

## Data Model

### New migration: Add `content_embedding` to stories
```sql
ALTER TABLE platform_stories ADD COLUMN content_embedding vector(1536);
```

### New table: `platform_story_arcs`
```sql
CREATE TABLE platform_story_arcs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,           -- arc title (LLM-generated or auto)
    world_id UUID REFERENCES platform_worlds(id),
    dweller_id UUID REFERENCES platform_dwellers(id),  -- nullable, cross-dweller arcs possible
    story_ids UUID[] NOT NULL,    -- ordered list of story IDs in the arc
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

## Service: `platform/backend/utils/arc_service.py`

```python
async def detect_arcs() -> list[dict]:
    """
    Arc detection algorithm:
    1. Compute embeddings for all stories without content_embedding
    2. Group stories by dweller
    3. Within each dweller group, compute pairwise cosine similarity
    4. Cluster stories with similarity > 0.7 AND temporal proximity < 7 days
    5. For clusters with 2+ stories, create/update arc
    6. Generate arc name via LLM (or use "dweller_name: theme" pattern)
    """

async def get_story_arc(story_id: UUID) -> Optional[dict]:
    """Return the arc this story belongs to, with all sibling stories."""

async def list_arcs(world_id: Optional[UUID] = None) -> list[dict]:
    """List all arcs, optionally filtered by world."""
```

## API Endpoints

### `GET /api/stories/{id}/arc`
Returns the arc containing this story, or null.
```json
{
  "arc": {
    "id": "uuid",
    "name": "The Relay Corridor Sessions",
    "stories": [
      {"id": "uuid", "title": "string", "created_at": "iso", "position": 1},
      {"id": "uuid", "title": "string", "created_at": "iso", "position": 2}
    ]
  }
}
```

### `GET /api/arcs`
List all arcs with story counts.
Query params: `world_id`, `dweller_id`, `limit`, `cursor`

## Frontend Changes

### Story detail page
- Arc badge: "Part of: [Arc Name] (3 stories)" 
- Prev/Next story navigation within the arc
- Small arc timeline showing position

### New page: `/arcs`
- List all arcs grouped by world
- Each arc shows: name, dweller, story count, latest update
- Click → expands to show all stories in order

### Feed cards
- Small arc indicator on story cards that belong to arcs

## Backfill Script
`scripts/backfill_story_embeddings.py`
- Uses OpenAI text-embedding-3-small (same as world embeddings)
- Processes all existing stories
- Runs arc detection after embedding

## Cron
Add to Haku's crons: arc detection runs daily (after midnight refresh) to catch new stories.

## Files to create/modify
1. NEW: Migration adding `content_embedding` column + `platform_story_arcs` table
2. NEW: `platform/backend/utils/arc_service.py`
3. NEW: `platform/backend/api/arcs.py`
4. MODIFY: `platform/backend/api/__init__.py` — mount arcs router
5. MODIFY: `platform/backend/api/stories.py` — add arc info to story detail
6. NEW: `platform/app/arcs/page.tsx`
7. MODIFY: `platform/components/story/StoryDetail.tsx` — arc badge + navigation
8. MODIFY: `platform/components/story/StoryCard.tsx` — arc indicator
9. MODIFY: `platform/lib/api.ts` — add arc endpoints
10. NEW: `scripts/backfill_story_embeddings.py`

## Risk
High — migration (new column + table), new embeddings, new service. But follows PROP-015 patterns exactly.

## Showboat Proof-of-Work (MANDATORY)

You MUST produce a proper showboat document. This is not optional.

### Setup
```bash
uvx showboat init reports/PROP-011-complete.md "Story Arc Detection"
```

### For every significant step, capture output:
```bash
uvx showboat exec reports/PROP-011-complete.md bash "git diff --stat"
uvx showboat exec reports/PROP-011-complete.md bash "python -m pytest tests/ -x -q 2>&1 | tail -20"
uvx showboat exec reports/PROP-011-complete.md bash "curl -s 'https://api.deep-sci-fi.world/api/arcs' | python3 -m json.tool | head -30"
```

### For frontend changes, use Rodney for screenshots:
```bash
rodney start
rodney open http://localhost:3000/arcs
rodney waitstable
rodney screenshot -w 1280 -h 900 /tmp/arcs-desktop.png
uvx showboat image reports/PROP-011-complete.md /tmp/arcs-desktop.png "Desktop view of arcs page"
rodney screenshot -w 375 -h 812 /tmp/arcs-mobile.png
uvx showboat image reports/PROP-011-complete.md /tmp/arcs-mobile.png "Mobile view"
rodney stop
```

### Document structure must include:
1. **Summary** — one paragraph of what changed
2. **Changes** — `git diff --stat` output
3. **API Response** — real curl output from the endpoint
4. **Screenshots** — desktop + mobile of every new/changed page
5. **Tests** — full test output captured
6. **Migration** — diff of the migration file

A thin doc is a failure. Capture everything.

## Branch
`feat/story-arc-detection`
