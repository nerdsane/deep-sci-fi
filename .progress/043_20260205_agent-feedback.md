# Plan: Address All Agent Feedback (6 Items)

## Status: COMPLETE

## Phases
- [x] Phase 1: Model + Migration (0007_revision_tracking_threading_context.py)
- [x] Phase 2: Acclaim Gating + Revision Tracking (stories.py)
- [x] Phase 3: Feed story_revised Event (feed.py)
- [x] Phase 4: Two-Phase Action Flow + Conversation Threading (dwellers.py)
- [x] Phase 5: Mark Feedback Resolved (5/5 items resolved via production API)
- [x] Phase 6: Tests + Housekeeping (all test files updated, DST passes)

## Commits
- `6d70eec` feat: two-phase action flow, conversation threading, acclaim revision gate
- `a10294b` fix: remove action strategies from schema map (two-phase flow)

## Feedback Items Resolved
- `d8c7e77c` Name rejection examples — Fixed in 887e39e
- `b99e3716` Context-first action endpoint — Two-phase /act/context → /act
- `900f1b45` Story revisions on feed — story_revised feed event
- `2f85335b` Require revision for acclaim — revision_count >= 1 gate
- `2fc138fc` Same as above (duplicate) — same fix

## CI
- DST passes with seed=0 on GitHub Actions
- Deploy job runs migration against staging DB
- Full verification passed (health, smoke, schema, logfire)

## Notes
- Changes on `staging` branch — merge to `main` for production deploy
- Breaking change: POST /act now requires context_token from /act/context
