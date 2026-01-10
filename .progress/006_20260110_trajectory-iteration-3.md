# Trajectory Integration - Iteration 3

**Started**: 2026-01-10
**Completed**: 2026-01-10
**Status**: ✅ COMPLETE

## Overview

Refactor trajectory system to properly separate OTS (generic) from Letta (application-specific) concerns.

## Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | OTS Privacy Module | ✅ COMPLETE |
| 2 | OTS DecisionManager | ✅ COMPLETE |
| 3 | OTS Pure Analytics | ✅ COMPLETE |
| 4 | Update Letta to use OTS | ✅ COMPLETE |
| 5 | Add OTS Analytics to UI | ✅ COMPLETE |
| 6 | Update OTS exports | ✅ COMPLETE |

---

## Phase 1: OTS Privacy Module ✅ COMPLETE

Created privacy/anonymization infrastructure in OTS.

### Files Created

| File | Description |
|------|-------------|
| `ots/src/ots/privacy/__init__.py` | Module exports |
| `ots/src/ots/privacy/protocols.py` | AnonymizationPolicy protocol + implementations |
| `ots/src/ots/privacy/anonymization.py` | Core anonymization functions |

### Key Functions

- `hash_identifier(identifier, salt)` - Deterministic ID hashing
- `anonymize_trajectory(trajectory, policy, salt)` - Full trajectory anonymization

### Policies Implemented

1. **DefaultAnonymizationPolicy** - Standard privacy (hashes IDs, redacts content)
2. **LearningPreservingPolicy** - Less aggressive (keeps rationale patterns for training)

### What Gets Preserved vs Anonymized

| Preserved (Learning Signal) | Anonymized |
|-----------------------------|------------|
| Turn sequence, decision types | IDs (hashed) |
| Timestamps, durations | Message text, arguments |
| Success/failure, error types | User info, referrers |
| Action names, scores | Reasoning (summarized) |

---

## Phase 2: OTS DecisionManager ✅ COMPLETE

Created decision management core in OTS.

### Files Created

| File | Description |
|------|-------------|
| `ots/src/ots/management/__init__.py` | Module exports |
| `ots/src/ots/management/decision_manager.py` | DecisionManager class with extraction and embedding |

### Key Components

- **DecisionRecord** dataclass - Flattened decision with trajectory context
- **DecisionSearchResult** dataclass - Result from decision search with similarity score
- **DecisionFilter** dataclass - Filter criteria for decisions
- **DecisionManager** class - Core logic for:
  - `extract_decisions(trajectory)` - Extract decisions from trajectory
  - `embed_decisions(records)` - Generate embeddings asynchronously
  - `filter_records(records, filter_criteria)` - Apply filters

---

## Phase 3: OTS Pure Analytics ✅ COMPLETE

Created analytics functions that work on pure OTS data (no LLM enrichment required).

### Files Created

| File | Description |
|------|-------------|
| `ots/src/ots/analytics/__init__.py` | Module exports |
| `ots/src/ots/analytics/pure_ots.py` | Pure OTS analytics functions |

### Key Functions

- `compute_decision_success_rate(trajectories)` - Success rate per action type
- `compute_action_frequency(trajectories)` - Action occurrence counts
- `compute_decision_type_breakdown(trajectories)` - Decision type distribution
- `compute_turn_distribution(trajectories)` - Turn count histogram
- `compute_error_type_frequency(trajectories)` - Error type counts
- `compute_trajectory_outcomes(trajectories)` - Outcome distribution (success/partial/failure)
- `get_pure_ots_analytics(trajectories)` - All analytics in one call

### OTSAnalytics Dataclass

Returns comprehensive metrics:
- decision_success_rate, action_frequency, decision_type_breakdown
- turn_distribution, error_type_frequency, trajectory_outcomes
- total_trajectories, total_decisions, total_turns, total_messages
- avg_turns_per_trajectory, avg_decisions_per_turn, avg_messages_per_turn
- overall_success_rate

---

## Phase 4: Update Letta to Use OTS ✅ COMPLETE

Refactored Letta to import from OTS instead of duplicating logic.

### Files Modified

| File | Change |
|------|--------|
| `letta/letta/services/trajectory_manager.py` | Import `hash_identifier` from OTS privacy module |

### Files Created

| File | Description |
|------|-------------|
| `letta/letta/services/decision_manager.py` | Thin wrapper over OTS DecisionManager |

### Key Changes

1. **trajectory_manager.py**: Now uses `ots.privacy.hash_identifier` for ID hashing
2. **decision_manager.py (NEW)**:
   - `LettaDecisionManager` class wrapping OTS DecisionManager
   - Handles Letta ORM persistence to `trajectories_decisions` table
   - Integration with Letta's embedding provider
   - Organization-scoped queries
   - Methods: `extract_and_store_async`, `search_decisions_async`, `get_decisions_for_trajectory_async`

---

## Phase 5: Add OTS Analytics to Letta UI ✅ COMPLETE

Added API endpoint and UI components for pure OTS analytics.

### Files Modified

| File | Change |
|------|--------|
| `letta/letta/server/rest_api/routers/v1/trajectories.py` | Added `/v1/trajectories/analytics/ots` endpoint |
| `letta-ui/src/lib/api.ts` | Added `getOTSAnalytics()` function |
| `letta-ui/src/components/AnalyticsView.tsx` | Added OTS analytics section with charts |

### New API Endpoint

