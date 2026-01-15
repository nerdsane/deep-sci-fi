# Web App Immersive UX Implementation

**Created:** 2026-01-10
**Status:** IN_PROGRESS
**Type:** Implementation

---

## Problem Statement

The user reports that the previously implemented world card animations (neon pulse, loading spinner) are **not working**. Additionally, the web app needs more immersive, game-like UX beyond just fixing the animations.

### Symptoms Reported
1. Pulsing animation not visible when new worlds appear
2. Loading spinner inconsistent for image generation
3. Images still require refresh to appear

### Vision Alignment
From `.vision/UX_STYLING.md`:
- "Push the envelope" - not a generic dashboard
- "Immersive over utilitarian" - interface is part of experience
- "Canvas as Living Space" - agent-controlled multimedia
- "Feel like playing a game, not reading a document"

---

## Research Applied (from .progress/009)

### What's Relevant for the Web App

| Technology | Application |
|------------|-------------|
| **GSAP ScrollTrigger** | Parallax world cards, reveal animations, smooth scrolling |
| **Shader Background** | Already implemented - procedural nebula |
| **Particles** | Already implemented - floating dust motes |
| **Howler.js Audio** | Already implemented - UI sounds, ambient |
| **CSS Animations** | Fix the neon pulse/flash - currently broken |

### Key Improvements Needed

1. **Debug existing animations** - Why isn't neon pulse showing?
2. **GSAP integration in WelcomeSpace** - Replace ScrollSection with GSAP
3. **World card interactions** - 3D tilt on hover, attraction particles
4. **View transitions** - Cinematic transitions between views
5. **Audio integration** - Play sounds on interactions

---

## Phase 1: Debug Existing Animations

### Checklist
- [ ] Verify CSS classes are being applied correctly
- [ ] Check if world_entered event is firing
- [ ] Check if newWorldIds Set is being populated
- [ ] Verify CSS animation syntax
- [ ] Test in browser with DevTools

### Investigation Points
1. Is `getWorldId()` returning matching IDs in app.tsx and WelcomeSpace?
2. Are the Sets being passed correctly as props?
3. Is the CSS animation @keyframes syntax correct?
4. Are there any z-index or opacity issues hiding the effect?

---

## Phase 2: Apply GSAP to World Cards

### Goals
- Staggered reveal on scroll
- Parallax effect on cards
- Smooth hover animations
- Card "lift" with 3D perspective

---

## Phase 3: Enhance Interactions

### Goals
- 3D tilt on world card hover
- Particles attract to hovered card
- Audio feedback on hover/click
- Glow intensifies based on mouse proximity

---

## Phase 4: View Transitions

### Goals
- Crossfade between Welcome/World/Story views
- Camera-like zoom on world selection
- Smooth back navigation

---

## Investigation Log

(To be filled during debugging)

---

## Files to Examine

- `letta-code/src/canvas/components/welcome/WelcomeSpace.tsx`
- `letta-code/src/canvas/components/welcome/welcome-space.css`
- `letta-code/src/canvas/app.tsx` (state tracking)
- `letta-code/src/canvas/agentBusClient.ts` (event handling)
