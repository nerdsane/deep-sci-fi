# Plan: Playwright E2E Tests — Full Coverage, CI Gate, Change-Detection Hook

**Status:** COMPLETE
**Date:** 2026-02-07

## Summary

Implemented full E2E test coverage for all 13 routes, CI blocking gate, route coverage checker, and change-detection hooks.

## Phases Completed

### Phase 1: Fix Existing Failures + Extract Shared Fixtures ✅
- Fixed `agent-visibility.spec.ts`: tab locator `activity` → `live` (3 tests)
- Extracted shared fixtures to `platform/e2e/fixtures/test-world.ts`
- Helpers: `setupTestWorld()`, `setupTestProposal()`, `setupTestAspect()`, `setupTestStory()`

### Phase 2: Write E2E Tests for All 13 Routes ✅
- `smoke.spec.ts` — `/`, `/how-it-works`
- `worlds.spec.ts` — `/worlds`, `/world/[id]`
- `proposals.spec.ts` — `/proposals`, `/proposal/[id]`
- `agents.spec.ts` — `/agents`, `/agent/[id]`
- `stories.spec.ts` — `/stories`, `/stories/[id]`
- `dweller.spec.ts` — `/dweller/[id]`
- `aspect.spec.ts` — `/aspect/[id]`
- `feed.spec.ts` — `/feed`

### Phase 3: CI Gate in review.yml ✅
- Added Playwright browser install step
- Added E2E test step with proper env vars (DATABASE_URL, DSF_TEST_MODE_ENABLED, ADMIN_API_KEY)
- Placed after Alembic migrations, before schema checks
- 10-minute timeout

### Phase 4: E2E Route Coverage Checker ✅
- Created `scripts/check_e2e_coverage.py`
- Scans `platform/app/**/page.tsx` for routes
- Scans `platform/e2e/**/*.spec.ts` for `page.goto()` calls
- `--check` flag exits 1 if uncovered routes
- Added as CI step in review.yml
- Verified: 13/13 routes covered (100%)

### Phase 5: Change-Detection Hooks ✅
- Created `.claude/hooks/check-e2e-coverage.sh` (PostToolUse hook for Edit|Write)
- Updated `.claude/hooks/stop-verify-deploy.sh` with e2e-pending blocking check
- Updated `.claude/settings.json` with new PostToolUse hook entry
- Route mapping table maps frontend files to corresponding test files

## Files Changed

| File | Action |
|------|--------|
| `platform/e2e/fixtures/test-world.ts` | Created |
| `platform/e2e/agent-visibility.spec.ts` | Fixed + refactored |
| `platform/e2e/smoke.spec.ts` | Created |
| `platform/e2e/worlds.spec.ts` | Created |
| `platform/e2e/proposals.spec.ts` | Created |
| `platform/e2e/agents.spec.ts` | Created |
| `platform/e2e/stories.spec.ts` | Created |
| `platform/e2e/dweller.spec.ts` | Created |
| `platform/e2e/aspect.spec.ts` | Created |
| `platform/e2e/feed.spec.ts` | Created |
| `.github/workflows/review.yml` | Modified |
| `scripts/check_e2e_coverage.py` | Created |
| `.claude/hooks/check-e2e-coverage.sh` | Created |
| `.claude/hooks/stop-verify-deploy.sh` | Modified |
| `.claude/settings.json` | Modified |
