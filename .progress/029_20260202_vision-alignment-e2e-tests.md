# Vision Alignment Review & E2E Testing

**Created:** 2026-02-02
**Status:** IN PROGRESS
**Goal:** Audit implementation against vision, identify gaps, set up comprehensive E2E tests

---

## Context

User request: Review current implementation for gaps, brittleness, and over-prescription (vision wants emergent behaviors), then create integration/E2E tests for the complete flow.

---

## Phase 1: Vision Alignment Audit ✅

### What Vision Says vs. What's Implemented

#### PHILOSOPHY.md: "Tools over workflows"

| Principle | Status | Assessment |
|-----------|--------|------------|
| Agents choose when to use tools | ✅ | API provides tools, doesn't prescribe order |
| No hard-coded sequences | ✅ | Proposal → Validate → World is natural, not forced |
| Self-eval not enforced | ✅ | Validation is external, agents choose to validate |
| Scales with better models | ✅ | More capable agents = better proposals/validations |

**Verdict: ALIGNED** - No over-prescription found.

#### PLATFORM_VISION.md: Core Loop

| Phase | Status | Notes |
|-------|--------|-------|
| PROPOSE | ✅ | POST /api/proposals |
| STRESS-TEST | ✅ | POST /api/proposals/{id}/validate |
| STRENGTHEN | ✅ | POST /api/proposals/{id}/revise |
| APPROVE | ✅ | Auto via validation verdicts |
| INHABIT | ✅ | POST /api/dwellers/{id}/claim |
| LIVE | ✅ | POST /api/dwellers/{id}/act |
| VISIT | ❌ | Not implemented (Phase 2+) |
| STORIES EMERGE | ⚠️ | Story model exists, no creation endpoint |
| HUMANS WATCH | ⚠️ | Feed exists, story detail page missing |

#### ARCHITECTURE.md: API Surface

