# PROP-022 Revision: Directional Relationship Graph

**Date:** 2026-02-18
**Branch:** staging
**Prompt:** `.progress/PROP-022-revision-prompt.md`

## Summary

Replace crude name co-occurrence relationship detection with real interaction signals:
- SPEAK actions with target (directional: A spoke to B)
- Story mentions of another dweller (directional: A's story mentions B)
- Reply threading (depth of back-and-forth)

## Files to Change

1. `platform/backend/alembic/versions/0024_directional_relationships.py` — ALTER TABLE, add 6 directional columns
2. `platform/backend/db/models.py` — Add new columns to DwellerRelationship
3. `platform/backend/utils/relationship_service.py` — Add `update_relationships_for_action()`, revise story logic
4. `platform/backend/api/dwellers.py` — Hook post-save after SPEAK action (~line 1864)
5. `platform/backend/api/dwellers.py` — graph endpoint response (get_dweller_graph already in relationship_service)
6. `platform/lib/api.ts` — Add directional fields to DwellerGraphEdge
7. `platform/components/graph/DwellerGraphCanvas.tsx` — Directional edges (arrows, asymmetry styling)
8. `scripts/materialize_relationships_and_arcs.py` — Backfill speak actions too

## Key Constraints

- DO NOT drop/recreate platform_dweller_relationships — ALTER it
- DO NOT remove co_occurrence_count
- DO NOT touch arc_service.py
- DO NOT change CHECK constraint (dweller_a_id < dweller_b_id) — directional counts live in separate columns within same canonical row

## Score Formula

```
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

## Status

- [x] Plan created
- [x] Migration 0024 — `platform/backend/alembic/versions/0024_directional_relationships.py`
- [x] Model updated — `DwellerRelationship` in `db/models.py`
- [x] Service updated — `update_relationships_for_story()` + `update_relationships_for_action()` in `relationship_service.py`
- [x] Hook in dwellers.py — post-save SPEAK hook at line 1864
- [x] Graph response updated — `get_dweller_graph()` returns all directional fields
- [x] TypeScript types updated — `DwellerGraphEdge` in `platform/lib/api.ts`
- [x] Canvas component updated — arrows, asymmetry (amber dashed), tooltip with directional counts
- [x] Backfill script updated — phases: speak actions first, then stories, then arcs
- [x] Tests written — `tests/test_relationships.py` has full suite
- [ ] Tests passing
- [ ] Committed & pushed
