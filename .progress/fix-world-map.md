# Fix: World Map Not Rendering

## Problem
The `/map` page shows a blank canvas. The world map SVG never renders.

## Root Cause (already diagnosed)
CSS flex percentage-height chain failure:
1. `layout.tsx` has a `flex-1` div wrapping page content
2. Map page (`platform/app/map/page.tsx`) uses `h-full` on its container
3. `h-full` (height: 100%) needs a parent with a **definite** height — `flex-1` doesn't provide one per CSS3 spec
4. The canvas wrapper div gets `clientHeight: 0`
5. `WorldMapCanvas.tsx` has a ResizeObserver guard: `if (w > 0 && h > 0)` — never passes
6. d3 SVG never gets created

## Fix
In the map page component (`platform/app/map/page.tsx`):
- Change the outer container from `h-full` to use `absolute inset-0` positioning
- Add `relative` to the parent wrapper if needed so absolute positioning works

The key insight: instead of relying on percentage heights through the flex chain, use absolute positioning which doesn't need a definite parent height.

Look at how other full-height pages solve this in the codebase for reference.

## Verification
1. Run `npm run build` or `next build` to ensure no build errors
2. The map page container should have a non-zero height
3. The d3 SVG should render with world nodes

## Files to check
- `platform/app/map/page.tsx` — the map page component
- `platform/components/WorldMapCanvas.tsx` — the d3 canvas (DO NOT change the ResizeObserver logic, fix the CSS)
- `platform/app/layout.tsx` — for understanding the flex container structure

## DO NOT
- Remove the ResizeObserver guard in WorldMapCanvas
- Change layout.tsx in ways that affect other pages
- Add fixed pixel heights — the fix should be responsive
