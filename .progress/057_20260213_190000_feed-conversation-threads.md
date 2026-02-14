# Feed Conversation Threading

**Created:** 2026-02-13 19:00:00
**Status:** In Progress
**Branch:** staging

## Goal

Transform the LIVE feed from flat action dumps to threaded conversations. Group related DwellerAction rows by their `in_reply_to_action_id` relationship and render them as conversation threads in the UI.

## Current State

- **Backend (`platform/backend/api/feed.py`)**: Lines 239-279 query DwellerAction rows and return each as individual `dweller_action` feed items
- **Frontend (`platform/components/feed/FeedContainer.tsx`)**: Lines 314-345 render each action as its own card
- **Data Model**: DwellerAction has `in_reply_to_action_id` FK forming reply chains

## Problem

Conversations between dwellers appear as disconnected flat entries. A conversation of 5 back-and-forth exchanges shows as 5 separate cards, making it hard to follow dialogue.

## Solution Design

### Backend Changes (feed.py)

1. **Thread Detection**: After fetching actions, group them into conversation threads
   - Root actions: `in_reply_to_action_id IS NULL`
   - Collect all descendants recursively via FK relationship
   - Solo actions (no replies, not replied to) stay individual

2. **New Feed Item Type**: `conversation`
   - Contains ordered list of actions in thread
   - Sorted by most recent action timestamp (active conversations bubble up)
   - Includes all action types (SPEAK, MOVE, OBSERVE, DECIDE, INTERACT)

3. **Maintain Existing Behavior**:
   - Keep all other feed item types unchanged
   - Preserve cursor-based pagination
   - Don't break time window filtering (last 7 days)

### Frontend Changes (FeedContainer.tsx)

1. **New Card Type**: `conversation`
   - Render threaded dialogue with visual hierarchy
   - Show dweller avatars (initial letter) + names
   - Different styling for action types:
     - **SPEAK**: Full dialogue with quotes, primary styling
     - **MOVE/OBSERVE/DECIDE/INTERACT**: Narrative description, dimmed/italic/smaller
   - Action type badge next to each line
   - Indentation or left-border coloring per speaker
   - Link to first dweller's page

2. **Preserve Existing**: Keep all other feed item card types working

## Implementation Plan

### Phase 1: Backend Threading Logic ✅
- [x] Add helper function to build conversation threads from actions
- [x] Modify dweller actions query section to group into threads
- [x] Return new `conversation` feed item type
- [x] Keep solo actions as `dweller_action` items

### Phase 2: Frontend Conversation Card ✅
- [x] Add `conversation` case to FeedItemCard component
- [x] Implement threaded rendering with speaker identification
- [x] Style dialogue vs narrative actions differently
- [x] Add linking to first dweller

### Phase 3: Testing & Verification
- [x] Backend syntax check passes
- [ ] Test with real conversation data (requires deployment)
- [ ] Verify pagination still works
- [ ] Check all existing feed types still render
- [ ] Verify performance with large threads

## Implementation Summary

### Backend Changes (api/feed.py)
- Modified dweller actions query to fetch more items (limit * 5) for threading
- Built thread detection logic:
  - Identifies root actions (no in_reply_to_action_id)
  - Recursively collects all descendants via FK relationship
  - Sorts threads by most recent action timestamp
  - Keeps solo actions (no replies, not a reply) as individual items
- Returns new `conversation` feed item type with:
  - `actions`: Array of actions in thread order
  - `action_count`: Number of actions
  - `updated_at`: Timestamp of most recent action
  - `world`: World context

### Frontend Changes
- Updated types in `lib/api.ts`:
  - Added `conversation` to FeedItemType union
  - Created FeedConversationAction interface
  - Extended FeedItem with conversation fields
- Added conversation card to `FeedContainer.tsx`:
  - Shows thread header with world name and action count
  - Renders each action with dweller avatar + name
  - Different styling for SPEAK (primary) vs narrative actions (dimmed/italic)
  - Shows action type badges
  - Indents replies with left border
  - Links to first dweller's page

## Next Steps
- Deploy to staging and test with real data
- Monitor performance with large threads
- Consider adding thread collapse/expand for very long conversations

## Key Constraints

- Don't break existing feed item types (world_created, proposal_submitted, etc.)
- Keep pagination working (cursor-based)
- Thread grouping should be time-bounded (actions within same thread)
- Work on staging branch, commit when tests pass

## Files to Modify

- `platform/backend/api/feed.py` (~lines 239-279)
- `platform/components/feed/FeedContainer.tsx` (~lines 314-345)
- `platform/lib/api.ts` (update FeedItem type if needed)

## Risks

- Large conversation threads could impact feed load time
- Need to handle orphaned replies (parent action deleted)
- Threading logic complexity could introduce bugs
