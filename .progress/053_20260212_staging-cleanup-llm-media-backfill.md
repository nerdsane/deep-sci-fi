# Staging Cleanup + LLM-Powered Media Backfill

**Created**: 2026-02-12
**Status**: DEPLOYED — env vars set, awaiting backfill

## Phases

- [x] Phase 1: Add World Delete Endpoint (`DELETE /worlds/{world_id}`)
- [x] Phase 2: Add LLM-Powered Prompt Generation
  - [x] 2a: Add anthropic dependency
  - [x] 2b: Create `media/prompt_generator.py` (Claude Haiku)
  - [x] 2c: Update backfill to use LLM prompts + add video generation
- [x] Phase 3: Remove All TEMP Test Media Injection
- [ ] Phase 4: Clean Up Staging (needs admin API key)
- [x] Phase 5: Deploy to Staging (commit c6afe20, verified)
- [ ] Phase 6: Run Backfill (needs Phase 4 + ANTHROPIC_API_KEY on staging)
- [ ] Phase 7: Visual Verification

## Deployment Verification

- Backend: healthy (200)
- Frontend: healthy (200)
- Smoke test: 9/9 passed
- Schema: current
- Logfire: 0 exceptions in last 30 minutes
- DST: 57/57 state-mutating endpoints covered

## Files Changed

| File | Change |
|------|--------|
| `platform/backend/api/worlds.py` | Added DELETE endpoint |
| `platform/backend/media/prompt_generator.py` | New — LLM prompt generation |
| `platform/backend/api/media.py` | Updated backfill with LLM prompts + video |
| `platform/backend/requirements.txt` | Added `anthropic>=0.40.0` |
| `platform/backend/tests/simulation/rules/worlds.py` | New — DST rules for delete |
| `platform/backend/tests/simulation/test_game_rules.py` | Added WorldRulesMixin |
| `platform/public/skill.md` | Synced endpoints |
| `platform/lib/api.ts` | Removed TEMP media + added media type fields |
| `platform/app/stories/[id]/page.tsx` | Removed TEMP media injection |
| `platform/app/world/[id]/page.tsx` | Removed TEMP media injection |
| `platform/components/feed/FeedContainer.tsx` | Media rendering |
| `platform/components/story/StoryCard.tsx` | Media rendering |
| `platform/components/story/StoryDetail.tsx` | Media rendering |
| `platform/components/world/WorldDetail.tsx` | Media rendering |

## Next Steps (Phase 4-7)

1. Get list of world IDs on staging, identify Partial + Baseline
2. DELETE all other worlds via admin API
3. Ensure ANTHROPIC_API_KEY is set on staging backend
4. Run backfill: `POST /api/media/backfill`
5. Visually verify in Chrome
