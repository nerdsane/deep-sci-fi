# World Card UX Improvements

**Created:** 2026-01-10
**Status:** COMPLETE

## Problem Statement

1. **Inconsistent loading indicator**: When images are being generated for world cards, the spinning circle (loading indicator) sometimes appears and sometimes doesn't
2. **Manual refresh required**: After images are generated, user must manually refresh the page to see them
3. **No highlight animation**: When new world cards appear, there's no visual indicator to draw attention

## User Requirements

- New world cards should have a neon highlight animation when they appear
- Cards should be added dynamically without reloading everything
- When an image finishes generating for a world card, highlight animation should appear again
- Image should show without page refresh

## Current Implementation Analysis

- `WelcomeSpace.tsx`: Renders world cards in a grid, no image loading state
- `app.tsx`: Handles `world_entered` and `image_generated` state changes, triggers full data refresh
- No tracking of which worlds are "new" or which have pending images
- World cards don't use the Image primitive component (which has loading states)

## Solution Design

### Phase 1: Track New/Updated Worlds
- Add `newlyAddedWorlds` Set to AppState to track worlds added during session
- Add `worldsWithPendingImages` Set to track worlds awaiting image generation
- Clear from `newlyAddedWorlds` after animation completes (via timeout or callback)

### Phase 2: Neon Highlight Animation CSS
- Create `@keyframes` animation for neon glow effect using brand colors
- Apply animation class when world is in `newlyAddedWorlds` set
- Re-trigger animation when image loads

### Phase 3: Image Loading State
- Track when `image_generated` event fires and which world it belongs to
- Show consistent loading indicator while image is pending
- Animate card when image successfully loads

### Phase 4: Incremental Updates
- When state changes occur, compare world lists to identify new/updated worlds
- Only highlight changed worlds, not all worlds

## Implementation Plan

1. Add CSS animation for neon highlight (welcome-space.css)
2. Add state tracking to app.tsx (newWorldIds, pendingImageWorldIds)
3. Pass tracking state to WelcomeSpace component
4. Update WelcomeSpace to apply highlight class to new/updated worlds
5. Add image loading detection in world cards
6. Test the full flow

## Files to Modify

- `letta-code/src/canvas/components/welcome/welcome-space.css` - Add animations
- `letta-code/src/canvas/components/welcome/WelcomeSpace.tsx` - Add highlight logic
- `letta-code/src/canvas/app.tsx` - Add state tracking for new/pending worlds

## Progress Log

- [x] Phase 1: State tracking for new/updated worlds
- [x] Phase 2: Neon highlight animation CSS
- [x] Phase 3: Image loading state handling
- [x] Phase 4: Testing and refinement

## Implementation Summary

### Changes Made

1. **CSS Animations** (`welcome-space.css`):
   - Added `@keyframes neon-pulse` - 3-pulse animation for new world cards
   - Added `@keyframes neon-flash` - Quick flash animation when image loads
   - Added `@keyframes spin` - Spinner for loading state
   - Added image container styles with placeholder, loading overlay, and image states

2. **App State Tracking** (`app.tsx`):
   - Added `newWorldIds`, `pendingImageWorldIds`, `recentImageWorldIds` Sets to AppState
   - Updated `world_entered` handler to detect new worlds and track pending images
   - Updated `image_generated` handler to detect which worlds got images
   - Auto-cleanup of tracking sets after animations complete via setTimeout

3. **WelcomeSpace Component** (`WelcomeSpace.tsx`):
   - Added new props for tracking Sets
   - Created `WorldCard` component with image loading state
   - Applied highlight classes based on tracking state
   - Image onLoad/onError handlers for proper state management
   - Fixed `getWorldId` to match `getWorldCheckpointName` logic from app.tsx

### How It Works

1. When a new world is created:
   - `world_entered` event fires → app detects new world → adds to `newWorldIds`
   - World card renders with `--new` class → neon-pulse animation plays
   - If world has no image yet → added to `pendingImageWorldIds` → spinner shows

2. When an image is generated:
   - `image_generated` event fires → app detects which world got image
   - World removed from `pendingImageWorldIds`, added to `recentImageWorldIds`
   - World card gets `--image-loaded` class → neon-flash animation plays
   - Image fades in smoothly as it loads