```
GET /v1/trajectories/analytics/ots?agent_id=...&limit=...

Response:
{
  "decision_success_rate": {"world_manager": 0.85, "story_manager": 0.72},
  "action_frequency": {"world_manager": 42, "story_manager": 38},
  "decision_type_breakdown": {"tool_selection": 80, "parameter_choice": 45},
  "turn_distribution": {"1": 5, "2": 12, "3": 8},
  "error_type_frequency": {"ValidationError": 3, "Timeout": 1},
  "trajectory_outcomes": {"success": 40, "partial": 8, "failure": 2},
  "total_trajectories": 50,
  "total_decisions": 125,
  "total_turns": 200,
  "total_messages": 800,
  "avg_turns_per_trajectory": 4.0,
  "avg_decisions_per_turn": 0.625,
  "avg_messages_per_turn": 4.0,
  "overall_success_rate": 0.78
}
```

### UI Components Added

New "Pure OTS Analytics" section with:
1. **OTS Overview Stats** - Total decisions, success rate, avg decisions/turn, total messages
2. **Decision Success Rate by Action** - Bar chart showing success rate per action
3. **Action Frequency** - Bar chart of most common actions
4. **Decision Type Breakdown** - Pie chart of decision types
5. **Trajectory Outcomes** - Pie chart of success/partial/failure
6. **Error Type Frequency** - Bar chart of error types (if any)

---

## Phase 6: Update OTS Exports ✅ COMPLETE

Updated `ots/__init__.py` to export all new modules.

### Exports Added

```python
# Privacy
from ots.privacy import (
    anonymize_trajectory,
    hash_identifier,
    AnonymizationPolicy,
    DefaultAnonymizationPolicy,
    LearningPreservingPolicy,
)

# Management
from ots.management import (
    DecisionManager,
    DecisionRecord,
    DecisionSearchResult,
    DecisionFilter,
)

# Analytics
from ots.analytics import (
    get_pure_ots_analytics,
    compute_decision_success_rate,
    compute_action_frequency,
    compute_decision_type_breakdown,
    compute_turn_distribution,
    compute_error_type_frequency,
    compute_trajectory_outcomes,
    OTSAnalytics,
)
```

---

## Findings Log

### 2026-01-10

1. **OTS models.py structure** - Well-designed Pydantic models with full decision tracking:
   - `OTSDecision` has state, alternatives, choice, consequence, evaluation, credit_assignment
   - `OTSChoice` has action, arguments, rationale, confidence
   - `OTSConsequence` has success, result_summary, error_type

2. **Privacy policy pattern** - Created Protocol-based policies for flexible anonymization
   - DefaultAnonymizationPolicy for maximum privacy
   - LearningPreservingPolicy keeps more learning signal

3. **Letta trajectory format** - Letta stores trajectories differently from OTS spec:
   - Trajectories stored with `data` JSONB column containing turns/messages
   - Tool calls embedded in messages, not as separate decisions
   - Created conversion functions (`_letta_to_ots_for_analytics`) for compatibility

4. **OTS vs Letta-enriched data**:
   - **OTS (in `data` JSONB)**: turns, decisions, messages, metadata.outcome, final_reward
   - **Letta-enriched (separate columns)**: searchable_summary, outcome_score, tags, task_category, complexity_level, embedding

---

## Architecture

```
OTS Library (Generic)
├── privacy/                    ← Phase 1 ✅
│   ├── protocols.py           (AnonymizationPolicy)
│   └── anonymization.py       (anonymize_trajectory)
├── management/                 ← Phase 2 ✅
│   └── decision_manager.py    (DecisionManager)
├── analytics/                  ← Phase 3 ✅
│   └── pure_ots.py            (compute_* functions)
└── __init__.py                 ← Phase 6 ✅ (exports)

Letta Server (Application-Specific)
├── services/trajectory_manager.py    ← Phase 4 ✅ (use OTS anonymization)
├── services/decision_manager.py      ← Phase 4 ✅ (thin wrapper)
└── rest_api/.../trajectories.py      ← Phase 5 ✅ (OTS analytics endpoint)

Letta UI
├── lib/api.ts                        ← Phase 5 ✅ (getOTSAnalytics)
└── components/AnalyticsView.tsx      ← Phase 5 ✅ (OTS charts)
```

---

## Verification Checklist

- [x] OTS privacy module created
- [x] OTS DecisionManager created
- [x] OTS analytics functions created
- [x] Letta imports OTS anonymization
- [x] Letta DecisionManager uses OTS core
- [x] OTS analytics endpoint added
- [x] Letta UI displays pure OTS analytics
- [ ] Unit tests pass (deferred - no test infrastructure in current session)

---

## Summary of Changes

### OTS (7 new files)

1. `ots/src/ots/privacy/__init__.py`
2. `ots/src/ots/privacy/protocols.py`
3. `ots/src/ots/privacy/anonymization.py`
4. `ots/src/ots/management/__init__.py`
5. `ots/src/ots/management/decision_manager.py`
6. `ots/src/ots/analytics/__init__.py`
7. `ots/src/ots/analytics/pure_ots.py`

### Letta (2 modified, 1 new)

1. `letta/letta/services/trajectory_manager.py` (modified)
2. `letta/letta/services/decision_manager.py` (new)
3. `letta/letta/server/rest_api/routers/v1/trajectories.py` (modified)

### Letta UI (2 modified)

1. `letta-ui/src/lib/api.ts` (modified)
2. `letta-ui/src/components/AnalyticsView.tsx` (modified)
