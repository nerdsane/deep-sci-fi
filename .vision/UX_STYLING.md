# UX & Styling

**Type:** STABLE
**Created:** 2026-01-09
**Last Updated:** 2026-01-10

---

## Design Philosophy

Push the envelope. Generic dashboards are everywhere. Deep Sci-Fi should feel like nothing else - a portal into worlds being created, not a tool for managing them.

**Core Tenets:**
1. **Immersive over utilitarian** - The interface is part of the experience
2. **Minimalist but bold** - Clean layouts, striking accents
3. **Square and sharp** - No soft edges, no rounded corners
4. **Agent as creative partner** - Not a chatbot, a collaborator

---

## Color Palette (Locked)

Use only these colors. Vary transparency, not hue.

```css
/* Backgrounds */
--bg-primary: #000000;
--bg-secondary: #0a0a0a;
--bg-tertiary: #0f0f0f;

/* Neon Accents */
--neon-cyan: #00ffcc;
--neon-cyan-bright: #00ffff;
--neon-purple: #aa00ff;

/* Text */
--text-primary: #c8c8c8;
--text-secondary: #8a8a8a;
--text-tertiary: #5a5a5a;
```

**Rules:**
- No new greens, blues, or purples - use the palette
- Vary with `rgba()` for transparency effects
- Cyan for primary actions, purple for secondary/agent
- **Purple for danger/destructive actions** (delete, remove, etc.)
- Glow effects via `box-shadow` with accent colors

---

## Typography

```css
--font-mono: 'Berkeley Mono', 'SF Mono', 'JetBrains Mono', monospace;
--font-sans: -apple-system, BlinkMacSystemFont, 'Inter', sans-serif;
```

- **Mono** for headers, labels, UI chrome
- **Sans** for body text, story content, long-form reading
- All caps + letter-spacing for labels and badges

---

## Component Rules

### Buttons
- Square corners (no border-radius)
- Uppercase, letter-spaced text
- Neon glow on hover
- Never rounded, never pill-shaped

### Cards
- Square corners
- Subtle border (`rgba(255,255,255,0.06)`)
- Top accent line on hover (gradient)
- Lift effect (`translateY(-2px)`) on hover

### Inputs
- Square corners
- Transparent or dark background
- Cyan border on focus
- No placeholder animations

### Modals
- Square corners
- Top accent border in cyan
- Backdrop blur
- No rounded anything

---

## Interaction Model

### Multimodal Agent Interaction

Users interact with the agent through multiple channels:

```
┌─────────────────────────────────────────────────┐
│                   AGENT                          │
│                                                  │
│   ┌─────────┐   ┌─────────┐   ┌─────────┐       │
│   │  CHAT   │   │ CANVAS  │   │  VOICE  │       │
│   │         │   │         │   │ (future)│       │
│   │Terminal │   │Immersive│   │  Speak  │       │
│   │  style  │   │  world  │   │ & listen│       │
│   └─────────┘   └─────────┘   └─────────┘       │
└─────────────────────────────────────────────────┘
```

**Chat** - Terminal-style conversation, always accessible
**Canvas** - Agent-controlled multimedia space for immersive exploration
**Voice** - Natural conversation (future)

### Canvas as Living Space

The canvas is not static UI. The agent dynamically creates and controls:
- Visual novel-style story presentation
- World exploration interfaces
- Character interactions
- Generated imagery and audio
- Game-like experiences

Think of canvas as a stage where the agent is the director.

---

## Immersive Experiences

When exploring worlds through story, the experience should feel like playing a game, not reading a document.

**Elements:**
- Full-screen visual novel mode
- Character portraits and backgrounds
- Ambient audio and music
- Smooth transitions between scenes
- Agent-driven narrative pacing

**Anti-patterns:**
- Static text walls
- Generic reading views
- Interrupting the experience with chrome

---

## Pushing the Envelope

We aim to set trends, not follow them. Current directions to explore:

### Spatial Depth
- Layered UI with parallax
- Elements that feel dimensional
- Subtle 3D transforms

### Kinetic Typography
- Text that responds to context
- Headlines that animate meaningfully (not decoratively)
- Type as interface element

### Adaptive Interfaces
- UI that responds to story mood
- Layouts that shift based on context
- Agent-driven visual changes

### Haptic Integration (Future)
- Tactile feedback for interactions
- Vibration patterns for agent communication
- Physical presence in digital space

---

## What We Avoid

| Anti-Pattern | Why |
|--------------|-----|
| Rounded corners | Breaks our sharp aesthetic |
| New color shades | Fragments the palette |
| Generic dashboard layouts | We're not a SaaS tool |
| Decorative animations | Motion should have purpose |
| Soft/friendly aesthetic | We're bold and immersive |
| Traditional form UX | Conversation is primary |

---

## Success Criteria

| Question | Good Answer |
|----------|-------------|
| Does it feel unique? | Unlike any other app |
| Is the agent present? | Feels like a collaborator, not a feature |
| Is it immersive? | You forget you're using software |
| Is it bold? | Makes a statement |
| Is it clean? | No clutter, clear focus |
