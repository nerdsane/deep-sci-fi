# Immersive Experience Implementation

**Created:** 2026-01-10
**Status:** IN_PROGRESS
**Type:** Implementation

---

## Overview

Transform the Deep Sci-Fi canvas from a static dashboard into an immersive, game-like experience using cutting-edge web technologies.

---

## Technology Stack

| Technology | Purpose | Priority |
|------------|---------|----------|
| GSAP + ScrollTrigger | Scroll-driven animations, parallax, transitions | P0 |
| Shader Background | Procedural space/nebula effects | P0 |
| WebGPU Particles | High-performance particle system (100k+) | P1 |
| Howler.js | Spatial audio, ambient soundscapes | P1 |

---

## What Each Technology Does

### 1. GSAP + ScrollTrigger

**Use Cases in Deep Sci-Fi:**

```
┌─────────────────────────────────────────────────────────────┐
│  WELCOME SPACE                                               │
│                                                              │
│  [Scroll-triggered parallax on world cards]                  │
│  - Cards float up with staggered delays                      │
│  - Background shader responds to scroll position             │
│  - Particles flow in scroll direction                        │
│                                                              │
│  [World Card Hover]                                          │
│  - Card lifts with 3D tilt                                  │
│  - Nearby particles attract to card                          │
│  - Background brightens around card                          │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  WORLD SPACE (Full world exploration)                        │
│                                                              │
│  [Scroll-pinned Hero]                                        │
│  - Hero section pins while content scrolls                   │
│  - Camera zooms into world image                             │
│  - Text fades and scales cinematically                       │
│                                                              │
│  [Section Reveals]                                           │
│  - Rules fade in from sides                                  │
│  - Characters scale up from 0                                │
│  - Timeline animates along its axis                          │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  STORY READER                                                │
│                                                              │
│  [Scroll-scrubbed Reading]                                   │
│  - Progress bar tracks scroll                                │
│  - Background shifts mood with story                         │
│  - Audio crossfades between segments                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2. Shader Background

**The Procedural Space Shader:**

```glsl
// Conceptual - what it creates:
// - Animated nebula clouds (fractal Brownian motion)
// - Twinkling stars (noise + time-based flicker)
// - Color gradients that shift with view
// - Subtle parallax on mouse movement
// - Energy pulse effects on interactions
```

**Where It Appears:**
- Full-screen canvas behind ALL content
- Z-index -1, position fixed
- Responds to:
  - Time (continuous animation)
  - Mouse position (subtle parallax)
  - Current view (color theme)
  - User interactions (pulse effects)

**Visual Effect:**
```
┌────────────────────────────────────────────┐
│  ░░▒▒▓▓██████▓▓▒▒░░      ★              │
│    ░░▒▒▓▓████▓▓▒▒░░           ★   ★     │
│      ░░▒▒████▒▒░░                        │
│        ░░▒▒▒▒░░      ★                   │
│   ★         ░░                           │
│        ░░░░░░░░░░           ★            │
│      ░░▒▒▓▓▓▓▓▓▒▒░░                      │
│    ░░▒▒▓▓████████▓▓▒▒░░    ★             │
│  ░░▒▒▓▓██████████████▓▓▒▒░░              │
│    ░░▒▒▓▓████████▓▓▒▒░░         ★        │
└────────────────────────────────────────────┘
  Animated nebula with twinkling stars