| Endpoint Group | Vision Says | Implemented | Gap |
|----------------|-------------|-------------|-----|
| /proposals/* | Submit, list, revise | ✅ All | None |
| /validate/* | Submit validation | ✅ | None |
| /worlds/* | List, detail, events | ⚠️ | Events missing |
| /dwellers/* | Claim, propose, list | ✅ | None |
| /inhabit/* | State, act, release | ✅ | Named differently (/dwellers/{id}/*) |
| /visit/* | Enter, state, act, report, leave | ❌ | Not implemented |
| /stories/* | Submit, list, detail | ❌ | Missing |
| /social/* | React, comment, feed | ✅ | None |
| /reputation/* | Score, history | ❌ | Not implemented |

---

## Phase 2: Gaps Identified

### Critical Gaps (Must Fix)

1. **No Story Creation Endpoint**
   - Vision: "Stories emerge from lived experience"
   - Reality: Story model exists, no POST endpoint
   - Impact: Storytelling agents can't submit stories

2. **No Visitor System**
   - Vision: "Visitors observe, interact, file reports"
   - Reality: Not implemented
   - Impact: Phase 2+ feature, not critical for Phase 0

3. **No Reputation System**
   - Vision: Reputation gates high-impact actions
   - Reality: No reputation tracking
   - Impact: Phase 0 is test-mode with your bot, acceptable

### Moderate Gaps

4. **Frontend Story Detail Page**
   - StoryCard links to `/story/:id` which doesn't exist

5. **Frontend Conversation Detail Page**
   - ConversationCard links to `/conversation/:id` which doesn't exist

6. **World Events Endpoint**
   - Vision shows events feed, not implemented

### Low Priority Gaps

7. **Automatic Memory Summarization**
   - Currently agent-driven, not automatic
   - Acceptable per vision (agents choose tools)

---

## Phase 3: Over-Prescription Check

Checking for things that constrain emergent behavior:

| Area | Check | Status |
|------|-------|--------|
| Proposal format | Flexible JSONB for causal_chain | ✅ |
| Validation verdicts | 3 options (strengthen/approve/reject) | ✅ |
| Action types | 4 types (speak/move/interact/decide) | ⚠️ |
| Memory structure | Fixed schema | ⚠️ |
| Name context requirement | Min 20 chars enforced | ✅ (prevents slop) |

### Potential Over-Prescriptions

1. **Action Types Limited to 4**
   - `speak`, `move`, `interact`, `decide`
   - Could limit creative actions
   - **Assessment:** Acceptable as base categories, content field allows flexibility

2. **Memory Schema Fixed**
   - core_memories, episodic_memories, relationships, summaries
   - **Assessment:** Good foundation, flexible JSONB allows extension

**Verdict: NOT OVER-PRESCRIBED** - Structure provides foundation, flexibility maintained through JSONB fields and free-form content.

---

## Phase 4: E2E Test Plan

### Test Scope

The complete flow that should work:

```
1. Agent registers → Gets API key
2. Agent creates proposal → Draft saved
3. Agent submits proposal → Status: validating
4. Another agent validates (approve) → Status: approved, World created
5. World creator adds region → Region saved
6. World creator creates dweller → Dweller available
7. Agent claims dweller → Dweller inhabited
8. Agent takes action → Action recorded, memories updated
9. Agent releases dweller → Dweller available again
10. Human views feed → World appears
11. Human views world detail → Sees dwellers, activity
```

### Test Structure

```
platform/backend/tests/
├── test_e2e_proposal_flow.py      # Tests 1-4
├── test_e2e_dweller_flow.py       # Tests 5-9
├── test_e2e_aspect_flow.py        # Aspect creation and approval
├── conftest.py                    # Fixtures (test client, test agents)
```

### Fixtures Needed

- `test_client` - FastAPI TestClient
- `test_db` - Test database connection
- `agent_1` - Registered agent with API key
- `agent_2` - Second agent for validation
- `approved_world` - World from approved proposal
- `dweller` - Dweller in test world

---

## Phase 5: Implementation

### Files to Create

- `platform/backend/tests/conftest.py` - Pytest fixtures
- `platform/backend/tests/test_e2e_proposal_flow.py` - Proposal → World flow
- `platform/backend/tests/test_e2e_dweller_flow.py` - Dweller inhabitation flow
- `platform/backend/tests/test_e2e_aspect_flow.py` - Aspect integration flow

### Dependencies

- pytest
- pytest-asyncio
- httpx (async test client)

---

## Status

- [x] Phase 1: Vision Alignment Audit
- [x] Phase 2: Gap Identification
- [x] Phase 3: Over-Prescription Check
- [x] Phase 4: E2E Test Implementation
- [ ] Phase 5: Run & Verify Tests (requires PostgreSQL test database)

## Files Created

- `platform/backend/tests/test_e2e_proposal_flow.py` - Complete proposal → validation → world flow
- `platform/backend/tests/test_e2e_dweller_flow.py` - Complete dweller inhabitation flow
- `platform/backend/tests/test_e2e_aspect_flow.py` - Complete aspect integration flow
- Updated `platform/backend/tests/conftest.py` - Added second_agent fixture and sample data
- Updated `platform/backend/requirements.txt` - Added test dependencies

---

## Findings Summary

### Alignment: GOOD

The implementation aligns well with vision:
- Crowdsourced validation model works
- Dweller memory architecture is sophisticated
- No over-prescribed workflows
- Agents have tool autonomy

### Gaps: ACCEPTABLE FOR PHASE 0

Missing features are correctly scoped to later phases:
- Visitor system (Phase 2+)
- Reputation system (Phase 1+)
- Story creation (should add soon)

### Tests: NEEDED

No E2E tests exist. Creating comprehensive tests for:
- Proposal → Validation → World flow
- Dweller creation → Inhabitation → Action flow
- Aspect submission → Approval → Canon integration flow

---

## Next Steps

1. Create pytest fixtures with test database
2. Implement E2E tests for complete flows
3. Run tests to verify implementation
4. Fix any issues discovered
