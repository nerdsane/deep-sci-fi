# UI/Design System Overhaul

**Created:** 2026-02-02
**Status:** In Progress

## Objective

Improve the Deep Sci-Fi UI throughout using Refactoring UI principles, design tokens, and inspiration from agent-first landing pages (Molthunt, Linear).

**Key Requirements:**
- Keep existing ASCII logos
- Use Radix primitives (not shadcn)
- Clean, neat, responsive design
- Proper typography with Inter font
- Consistent spacing and color systems

## Inspiration Analysis

### Molthunt
- Clean dark theme with subtle gradients
- Orange/coral accent on dark backgrounds
- Card-based layout with clear hierarchy
- Minimal borders, subtle backgrounds for cards
- Clean sans-serif typography (Inter-style)

### Linear
- Large, confident typography
- Generous whitespace
- Dark mode with product screenshots
- Simple 2-button CTA pattern
- Subtle grid/line decorations

### Anthropic
- Elegant serif headings
- Cream/warm backgrounds
- Generous spacing
- Editorial feel

## Phases

### Phase 1: Design Tokens Foundation
- [x] Define color palette with proper scales
- [x] Define typography scale (fluid)
- [x] Define spacing scale
- [x] Remove duplicate token definitions (CSS vars vs Tailwind)

### Phase 2: Font Setup
- [x] Add Inter font via next/font
- [x] Configure font variables properly
- [x] Keep Berkeley Mono for code/UI chrome

### Phase 3: Global Styles Cleanup
- [x] Clean up globals.css
- [x] Remove redundant rules
- [x] Proper focus ring system

### Phase 4: Landing Page Refinement
- [x] Better visual hierarchy
- [x] Cleaner spacing
- [x] More responsive layout
- [x] Improved button styles

### Phase 5: Component Updates
- [ ] Update Button component
- [ ] Update Card component
- [ ] Ensure consistency

## Files Modified
- platform/tailwind.config.ts
- platform/app/globals.css
- platform/app/layout.tsx
- platform/app/landing/page.tsx
