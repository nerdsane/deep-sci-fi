# Plan: Fix UI Errors & Add Agent Visibility

## Status: COMPLETE

## Summary
Fix "Not Found" errors on pages and add agent visibility features. Additionally, comprehensive feed rewrite to show all platform activity.

## Phases

### Phase 1: Add API Client Functions ✅
- [x] Add `getAgents()` to `lib/api.ts`
- [x] Add `getPlatformStats()` to `lib/api.ts`
- [x] Add comprehensive FeedItem types for all activity types

### Phase 2: Create Agents Page ✅
- [x] Create `app/agents/page.tsx`
- [x] Display platform stats at top
- [x] List agents with cards showing their stats

### Phase 3: Update Navigation ✅
- [x] Add AGENTS link to Header
- [x] Update MobileNav (change STUDIO to AGENTS)
- [x] Add AGENTS link to BottomNav

### Phase 4: Comprehensive Feed Rewrite ✅
- [x] Backend: Rewrite feed API to return all activity types
  - world_created, proposal_submitted, proposal_validated
  - aspect_proposed, aspect_approved
  - dweller_created, dweller_action
  - agent_registered
- [x] Frontend: Complete FeedContainer rewrite
  - Compact, well-styled activity cards
  - Activity type icons
  - VerdictBadge and StatusBadge components
  - AgentLink and WorldLink for navigation
- [x] Remove unused legacy components (StoryCard, ConversationCard, WorldCreatedCard)

### Phase 5: Backend Fixes ✅
- [x] Fix model attribute names in platform.py (creator→agent, proposer→agent)
- [x] Fix AspectStatus.PROPOSED→VALIDATING
- [x] Fix Dweller.backstory→background

## Notes
- Error handling on all pages is good - distinguishes between API errors and empty states
- Feed now shows ALL platform activity in a unified, compact format
