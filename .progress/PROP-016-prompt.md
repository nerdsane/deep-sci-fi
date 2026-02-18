Fix visual bugs on the /map page of deep-sci-fi.world. This is PROP-016.

READ THESE FILES FIRST:
- platform/components/world/WorldMapCanvas.tsx
- platform/app/map/page.tsx
- platform/backend/utils/map_service.py

BUGS TO FIX (from Rodney visual audit):

CRITICAL:
1. Mobile (375px): map nodes completely invisible - canvas does not render on small screens
2. Text collision: world count "13" overlays legend word "partial" creating "parti13al mapped"
3. World labels overlap each other - multiple labels smash together and become unreadable
4. Most legend items cut off on mobile

MAJOR:
5. All worlds sit on same Y-axis (flat horizontal line) - with only 13 points, dimensionality reduction produces degenerate 1D layout. Add jitter or use force-directed positioning to spread nodes in 2D
6. About 70% empty space - map only fills top 30% of viewport, rest is void
7. Subtitle missing on mobile

MODERATE:
8. Legend color swatches too small (about 8px)
9. Low contrast on legend text and subtitle against dark background
10. No hover tooltips on world nodes showing name and premise
11. Instruction text disconnected from map content

DOCUMENTATION - use these tools:
- Run: showboat --help (to learn the showboat CLI)
- Run: rodney --help (to learn the rodney headless Chrome CLI)
- Initialize: showboat init reports/PROP-016-complete.md "PROP-016: World Map Visual Overhaul"
- Before screenshots: rodney start, then rodney open https://deep-sci-fi.world/map, rodney waitstable, rodney sleep 2, rodney screenshot -w 1280 -h 900 reports/before-desktop.png, rodney screenshot -w 375 -h 812 reports/before-mobile.png
- Embed before: showboat image reports/PROP-016-complete.md "![Before - Desktop](before-desktop.png)" and showboat image reports/PROP-016-complete.md "![Before - Mobile](before-mobile.png)"
- After fixing: push to branch, get Vercel preview URL from git push output, screenshot the preview
- Embed after screenshots similarly
- Add notes with showboat note explaining changes
- Run rodney stop when done

You are on branch fix/world-map-visual-overhaul. Commit and push when done. Do NOT merge to staging or main.
