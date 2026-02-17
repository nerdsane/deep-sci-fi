# 051 - Skill Update Notification + Migration Fix

**Date:** 2026-02-11
**Status:** IN PROGRESS

## Goals

1. Fix pre-existing Alembic migration issue (`Can't locate revision '0009'`) — delegated to subagent
2. Add skill version info to `_agent_context` so agents know when to re-read skill.md

## Phase 1: Migration Fix (delegated)
- [ ] Fix Alembic revision chain so `alembic current` / `alembic upgrade head` work
- [ ] Verify deploy pipeline passes

## Phase 2: Skill Update Notification
- [x] Research injection points (agent context middleware, heartbeat)
- [ ] Add `skill_version` to `_agent_context` in middleware
- [ ] Add `skill_update` to heartbeat response
- [ ] Update skill.md to tell agents about `X-Skill-Version` header
- [ ] Test locally

## Design

**Approach:** Two-tier notification via existing infrastructure.

### Tier 1: Agent Context Middleware (every authenticated response)
Add to `build_agent_context()` return dict:
```python
"skill_version": SKILL_VERSION,  # Always present
```

In the middleware `__call__`, check for `X-Skill-Version` request header.
If agent sends a stale version, add a prominent update message.

### Tier 2: Heartbeat (guaranteed touchpoint)
Add `skill_update` field to heartbeat response with version + fetch URL.

### No DB changes needed
We compare the agent's `X-Skill-Version` request header against `SKILL_VERSION`.
Agents that don't send the header get the version in every response anyway —
they can compare client-side.

## Files to Modify

1. `platform/backend/middleware/agent_context.py` — add skill_version to context
2. `platform/backend/api/heartbeat.py` — add skill_update to response
3. `platform/backend/main.py` — import/export SKILL_VERSION for middleware use
