# Pixelarticons Migration

**Status:** Complete
**Created:** 2026-02-03
**Completed:** 2026-02-03

## Goal
Replace custom SVG icons and emojis with pixelarticons throughout the platform for a cohesive retro-futuristic aesthetic.

## Icon Mapping

| Location | Current | Pixelarticon |
|----------|---------|--------------|
| BottomNav - HOME | custom hexagon | `home` |
| BottomNav - FEED | custom pulse | `radio-signal` |
| BottomNav - WORLDS | custom planet | **Keep custom** (no equivalent) |
| BottomNav - AGENTS | custom android | `android` |
| Header - Menu | hamburger lines | `menu` |
| MobileNav - Close | X lines | `close` |
| Reactions - fire | emoji 🔥 | `zap` |
| Reactions - mind | emoji 🧠 | `lightbulb` |
| Reactions - heart | emoji ❤️ | `heart` |
| Reactions - thinking | emoji 🤔 | `mood-neutral` |
| VideoPlayer - Play | custom triangle | `play` |
| VideoPlayer - Pause | custom bars | `pause` |
| VideoPlayer - Mute | custom speaker-x | `volume-x` |
| VideoPlayer - Unmute | custom speaker | `volume-3` |
| VideoPlayer - Fullscreen | custom expand | `expand` |
| FeedContainer - world_created | globe SVG | **Keep custom** (no globe) |
| FeedContainer - proposal_submitted | doc SVG | `file-plus` |
| FeedContainer - proposal_validated | check SVG | `check` |
| FeedContainer - aspect_proposed | star SVG | `moon-star` |
| FeedContainer - aspect_approved | filled star | `moon-stars` |
| FeedContainer - dweller_created | person SVG | `user` |
| FeedContainer - dweller_action | chat bubble | `chat` |
| FeedContainer - agent_registered | person+ SVG | `user-plus` |
| WorldDetail - Puppeteer | smiley face | `mood-happy` |
| WorldDetail - Storyteller | eye | `eye` |
| WorldDetail - Critic | layers | `card-stack` |
| page.tsx - scroll arrow | arrow SVG | `arrow-down` |
| WorldDetail - play overlay | ▶ text | `play` |
| WorldDetail - back arrow | ← text | `arrow-left` |

## Implementation Phases

### Phase 1: Create PixelIcon Component
- [x] Install pixelarticons package
- [ ] Create reusable PixelIcon component that loads SVGs

### Phase 2: Replace Emojis (ReactionButtons.tsx)
- [ ] Replace 4 reaction emojis with pixel icons

### Phase 3: Navigation Icons
- [ ] BottomNav.tsx - 4 icons (keep planet custom)
- [ ] Header.tsx - menu icon
- [ ] MobileNav.tsx - close icon

### Phase 4: Video Player Icons
- [ ] VideoPlayer.tsx - 5 icons (play, pause, mute, unmute, fullscreen)

### Phase 5: Feed Icons
- [ ] FeedContainer.tsx - 7 activity type icons (keep globe custom)

### Phase 6: World Detail Icons
- [ ] Agent status icons (Puppeteer, Storyteller, Critic)
- [ ] Play overlay
- [ ] Back arrow

### Phase 7: Homepage
- [ ] Scroll indicator arrow

## Notes
- Icons should be sized at 24px multiples for crispness
- Use `currentColor` for dynamic theming
- Keep custom planet/globe SVG since pixelarticons has no equivalent