```

### 3. WebGPU Particle System

**Particle Types:**

| Type | Count | Behavior | Visual |
|------|-------|----------|--------|
| Ambient dust | 10,000 | Float gently, react to scroll | Tiny white dots |
| Stars | 5,000 | Twinkle, subtle parallax | Bright points |
| Energy motes | 500 | Attracted to cursor, cards | Cyan/purple glow |
| World particles | Variable | Per-world themed | Custom colors |

**Performance Strategy:**
```
if (WebGPU supported) {
  // Use compute shaders - 100k+ particles at 60fps
  // All physics on GPU
} else if (WebGL2 supported) {
  // Use transform feedback - 50k particles
} else {
  // Canvas 2D fallback - 5k particles
}
```

### 4. Howler.js Audio

**Audio Layers:**

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: AMBIENT BASE (always playing)                      │
│  - Low-frequency space drone                                 │
│  - Volume: 0.3                                               │
│  - Loop: true                                                │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2: VIEW ATMOSPHERE (per-view)                         │
│  - Welcome: Mysterious, open                                 │
│  - World: Specific to world theme                            │
│  - Story: Narrative tension/mood                             │
│  - Crossfade on view change                                  │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  LAYER 3: UI FEEDBACK (triggered)                            │
│  - Card hover: Soft whoosh                                   │
│  - Selection: Confirmation tone                              │
│  - Transition: Swoosh effect                                 │
│  - New content: Notification ping                            │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  LAYER 4: SPATIAL (3D positioned)                            │
│  - Cards emit subtle hum when hovered                        │
│  - Particles have quiet crackling                            │
│  - Positioned in 3D space relative to cursor                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Foundation (Dependencies + Base Structure)

- [ ] Install dependencies: gsap, howler, @webgpu/types
- [ ] Create `ImmersiveBackground` component structure
- [ ] Create `AudioManager` context
- [ ] Create `ParticleSystem` base class
- [ ] Set up WebGPU/WebGL detection

### Phase 2: Shader Background

- [ ] Create WebGL canvas layer
- [ ] Implement space nebula shader (Perlin noise + fBm)
- [ ] Add star field layer
- [ ] Implement time-based animation
- [ ] Add mouse parallax effect
- [ ] Create view-based color theming

### Phase 3: GSAP Animations

- [ ] Integrate GSAP into React app
- [ ] Replace ScrollSection with GSAP ScrollTrigger
- [ ] Add world card parallax
- [ ] Implement section reveal animations
- [ ] Add view transition effects
- [ ] Create hero section pin/scrub

### Phase 4: Particle System

- [ ] Implement WebGPU particle compute shader
- [ ] Create WebGL fallback
- [ ] Add ambient dust particles
- [ ] Add cursor-attracted energy particles
- [ ] Implement scroll-direction flow
- [ ] Performance optimization

### Phase 5: Audio Integration

- [ ] Replace AudioPlayer with Howler.js
- [ ] Create ambient soundscape system
- [ ] Add UI sound effects
- [ ] Implement spatial audio
- [ ] Add volume/mute controls
- [ ] Create per-world audio themes

### Phase 6: Polish

- [ ] Performance profiling
- [ ] Mobile optimization
- [ ] Accessibility (prefers-reduced-motion)
- [ ] Loading states for assets
- [ ] Error boundaries

---

## File Structure

```
letta-code/src/canvas/
├── immersive/
│   ├── ImmersiveBackground.tsx    # Main container
│   ├── ShaderCanvas.tsx           # WebGL/WebGPU canvas
│   ├── ParticleSystem.tsx         # Particle orchestration
│   ├── shaders/
│   │   ├── nebula.frag           # Nebula fragment shader
│   │   ├── stars.frag            # Star field shader
│   │   └── particles.wgsl        # WebGPU compute shader
│   └── audio/
│       ├── AudioManager.tsx       # Howler integration
│       ├── sounds/               # Sound files
│       └── themes.ts             # Per-world audio config
├── hooks/
│   ├── useGsapScrollTrigger.ts   # GSAP integration hook
│   ├── useParticles.ts           # Particle system hook
│   └── useAmbientAudio.ts        # Audio hook
└── ...existing files
```

---

## Dependencies to Add

```json
{
  "dependencies": {
    "gsap": "^3.12.7",
    "howler": "^2.2.4"
  },
  "devDependencies": {
    "@webgpu/types": "^0.1.52",
    "@types/howler": "^2.2.12"
  }
}
```

---

## Progress Log

- [x] Phase 1: Foundation (dependencies installed)
- [x] Phase 2: Shader Background (ShaderCanvas.tsx with GLSL nebula shader)
- [x] Phase 3: GSAP Animations (useGsapAnimations.ts with ScrollTrigger hooks)
- [x] Phase 4: Particle System (ParticleSystem.tsx with WebGL)
- [x] Phase 5: Audio Integration (AudioManager.tsx with Howler.js + procedural UI sounds)
- [ ] Phase 6: Polish (pending - see notes below)

## Implementation Notes

### What Was Built

1. **ShaderCanvas.tsx**
   - Full GLSL fragment shader with Simplex noise for nebula effect
   - Animated stars with twinkle effect
   - Mouse parallax interaction
   - Configurable colors and intensity
   - WebGL2 with proper error handling

2. **ParticleSystem.tsx**
   - 5000+ particles with WebGL point rendering
   - Cursor attraction physics
   - Life cycle with fade in/out
   - Upward drift motion (like dust motes)
   - Additive blending for glow effect

3. **AudioManager.tsx**
   - Howler.js integration for ambient sounds
   - Procedural UI sounds using Web Audio API oscillators
   - Sound categories: hover, click, success, error, transition
   - Master volume and mute controls
   - Audio context initialization on user interaction

4. **useGsapAnimations.ts**
   - useScrollAnimation - ScrollTrigger integration
   - useParallax - Parallax effects
   - useFadeIn - Fade in elements on scroll
   - useRevealOnScroll - Various reveal effects
   - useStaggeredReveal - Staggered children reveals
   - useViewTransition - View transition animations
   - usePinSection - Pin sections while scrolling

5. **ImmersiveBackground.tsx**
   - Combines ShaderCanvas + ParticleSystem
   - Theme presets: default, cosmic, nebula, void, energy
   - Configurable per-view theme switching

### Files Created

```
letta-code/src/canvas/immersive/
├── index.ts                 # Exports
├── ImmersiveBackground.tsx  # Main wrapper
├── ShaderCanvas.tsx         # WebGL nebula shader
├── ParticleSystem.tsx       # Particle effects
├── AudioManager.tsx         # Howler.js audio system
└── useGsapAnimations.ts     # GSAP/ScrollTrigger hooks
```

### Remaining Work (Phase 6 - Polish)

- [ ] Test in browser and fix any visual issues
- [ ] Performance profiling
- [ ] Mobile responsiveness
- [ ] Respect prefers-reduced-motion
- [ ] Add loading states
- [ ] Add error boundaries
