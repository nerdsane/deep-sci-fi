# PROP-016 Follow-up: Remaining Map Visual Bugs

Read platform/components/world/WorldMapCanvas.tsx first. You are on branch fix/world-map-visual-overhaul.

## Bugs to fix

### 1. Ghost/Duplicate Labels (CRITICAL)
Every world node has TWO labels rendering: a white uppercase label near the node, AND a faded colored label at a different position. This means there are two label-rendering systems active. Find both, remove the duplicate. Only one label per node should render.

### 2. Legend Cut Off by Mobile Bottom Nav
On mobile (375px), the fixed bottom navigation bar overlaps the legend at the bottom of the screen. The legend entries "signed" and "thoughtcrime auditing" are hidden behind the nav bar. Add bottom padding (at least pb-20 or 80px) to the legend container so it clears the bottom nav.

### 3. Label Collision on Mobile Still Bad
On mobile, labels pile up in the bottom 15% of the canvas. The avoidLabelCollisions algorithm needs stronger separation force or more iterations for small viewports. Consider:
- Increase iteration count on mobile
- Increase minimum separation distance
- Or hide labels on mobile and show them only on tap/hover

### 4. Interaction Hints Missing on Mobile
The "scroll / drag / click" instructions visible on desktop are hidden on mobile. Either show them or replace with a brief mobile-appropriate hint.

## Verification
After fixing, use rodney to screenshot production (after pushing):
- rodney start
- rodney open https://deep-sci-fi.world/map
- rodney waitstable && rodney sleep 3
- rodney screenshot -w 1280 -h 900 reports/after-desktop-v2.png
- rodney screenshot -w 375 -h 812 reports/after-mobile-v2.png
- Add screenshots to reports/PROP-016-complete.md with showboat image
- rodney stop

Commit, push. Do NOT merge.
