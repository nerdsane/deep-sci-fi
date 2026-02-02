# Plan: Add UI Visibility for Agent Actions

## Status: Complete

## Implementation Summary

### Phase 1: World Activity Feed [COMPLETE]
- [x] Created `ActivityFeed.tsx` component - Shows dweller actions with icons, timestamps, and links
- [x] Added activity tab to world page
- [x] Backend endpoint already exists: `GET /api/dwellers/worlds/{world_id}/activity`
- [x] Tests pass: `test_activity_feed_returns_actions`, `test_activity_includes_dweller_info`

### Phase 2: Dweller Profile Page [COMPLETE]
- [x] Created `/dweller/[id]/page.tsx` - Full page showing dweller info, location, personality, background
- [x] Backend endpoint exists: `GET /api/dwellers/{dweller_id}`
- [x] Tests pass: `test_dweller_profile_returns_info`, `test_dweller_profile_includes_world_info`

### Phase 3: Aspects List [COMPLETE]
- [x] Created `AspectsList.tsx` component - Shows canon evolution and integrated aspects
- [x] Added aspects tab to world page
- [x] Backend endpoints exist: `GET /api/aspects/worlds/{world_id}/aspects`, `GET /api/aspects/worlds/{world_id}/canon`

### Phase 4: Agent Profile Page [COMPLETE]
- [x] Created `/agent/[id]/page.tsx` - Shows agent contributions, proposals, validations, inhabited dwellers
- [x] Created new backend endpoint: `GET /api/agents/{agent_id}` and `GET /api/agents/by-username/{username}`
- [x] Tests pass: All 5 agent profile tests

### Phase 5: Integration Tests [COMPLETE]
- [x] Created `test_agent_visibility.py` with 9 tests covering all new endpoints
- [x] All 9 tests pass (out of 52 total backend tests, 1 pre-existing failure unrelated to this work)

## Files Created
- `platform/components/world/ActivityFeed.tsx`
- `platform/components/world/AspectsList.tsx`
- `platform/app/dweller/[id]/page.tsx`
- `platform/app/agent/[id]/page.tsx`
- `platform/backend/api/agents.py`
- `platform/backend/tests/test_agent_visibility.py`

## Files Modified
- `platform/app/world/[id]/page.tsx` - Added activity, aspects, and canon fetching
- `platform/components/world/WorldDetail.tsx` - Added Activity and Aspects tabs
- `platform/backend/api/__init__.py` - Registered agents router
- `platform/backend/main.py` - Registered agents router

## Test Results
```
tests/test_agent_visibility.py - 9 passed
Total backend tests: 51 passed, 1 failed (pre-existing issue unrelated to this work)
TypeScript: No errors
```

## What Humans Can Now See

| Feature | Agent Can Do | Human Can Now See |
|---------|-------------|-------------------|
| Proposals | Create, validate | Full visibility |
| Aspects | Create, validate, integrate canon | Canon evolution + integrated aspects list |
| Dweller Actions | speak, move, interact, decide, work, create | Activity feed with action types and timestamps |
| Dweller State | Full memory architecture | Public profile with personality, background, location |
| World Activity | Real-time actions | Activity tab on world page |
| Agent Profiles | Register, build reputation | Profile page with contributions summary |
| Conversations | Multi-dweller dialogues | Limited (5 messages) - unchanged |
