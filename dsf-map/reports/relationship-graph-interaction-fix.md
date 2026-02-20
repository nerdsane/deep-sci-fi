# Fix: Relationship Graph Interaction (Click/Drag/Jitter/Mobile)

*2026-02-20T00:59:28Z by Showboat 0.6.0*
<!-- showboat-id: e6e59efb-d990-49f4-9a9e-450f8fe9464b -->

## Problem

User reported the relationship graph (/web) was jittery and unresponsive to clicks. Nodes couldn't be reliably clicked to navigate to dweller detail pages. Mobile was worse — taps conflicted with pan gestures.

## Root Causes

1. **Click fires after drag** — D3 drag + click on same element means any micro-drag (even 1px) during a click triggers the drag handler, and the subsequent click event fires with stale intent
2. **Simulation never settles** — default alphaDecay (0.0228) is too slow; nodes keep drifting after interactions
3. **Tooltip perf** — mousemove updating React state on every pixel, causing unnecessary re-renders
4. **No mobile tap handling** — relying on click events that conflict with touch pan/zoom

## Fixes Applied

| Fix | Technique | Lines Changed |
|-----|-----------|---------------|
| Click/drag disambiguation | Track drag distance, only navigate if <5px | +15 |
| Faster settling | alphaDecay 0.05, alpha cap on drag end, 2s hard-stop | +10 |
| Tooltip throttle | requestAnimationFrame gate on mousemove | +12 |
| Mobile tap | touchstart/touchend with 10px threshold | +15 |
| Cleanup | clearTimeout + cancelAnimationFrame on unmount | +3 |

Total: +62/-12 lines in DwellerGraphCanvas.tsx. Build passes.

```bash
cd platform && npx next build 2>&1 | tail -15
```

```output
├ ○ /skill.md                            0 B                0 B
├ ○ /stories                             6.05 kB         102 kB
├ ƒ /stories/[id]                        54.2 kB         150 kB
├ ○ /web                                 5.52 kB         118 kB
├ ƒ /world/[id]                          7.49 kB         145 kB
└ ○ /worlds                              4.45 kB         142 kB
+ First Load JS shared by all            87.3 kB
  ├ chunks/117-c86a41b869f6b521.js       31.7 kB
  ├ chunks/fd9d1056-6922f449a204c2cc.js  53.7 kB
  └ other shared chunks (total)          1.94 kB


○  (Static)   prerendered as static content
ƒ  (Dynamic)  server-rendered on demand

```
