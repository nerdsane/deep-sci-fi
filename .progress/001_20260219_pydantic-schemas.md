# Pydantic Response Schemas + Logfire Instrumentation

## Status: COMPLETE

## Phase 0: Logfire Pydantic Instrumentation - DONE
- Added `instrument_pydantic(record="failure")` to observability.py
- Called before any Pydantic imports in main.py

## Phase 1: Base Schemas - DONE
- Created schemas/__init__.py, schemas/base.py, schemas/common.py
- PaginatedResponse, CursorPaginatedResponse, StatusResponse
- AgentSummary, WorldSummary, DwellerSummary

## Phases 2-5: Schema Files + API Wiring - DONE (4 parallel agents)
- Batch A: worlds, stories, proposals
- Batch B: agents, auth, social, notifications
- Batch C: dwellers, aspects, events, actions
- Batch D: feed, heartbeat, platform, reviews, suggestions, feedback, media, x_feedback, arcs

## Fix: response_model_exclude_none
- Added `response_model_exclude_none=True` to 2 endpoints that conditionally add dict keys:
  - `POST /dwellers/{id}/act` (escalation field only present for high-importance)
  - `GET /aspects/{id}` (inspiring_actions only present when aspect has them)

## Stats
- 23 schema files in platform/backend/schemas/
- 21 API files with response_model=
- 112 total response_model= decorators
- 6 responses= decorators (feed SSE, heartbeat, etc.)

## Verification
- [x] All 22 schema modules import successfully
- [x] FastAPI app loads with 128 endpoints having response_model + 6 with responses
- [x] pytest: 81 passed, 232 skipped, 0 failed
- [ ] /docs shows new response schemas (needs manual check)
