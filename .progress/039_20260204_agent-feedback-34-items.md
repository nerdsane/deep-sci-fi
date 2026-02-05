# Plan: Address All 34 Agent Feedback Items

## Status: COMPLETE (except Phase 0 — requires production API access)

## Commit: 0c6ec14 on staging branch

---

## Phase 0: Resolve 8 Items With No Code Changes — PENDING
- Cannot reach production API from dev machine (DNS doesn't resolve deepsci.fi)
- 8 feedback items to resolve via PATCH /api/feedback/{id}/status
- IDs: 5329a6b8, 7eef413d, 93b2dde2, dfefef03, 898076d1, 067d9be0, 521c30c7, 55a7ab47

## Phase 1: Unblock Agents — COMPLETE
- [x] Removed creator-only check for adding regions (dwellers.py)
- [x] Removed creator-only check for creating dwellers (dwellers.py)
- [x] Fixed region-not-found error to use structured format
- [x] Fixed dsf_hint to suggest "add region" when worlds have no regions (nudge.py)
- [x] Updated suggested_actions create_dweller message (agent_context.py)

## Phase 2: Auth + API Enhancements — COMPLETE
- [x] Accept Authorization: Bearer header (auth.py + agent_context.py middleware)
- [x] Add GET /dwellers/blocked-names endpoint (dwellers.py)
- [x] Add proposals_by_status to heartbeat your_work (heartbeat.py)
- [x] Add your_proposals to whats-new (platform.py)
- [x] Add validation_progress with queue_position to proposal detail (proposals.py)

## Phase 3: skill.md Documentation — COMPLETE
- [x] TL;DR 6-line quickstart
- [x] Bearer auth documentation
- [x] Dweller creation decision table (direct vs proposal)
- [x] Updated permissions text ("any agent can...")
- [x] Aspect content examples by type
- [x] Canon update guidance
- [x] Acclaim requirements note
- [x] Validation minimums callout table
- [x] test_mode guidance
- [x] Region naming note (by name, not ID)
- [x] blocked-names endpoint in table (auto-synced)

## Phase 4: World-inhabitable notification — COMPLETE
- [x] Added notify_world_became_inhabitable() to notifications.py
- [x] Triggered on first region add in dwellers.py
- [x] Wrapped in try/except so notification failure doesn't break region creation
- [x] Notifies all agents with platform_notifications enabled (not just callback_url agents)

## Code Review Fixes Applied
- [x] Fixed wrong table name in raw SQL (nudge.py) — used ORM instead
- [x] Removed callback_url filter from inhabitable notification
- [x] Wrapped notification call in try/except

## Files Modified (9)
- platform/backend/api/dwellers.py
- platform/backend/api/auth.py
- platform/backend/middleware/agent_context.py
- platform/backend/utils/nudge.py
- platform/backend/api/heartbeat.py
- platform/backend/api/platform.py
- platform/backend/api/proposals.py
- platform/backend/utils/notifications.py
- platform/public/skill.md
