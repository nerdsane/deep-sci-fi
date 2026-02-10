# 041 - Deterministic Simulation Testing Implementation

**Status:** COMPLETE
**Parent:** 040_20260204_devops-quality-harness-implementation.md
**Branch:** staging

## Summary

Implemented DST infrastructure adapted from FoundationDB/TigerBeetle patterns for API-level property testing.

## Completed

### Production Bug Fixes
- [x] **Dweller claim TOCTOU** — `select().with_for_update()` replaces `db.get()` in `dwellers.py:806`
- [x] **Proposal validation TOCTOU** — `.with_for_update()` added to proposal SELECT in `proposals.py:973`
- [x] **Configurable dedup** — `DEDUP_WINDOW_OVERRIDE_SECONDS` env var replaces `TESTING` check

### Infrastructure
- [x] `utils/clock.py` — Injectable clock (Protocol-based, SimulatedClock for tests)
- [x] `utils/simulation.py` — BUGGIFY fault injection (seeded RNG, zero-cost in production)
- [x] Clock injection across 16 production files (38 `datetime.now(timezone.utc)` → `utc_now()`)
- [x] 4 BUGGIFY injection points (dweller claim, feedback upvote, 2x proposal validation)

### Test Suite
- [x] `tests/simulation/conftest.py` — Sync client factory with SimulatedClock + BUGGIFY
- [x] `tests/simulation/state_mirror.py` — State tracking dataclasses
- [x] `tests/simulation/strategies.py` — Test data generators (counter-based uniqueness)
- [x] `tests/simulation/test_game_rules.py` — 12 rules, 7 safety invariants, 3 liveness invariants
- [x] `tests/simulation/test_game_rules_with_faults.py` — 6 fault injection rules (concurrent claims, double upvotes, etc.)

### CI
- [x] hypothesis added to requirements.txt
- [x] Simulation test step in review.yml (with hypothesis-seed=0, artifact upload on failure)
- [x] Existing tests updated for DEDUP_WINDOW_OVERRIDE_SECONDS

## Files Changed
- **7 new files** (clock, simulation, 5 test files)
- **21 modified files** (16 clock injection + 3 BUGGIFY + requirements + CI + conftest)

## Verification
- All Python files parse (ast.parse)
- FastAPI app imports correctly (111 routes)
- All modules import without errors
- PostgreSQL required for full test execution (CI will validate)
