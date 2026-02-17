# End-to-End Test: Production Agent → World → Simulation → UI

## Status: COMPLETE

## Phases

### Phase 1: Database Cleanup
- [x] Add `DELETE /api/admin/reset` endpoint
- [x] Clear tables: worlds, dwellers, conversations, messages, stories, world_events
- [x] Keep: users, production_briefs (for history)

### Phase 2: xAI Grok Avatar Integration
- [x] Add `generate_avatar()` function to grok_imagine.py
- [x] Integrate into world_creator.py - generate avatars after dweller creation
- [x] Update dweller persona to include avatar_url and avatar_prompt

### Phase 3: Enhanced World Detail API
- [x] Add `GET /worlds/{id}/agents` endpoint
- [x] Add `GET /worlds/{id}/events` endpoint
- [x] Enhance `GET /worlds/{id}` with simulation_status

### Phase 4: Frontend UI Updates
- [x] Add Agents tab to WorldDetail.tsx
- [x] Show avatar images in DwellersView
- [x] Update LiveConversations to show avatars

### Phase 5: End-to-End Test Flow (Manual Steps)
- [ ] Reset database: `curl -X DELETE http://localhost:8000/api/agents/admin/reset`
- [ ] Trigger Production Agent: `curl -X POST http://localhost:8000/api/agents/production/run`
- [ ] Get briefs: `curl http://localhost:8000/api/agents/production/briefs`
- [ ] Approve Brief: `curl -X POST http://localhost:8000/api/agents/production/briefs/{id}/approve -d '{"recommendation_index": 0}'`
- [ ] Start Simulation: `curl -X POST http://localhost:8000/api/worlds/{id}/simulation/start`
- [ ] Verify in UI: http://localhost:3000/world/{id}

## Files Modified

| File | Changes |
|------|---------|
| `backend/api/agents.py` | Added /admin/reset endpoint |
| `backend/video/grok_imagine.py` | Added generate_avatar() function |
| `backend/agents/world_creator.py` | Integrated avatar generation |
| `backend/api/worlds.py` | Added /agents, /events endpoints |
| `components/world/WorldDetail.tsx` | Added Agents tab, avatar images |

## Implementation Notes

- Using xAI Grok Imagine API (already set up) for avatar generation
- Avatar URLs stored in dweller.persona.avatar_url
- World style derived from premise for consistent avatars
