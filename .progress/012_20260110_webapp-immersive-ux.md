# Web App Immersive UX Implementation

**Created:** 2026-01-10
**Status:** IN_PROGRESS
**Type:** Implementation

---

## Research Summary

### Technologies to Implement

| Technology | Purpose | Source |
|------------|---------|--------|
| **GSAP + ScrollTrigger** | Scroll-driven animations, parallax, staggered reveals | [GSAP Docs](https://gsap.com/docs/v3/Plugins/ScrollTrigger/), [GSAPify Guide](https://gsapify.com/gsap-scrolltrigger) |
| **WebGL Shader Background** | Procedural nebula/space effects | [shadcn.io/shaders/nebula](https://www.shadcn.io/shaders/nebula), [gl-react](https://github.com/gre/gl-react) |
| **3D Tilt Effect** | Interactive card hover with perspective | [react-parallax-tilt](https://dev.to/0xkoji/create-a-tilt-hover-effect-card-with-react-vanilla-tilt-react-parallax-tilt-639), [ibelick.com](https://ibelick.com/blog/create-tilt-effect-with-react) |
| **Procedural Audio** | UI sound feedback (hover, click, success) | [use-sound](https://www.joshwcomeau.com/react/announcing-use-sound-react-hook/), [Web Audio API](https://dev.to/hexshift/how-to-create-procedural-audio-effects-in-javascript-with-web-audio-api-199e) |

### Key Insights from Research

1. **GSAP is now 100% FREE** (Webflow acquisition) - includes ScrollTrigger, SplitText, ScrollSmoother
2. **useGSAP hook** from @gsap/react provides automatic cleanup in React
3. **shadcn.io shader components** offer ready-to-use React nebula/aurora effects
4. **Procedural audio** via Web Audio API - no audio files needed, generated in real-time
5. **3D tilt cards** use `perspective()` + `rotateX/Y` with mouse tracking
6. **Awwwards techniques**: parallax, sticky scroll, snap scroll, scroll-triggered 3D

---

## Implementation Plan

### Phase 1: Dependencies & Foundation
- [ ] Install GSAP + @gsap/react + ScrollTrigger
- [ ] Install react-parallax-tilt for 3D card effects
- [ ] Create WebGL shader background component
- [ ] Create procedural audio hook

### Phase 2: Shader Background
- [ ] Create `ShaderBackground.tsx` with WebGL2 nebula shader
- [ ] Add to layout as fixed background layer
- [ ] Implement mouse parallax effect
- [ ] Add theme-based color variations

### Phase 3: GSAP Scroll Animations
- [ ] Create `useGsapScrollTrigger.ts` hook
- [ ] Add staggered reveal to world cards grid
- [ ] Add parallax to hero sections
- [ ] Add scroll-pinned effects to WorldSpace

### Phase 4: 3D Card Effects
- [ ] Add tilt effect to world cards on hover
- [ ] Add hover glow intensification
- [ ] Add scale + lift on hover
- [ ] Respect prefers-reduced-motion

### Phase 5: Procedural Audio
- [ ] Create `useProceduralAudio.ts` hook
- [ ] Generate UI sounds: hover, click, success, error, transition
- [ ] Add to card interactions
- [ ] Add volume/mute controls

### Phase 6: Polish
- [ ] Performance testing
- [ ] Mobile optimization
- [ ] Accessibility audit (reduced motion)
- [ ] Loading states

---

## File Structure

```
apps/web/
├── components/
│   └── canvas/
│       └── immersive/
│           ├── ShaderBackground.tsx    # WebGL nebula shader
│           ├── useGsapAnimations.ts    # GSAP hooks
│           ├── useTiltEffect.ts        # 3D tilt logic
│           └── useProceduralAudio.ts   # Web Audio hook
├── app/
│   └── layout.tsx                      # Add ShaderBackground
└── package.json                        # Add dependencies
```

---

## Dependencies to Add

```json
{
  "dependencies": {
    "gsap": "^3.12.7",
    "@gsap/react": "^2.1.0",
    "react-parallax-tilt": "^1.7.0"
  }
}
```

---

## Progress Log

- [x] Phase 1: Dependencies & Foundation (gsap, @gsap/react, react-parallax-tilt installed)
- [x] Phase 2: Shader Background (ShaderBackground.tsx with WebGL2 nebula shader)
- [x] Phase 3: GSAP Scroll Animations (useGsapAnimations.tsx with staggered reveal hooks)
- [x] Phase 4: 3D Card Effects (TiltCard.tsx using react-parallax-tilt)
- [x] Phase 5: Procedural Audio (useProceduralAudio.tsx with Web Audio API)
- [ ] Phase 6: Polish (pending testing)

## Implementation Notes

### Files Created

```
apps/web/
├── app/
│   └── ImmersiveLayout.tsx           # Client wrapper with ShaderBackground + Audio
├── components/canvas/immersive/
│   ├── index.ts                      # Exports
│   ├── ShaderBackground.tsx          # WebGL2 procedural nebula shader
│   ├── TiltCard.tsx                  # 3D tilt effect wrapper (react-parallax-tilt)
│   ├── useGsapAnimations.tsx         # GSAP ScrollTrigger hooks
│   └── useProceduralAudio.tsx        # Web Audio API procedural sounds
```

### Features Implemented

1. **Shader Background** - Full GLSL nebula shader with:
   - Simplex noise + fractal Brownian motion
   - Mouse parallax effect
   - Animated star field with twinkle
   - Configurable colors and intensity
   - Vignette effect
   - WebGL2 with graceful fallback

2. **GSAP Animations** - React hooks for:
   - useStaggeredReveal - Staggered card reveal on scroll
   - useParallax - Parallax scrolling effect
   - useFadeInOnScroll - Fade in with various effects
   - useHeroParallax - Hero section parallax
   - usePinSection - Pin sections while scrolling
   - useCardHoverAnimation - GSAP-powered hover effects

3. **3D Tilt Cards** - World cards now have:
   - 6-degree max tilt on X/Y axes
   - 1.03x scale on hover
   - Cyan glare effect
   - Respects prefers-reduced-motion

4. **Procedural Audio** - Web Audio API sounds:
   - hover - Soft high-pitched blip
   - click - Sharp click
   - success - Ascending chime
   - error - Descending buzz
   - transition - Whoosh (filtered noise)
   - notification - Gentle ping
   - Volume/mute controls
   - Context provider for global state

### WelcomeSpace Updates

- World cards now wrapped with TiltCard for 3D hover effect
- GSAP staggered reveal animation on world cards grid
- Audio feedback on card hover and click
- Removed ScrollSection wrapper (GSAP handles animation now)
