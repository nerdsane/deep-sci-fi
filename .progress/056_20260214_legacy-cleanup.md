# 056 — Legacy Cleanup: Skill.md Rewrite + Dead Code Removal

**Status:** IN PROGRESS
**Created:** 2026-02-14
**Branch:** staging

## Goal

Remove all legacy code and documentation. The skill should describe ONLY the current system. The backend should not expose dead endpoints.

## Skill.md Rewrite (→ Version 2.0.0)

### Remove
- All references to approve/reject/strengthen vote-based validation
- `POST /api/media/stories/{story_id}/cover-image` from Step 13 and media docs (stories = video only)
- Old validation flow language ("validation_count", "approve_count", "reject_count")
- Contradictory guidance (e.g., telling agents to use cover-image AND video for stories)
- Any "old system" / "new system" comparative language — there's only ONE system now

### Add / Update
- Simulation layer: POST heartbeat with embedded action + dweller context
- Delta perception in act/context
- Reflection memory endpoint (`POST /api/dwellers/{id}/memory/reflect`)
- World signals in heartbeat response
- Critical review as THE review system (not "new" — just how it works)
- Version → 2.0.0, date → 2026-02-14
- Update all X-Skill-Version references to 2.0.0

### Structure
Keep the progressive disclosure structure (TL;DR → Quick Start → First Incarnation → Full API). But clean every section so there's one path, not legacy + current.

## Backend Code Cleanup

### Remove endpoints
- `POST /api/media/stories/{story_id}/cover-image` — stories get video, not images
- `POST /api/proposals/{id}/validate` — old vote endpoint (replaced by `/api/review/proposal/{id}/feedback`)
- `POST /api/aspects/{id}/validate` — old vote endpoint (replaced by `/api/review/aspect/{id}/feedback`)
- `POST /api/dweller-proposals/{id}/validate` — old vote endpoint (replaced by review feedback)

### Keep but clean
- `Validation` and `AspectValidation` DB models — data exists, can't drop tables. But remove from API serialization if not needed.
- `ValidationVerdict` enum — keep in models (existing data references it), remove from any new code paths
- `ReviewSystemType.LEGACY` — keep enum value (existing rows reference it), but nothing new should use it

### Do NOT remove
- `POST /api/stories/{id}/review` — this is the current story review endpoint
- Any `/api/review/*` endpoints — these are the new critical review system
- GET endpoints that return legacy data (backwards compat for reading)

## Heartbeat.md Cleanup
- Update to document POST heartbeat as primary
- Remove any legacy references
- Add simulation layer docs (delta, embedded action, world signals)

## OpenAPI
- Auto-generated from FastAPI — removing endpoints removes them from docs
- Verify after cleanup that `/docs` is clean

## DST Updates
- Remove any DST rules that test legacy validation behavior
- Add rules for: skill version must be bumped when content changes

## Version Bump Hook
- Already added: `.claude/hooks/check-skill-version.sh` (commit 841f79b)
- CC gets warned if it edits skill.md without bumping version

## Testing
- Existing tests that use old validate endpoints need updating
- Run full test suite after cleanup
- Verify OpenAPI schema is clean
- Type check must pass (`tsc --noEmit`)
