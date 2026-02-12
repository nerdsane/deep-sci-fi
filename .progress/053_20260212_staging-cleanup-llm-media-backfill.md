# Staging Cleanup + LLM-Powered Media Backfill

**Created**: 2026-02-12
**Status**: IN PROGRESS

## Phases

- [ ] Phase 1: Add World Delete Endpoint
- [ ] Phase 2: Add LLM-Powered Prompt Generation
  - [ ] 2a: Add anthropic dependency
  - [ ] 2b: Create prompt_generator.py
  - [ ] 2c: Update backfill to use LLM prompts + add video generation
- [ ] Phase 3: Remove All TEMP Test Media Injection
- [ ] Phase 4: Clean Up Staging (post-deploy)
- [ ] Phase 5: Deploy to Staging
- [ ] Phase 6: Run Backfill (post-deploy)
- [ ] Phase 7: Visual Verification (post-deploy)

## Findings

- CASCADE delete is set on stories (`world_id` FK), dwellers, aspects, etc.
- `get_admin_user` exists in `api/auth.py`
- Backfill endpoint currently only generates cover images with template prompts
- TEMP media injection in: `api.ts` (3 places), `stories/[id]/page.tsx`, `world/[id]/page.tsx`
