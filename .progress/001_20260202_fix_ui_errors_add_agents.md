# Plan: Fix UI Errors & Add Agent Visibility

## Status: COMPLETE

## Summary
Fix "Not Found" errors on pages and add agent visibility features.

## Phases

### Phase 1: Add API Client Functions ✅
- [x] Add `getAgents()` to `lib/api.ts`
- [x] Add `getPlatformStats()` to `lib/api.ts`

### Phase 2: Create Agents Page ✅
- [x] Create `app/agents/page.tsx`
- [x] Display platform stats at top
- [x] List agents with cards showing their stats

### Phase 3: Update Navigation ✅
- [x] Add AGENTS link to Header
- [x] Update MobileNav (change STUDIO to AGENTS)
- [x] Add AGENTS link to BottomNav

### Phase 4: Improve Error Handling
- [x] FeedContainer - already handles empty state well
- [x] ProposalsPage - already handles empty state well
- [x] WorldRow - already handles empty state well
- [x] WorldCatalog - already handles empty state well

## Notes
- The error handling on all pages is already good - they distinguish between API errors and empty states
- "Not Found" errors would only appear if the API is actually failing (e.g., NEXT_PUBLIC_API_URL not set)
- Added agents page, platform stats, and navigation updates
