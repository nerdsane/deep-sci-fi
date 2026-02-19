# PROP-022 Revision: Relationship Graph from Real Interactions

## Context

PROP-022 shipped a materialized relationship graph, but it uses name co-occurrence in story text — crude and inaccurate. This revision rewrites the relationship service to use actual interaction data from the platform.

## The Real Signals (in order of strength)

### Signal 1: SPEAK actions with target (strongest)
Table `platform_dweller_actions` has:
- `action_type = 'speak'`
- `target` (string — target dweller name)
- `dweller_id` (UUID — the speaker)
- `dialogue` (the actual speech)
- `in_reply_to_action_id` (threading — back-and-forth conversations)

This is **directional**: A spoke TO B. The `target` field is a dweller name string, not a UUID — you'll need to resolve it against dweller names in the same world.

### Signal 2: Stories mentioning another dweller
Table `platform_stories` has:
- `perspective_dweller_id` (the POV dweller)
- `content` (story text)

If Dweller A writes a story (is the perspective dweller) that mentions Dweller B's name, that's A thinking about B. Directional.

### Signal 3: Reply threading
`in_reply_to_action_id` creates conversation chains. Count the length of back-and-forth between two dwellers — longer threads = deeper engagement.

## What to Change

### 1. Revise `dweller_relationships` table (migration 0024)

Add directional columns. The existing migration 0023 created the table — this migration ALTERs it:

```sql
ALTER TABLE dweller_relationships
    ADD COLUMN speak_count_a_to_b INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN speak_count_b_to_a INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN story_mention_a_to_b INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN story_mention_b_to_a INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN thread_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN last_interaction_at TIMESTAMP WITH TIME ZONE;
```

Keep existing columns (`co_occurrence_count`, `combined_score`, `shared_story_ids`, `semantic_similarity`). The new columns ADD directional detail.

### 2. Rewrite `update_relationships_for_story()` in `relationship_service.py`

When a story is created:
1. Get the `perspective_dweller_id` (author)
2. Get all dweller names in the same world
3. Check which names appear in the story content (word-boundary match)
4. For each mentioned dweller: increment `story_mention_a_to_b` where A = author, B = mentioned

### 3. Add `update_relationships_for_action()` in `relationship_service.py`

New function, called when a SPEAK action is created:
1. Get the speaker's `dweller_id`
2. Resolve `target` string to a dweller ID (query `platform_dwellers` by name in the same world)
3. Upsert into `dweller_relationships`:
   - Increment `speak_count_a_to_b` (where A = speaker, B = target)
   - If `in_reply_to_action_id` exists and the replied-to action was by B, increment `thread_count`
   - Update `last_interaction_at`
4. Recompute `combined_score`:
   ```python
   score = (
       3.0 * speak_count_a_to_b +
       3.0 * speak_count_b_to_a +
       2.0 * story_mention_a_to_b +
       2.0 * story_mention_b_to_a +
       1.0 * thread_count +
       1.0 * co_occurrence_count
   )
   # Normalize relative to max score across all pairs
   ```

### 4. Hook into action creation

Find where SPEAK actions are created (likely in `platform/backend/api/actions.py` or `dwellers.py`) and add a post-save call:
```python
if action.action_type == 'speak' and action.target:
    await update_relationships_for_action(db, action)
```

### 5. Update `get_dweller_graph()` response

The API response should include directional data so the frontend can draw arrows:
```json
{
  "edges": [
    {
      "source": "dweller-a-id",
      "target": "dweller-b-id", 
      "weight": 12.5,
      "speaks_a_to_b": 8,
      "speaks_b_to_a": 3,
      "story_mentions_a_to_b": 2,
      "story_mentions_b_to_a": 0,
      "threads": 4,
      "last_interaction": "2026-02-18T..."
    }
  ]
}
```

### 6. Update `DwellerGraphCanvas.tsx`

- Edge thickness = combined weight
- Edge arrows showing direction (thicker arrow = more speech in that direction)
- Hover tooltip: "A spoke to B 8 times, B spoke to A 3 times, A mentioned B in 2 stories"
- If relationship is highly asymmetric (one side 3x+ the other), show as dashed or different color

### 7. Rewrite backfill script

`scripts/materialize_relationships_and_arcs.py` needs to:
1. Query ALL speak actions with targets, group by (speaker_dweller, target_name, world)
2. Resolve target names to dweller IDs
3. Build relationship rows with directional counts
4. Query ALL stories, check perspective_dweller mentions of other dwellers
5. Merge into same relationship rows

### 8. Update DwellerRelationship model in `models.py`

Add the new columns to the SQLAlchemy model matching migration 0024.

## Testing

1. **SPEAK action creates relationship:**
   - Create two dwellers in same world
   - Create SPEAK action from A targeting B
   - Verify `dweller_relationships` has row with `speak_count_a_to_b = 1`

2. **Story mention creates directional edge:**
   - Create story with `perspective_dweller_id = A`, content mentioning B's name
   - Verify `story_mention_a_to_b = 1`, `story_mention_b_to_a = 0`

3. **Thread counting:**
   - Create SPEAK from A → B, then SPEAK from B → A with `in_reply_to_action_id`
   - Verify `thread_count = 1`

4. **Score normalization:**
   - Multiple pairs with different interaction counts
   - Verify scores normalized relative to max

5. **GET /api/dwellers/graph returns directional data:**
   - Verify response includes `speaks_a_to_b`, `speaks_b_to_a` fields

6. **Integration: hit the endpoint, assert 200, assert response shape**

## Showboat

```bash
uvx showboat init reports/PROP-022-revision-complete.md "PROP-022 Revision: Directional Relationship Graph"

# Capture migration
uvx showboat exec reports/PROP-022-revision-complete.md bash "cd platform/backend && python3 -m alembic upgrade head 2>&1 | tail -5"

# Test results
uvx showboat exec reports/PROP-022-revision-complete.md bash "cd platform/backend && python3 -m pytest tests/test_relationships.py -v 2>&1 | tail -30"

# API response shape
uvx showboat exec reports/PROP-022-revision-complete.md bash "curl -s https://api-staging.deep-sci-fi.world/api/dwellers/graph | python3 -m json.tool | head -40"

# Frontend screenshots
rodney start
rodney open "https://staging.deep-sci-fi.world/web"
rodney waitstable
rodney screenshot -w 1280 -h 900 /tmp/prop022rev-desktop.png
uvx showboat image reports/PROP-022-revision-complete.md /tmp/prop022rev-desktop.png "Relationship graph with directional edges — desktop"
```

## What NOT to do
- Do NOT drop or recreate the `dweller_relationships` table — ALTER it
- Do NOT remove co_occurrence_count — keep it as one signal among many
- Do NOT touch arc_service.py — arcs are fine, this revision is relationships only
- Do NOT use embeddings for relationships — interactions ARE the relationships
- Do NOT change the CHECK constraint on dweller_a_id < dweller_b_id — directional counts go in separate columns within the same canonical row
