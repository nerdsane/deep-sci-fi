# World Art Generation — The Atlas (PROP-010)

*2026-02-17T21:19:21Z by Showboat 0.6.0*
<!-- showboat-id: 187f2a69-d31d-4a84-8c4b-d681e44106f2 -->

Starting Phase 1: Dweller Portrait Generation. Plan: art_generation service, portrait_url migration, fire-and-forget hook on create, frontend avatar, backfill script.

Phase 1 complete. Files: services/art_generation.py (NEW), migration 0020 (NEW), Dweller.portrait_url added, dwellers.py fire-and-forget hook, feed.py portrait_url in all dweller dicts, api.ts FeedDweller type updated, FeedContainer.tsx DwellerAvatar component, backfill script (NEW). TypeScript typecheck passes. Python syntax verified.
