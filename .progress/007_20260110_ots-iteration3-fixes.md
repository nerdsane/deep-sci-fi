# OTS Iteration 3 Bug Fixes

**Created**: 2026-01-10
**Status**: COMPLETE

## Summary

Fix bugs and gaps discovered after completing Iteration 3 OTS integration.

## Issues

| # | Issue | Status |
|---|-------|--------|
| 1 | OTS Analytics API returns 404 | COMPLETE |
| 2 | Trajectories UI shows no decisions | COMPLETE |
| 3 | Web agents don't mandate trajectory search | COMPLETE |

## Phase 1: Fix API Route Ordering

**Issue**: `/v1/trajectories/analytics/ots` returns 404

**Root Cause**: In `trajectories.py`, `GET /{trajectory_id}` at line 111 shadows all specific routes defined after it.

**Fix**: Move `GET /{trajectory_id}` to END of file.

**File**: `letta/letta/server/rest_api/routers/v1/trajectories.py`

**Status**: COMPLETE - Moved `GET /{trajectory_id}` to end of file with comment explaining why.

---

## Phase 2: Add Decision Extraction to API

**Issue**: UI shows Letta-enriched data but no OTS decisions

**Fix**: Extract decisions on-demand in GET trajectory endpoint

**Files**:
- `letta/letta/server/rest_api/routers/v1/trajectories.py` - Added `_extract_decisions_from_trajectory()` helper
- `letta/letta/schemas/trajectory.py` - Added `DecisionSummary` and `TrajectoryWithDecisions` schemas
- `letta-ui/src/components/TrajectoriesView.tsx` - Added Decisions section with success/failure stats
- `letta-ui/src/types/letta.ts` - Added `DecisionSummary` interface

**Status**: COMPLETE

---

## Phase 3: Update Web Agent Prompts

**Issue**: Web agents list trajectory search as optional, not mandatory Phase 0

**Fix**: Add Phase 0 section to all agent prompts in `packages/letta/prompts.ts`

**File**: `packages/letta/prompts.ts` - Added `PHASE_ZERO_LEARNING` constant and injected into all three agent prompts (User, World, Experience)

**Status**: COMPLETE

---

## Implementation Summary

### Files Modified

| File | Changes |
|------|---------|
| `letta/letta/server/rest_api/routers/v1/trajectories.py` | Moved catch-all route to end; added decision extraction helper |
| `letta/letta/schemas/trajectory.py` | Added `DecisionSummary` and `TrajectoryWithDecisions` |
| `letta-ui/src/components/TrajectoriesView.tsx` | Added OTS Decisions section |
| `letta-ui/src/types/letta.ts` | Added `DecisionSummary` interface |
| `packages/letta/prompts.ts` | Added mandatory Phase 0 trajectory search to all agents |

### Verification Steps

After restarting the Letta server:

1. **Issue 1 Fix**: `curl http://localhost:8283/v1/trajectories/analytics/ots` should return 200
2. **Issue 2 Fix**: Trajectory detail view in UI should show "Decisions" section with success/failure stats
3. **Issue 3 Fix**: Create a new agent and verify system prompt includes Phase 0 section
