# DSF Unified UX Implementation Plan

> Consolidated from `dynamic-canvas-ux-vision.md` and `unified-ux-vision.md`
> Updated: January 2026 with new vision discussions

## Vision

**"Deep Sci-Fi as Living Narrative Space"**

Create a **seamless, agent-driven narrative experience** where:
- Users flow between CLI and Canvas interfaces effortlessly
- Agent dynamically composes rich multimedia experiences
- Stories feel magical — not text on a page, but immersive journeys
- Worlds are explorable spaces, not cards in a grid
- Agent is a visible guide, not hidden infrastructure

---

## Core Principles

| Principle | What It Means |
|-----------|---------------|
| **Contextual Entry** | Never a cold dashboard. Always "you were here, here's what's next" |
| **Agent as Guide** | Visible presence. Thinking out loud. Suggesting. Reacting. |
| **Stories as Magic** | Not text on a page. Multimedia scrollytelling that pulls you in. |
| **Worlds as Spaces** | Step *into* a world. Background, atmosphere, elements around you. |
| **Fluid Flow** | No hard "views". Zoom in, zoom out, drift between. Spatial, not hierarchical. |

---

## 2026 UI/UX Trends Incorporated

| Trend | How We Apply It |
|-------|-----------------|
| **GenUI** | Agent composes canvas content dynamically using component library |
| **Zero UI** | Anticipatory actions — agent suggests next steps contextually |
| **Scrollytelling** | Story reading as animated, visual journey with scroll triggers |
| **Alive Interfaces** | Motion, parallax, breathing backgrounds, micro-interactions |
| **Hyper-Personalization** | Session memory, reading position, contextual greetings |
| **Conversational Core** | Agent presence panel, CLI-Canvas bridge |

---

## Current Implementation Status

### Fully Implemented (100%)
- Canvas Server (REST API + WebSocket, port 3030)
- Agent Bus (basic routing, port 8284)
- World Manager Tool (save, load, diff, update)
- Story Manager Tool (create, save_segment, branch, continue)
- Asset Manager Tool (save, load, list, delete)
- Image Generator Tool (Google Gemini + OpenAI gpt-image-1.5)
- CLI Interface (Ink-based TUI)
- Settings Manager (local/global config)
- Letta Web UI (Agents, Runs, Trajectories)

### Component Library (Complete ✅)

**Primitives:**
- Image (lightbox, sizing, captions)
- Gallery (grid/carousel)
- Card (variants, accents)
- Timeline (vertical/horizontal)
- Callout, Stats, Badge, Divider
- Stack, Grid layouts
- Button, Text, Dialog

**Experience Primitives (NEW - GenUI Ready):**
- Hero (full viewport, parallax, scroll indicator, badge)
- ScrollSection (scroll-triggered animations: fade-up, slide, scale)
- ProgressBar (reading progress indicator)
- ActionBar (continue/branch action buttons)

All components:
- Registered in DynamicRenderer with full type support
- Use DSF brand colors only (teal #00ffcc, cyan #00ffff)
- No rounded corners, no purple, no bright white
- Support reduced-motion preferences

### Story Demo Components (Built)
- ImmersiveStoryReader with mock data
- StoryHero, StorySection, InlineMedia, WorldContext, StoryActions
- Immersive CSS with scroll physics

**Key Architecture Shift:** Removed static storyConverter in favor of GenUI approach where agent composes experiences dynamically.

### What Agent Can Now Compose

```json
{
  "type": "Stack",
  "children": [
    { "type": "Hero", "props": { "title": "...", "backgroundImage": "..." } },
    { "type": "ProgressBar", "props": { "position": "top" } },
    { "type": "ScrollSection", "props": { "animation": "fade-up" },
      "children": [{ "type": "Text", "props": { "content": "..." } }]
    },
    { "type": "ActionBar", "props": { "actions": [...] } }
  ]
}
```

---

## Implementation Phases (Revised)

### Phase 1: Magical Story Reading ⭐ PRIORITY

**Goal:** Transform story view into immersive scrollytelling experience

**Experience:**
```
┌─────────────────────────────────────────────────────────────┐
│              [FULL BLEED HERO IMAGE]                        │
│                    Story Title                              │
├─────────────────────────────────────────────────────────────┤
│    Story text flows naturally with generous spacing...      │
│                                                             │
│         ┌──────────────────────────────────┐                │
│         │  [Inline Image - scroll animated]│                │
│         └──────────────────────────────────┘                │
│                                                             │
│    ┌────────────────────────────────────────────────────┐   │
│    │ ▸ WORLD RULE: "In 2087, consciousness..."          │   │
│    └────────────────────────────────────────────────────┘   │
│                                                             │
│    ┌─────────┐  ┌─────────┐  ┌─────────┐                   │
│    │CHARACTER│  │LOCATION │  │  TECH   │                   │
│    └─────────┘  └─────────┘  └─────────┘                   │
│                                                             │
│              [FULL BLEED CLIMAX IMAGE]                      │
│                                                             │
│    ┌────────────────────────────────────────────────────┐   │
│    │  [Continue Story]  [Branch: What if...]            │   │
│    └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Components:**
- `ImmersiveStoryReader` - Main container with scroll handling
- `StoryHero` - Full-bleed opening image + title
- `StorySection` - Text block with scroll-triggered fade-in
- `InlineMedia` - Images/galleries that animate on scroll
- `WorldContext` - Callouts showing rules, characters, locations
- `StoryActions` - Continue/branch options

**Technical:**
- Intersection Observer for scroll triggers
- CSS scroll-snap for section flow
- Parallax effects on images
- Generous typography (larger, more spacing)
- Full-bleed imagery breaking the container

**Files to Create:**
- `letta-code/src/canvas/components/story/ImmersiveStoryReader.tsx`
- `letta-code/src/canvas/components/story/StoryHero.tsx`
- `letta-code/src/canvas/components/story/StorySection.tsx`
- `letta-code/src/canvas/styles/immersive.css`

---

### Phase 2: Welcome Back Hero

**Goal:** Contextual entry experience, not cold dashboard

**Experience:**
```
┌─────────────────────────────────────────────────────────────┐
│  [Blurred world cover as background, subtle animation]      │
│                                                             │
│                  ┌─────────────────────────┐                │
│                  │  ◉ Agent                │                │
│                  │  "Welcome back. You     │                │
│                  │   were 3 chapters into  │                │
│                  │   'The Resonance'..."   │                │
│                  └─────────────────────────┘                │
│                                                             │
│           ┌─────────────────────────────────────┐           │
│           │  [World: Affective Resonance]       │           │
│           │  Story: "The Resonance"             │           │
│           │  Chapter 3 of 5 • 12 min read       │           │
│           │  [▶ Continue Reading]               │           │
│           └─────────────────────────────────────┘           │
│                                                             │
│   [Other Worlds]  [Start Something New]  [Ask Agent]        │
└─────────────────────────────────────────────────────────────┘
```

**Technical:**
- Session storage: last world, story, segment, scroll position
- Agent generates contextual greeting
- Background from world cover (blurred, animated)
- Smooth transition to reading

**Files to Create:**
- `letta-code/src/canvas/components/WelcomeHero.tsx`
- `letta-code/src/canvas/hooks/useSession.ts`

---

### Phase 3: Agent Presence Panel

**Goal:** Agent is visible guide, not hidden

**Experience:**
```
┌──────────────────────┐
│ ◉ DSF Agent          │
│ ━━━━━━━━━━━━━━━━━━━━ │
│                      │
│ [Thinking...]        │
│                      │
│ "I could generate    │
│  an image for this   │
│  scene. Want me to?" │
│                      │
│ [Yes] [Not now]      │
│                      │
│ ──────────────────── │
│ 💬 Say something...  │
└──────────────────────┘
```

**Technical:**
- WebSocket to Agent Bus for real-time state
- Agent pushes suggestions/thoughts
- User can type to agent (bridges CLI and Canvas)
- Collapsible, draggable panel
- "Thinking" indicator when agent working

**Files to Create:**
- `letta-code/src/canvas/components/AgentPresence.tsx`
- `letta-code/src/canvas/hooks/useAgentBus.ts`

---

### Phase 4: Worlds as Explorable Spaces

**Goal:** Worlds are environments you step into, not cards

**Experience:**
```
┌─────────────────────────────────────────────────────────────┐
│  [World atmosphere fills background - animated, ambient]    │
│                                                             │
│            ═══════════════════════════════════              │
│                    AFFECTIVE RESONANCE                      │
│                        Year: 2087                           │
│            ═══════════════════════════════════              │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ TIMELINE: ●━━━━━●━━━━━●━━━━━●━━━━━●                    │ │
│  │           2025  2040  2060  2080  NOW                  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ CHARS    │ │ PLACES   │ │ TECH     │ │ RULES    │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│                                                             │
│  ─────────────── STORIES IN THIS WORLD ─────────────────    │
│  "The Resonance" ──────────────────────────── Chapter 3     │
│  "First Contact" ──────────────────────────── Complete      │
└─────────────────────────────────────────────────────────────┘
```

**Technical:**
- Background shifts to world's visual theme
- Timeline component populated with world history
- Cards for characters, locations, technologies, rules
- Stories as "threads" emerging from world

**Files to Modify:**
- `letta-code/src/canvas/app.tsx` - WorldView refactor
- New: `letta-code/src/canvas/components/world/WorldSpace.tsx`

---

### Phase 5: Fluid Navigation

**Goal:** No hard view switches, spatial flow

**Approach:**
- **Zoom metaphor**: Home → World → Story is zooming into fractal
- **Smooth transitions**: Morph animations, not page loads
- **Spatial memory**: Position preserved when zooming out
- **Gestures**: Scroll to progress, keyboard navigation

**Technical:**
- Framer Motion or CSS View Transitions API
- State machine for navigation (XState?)
- Scroll position restoration
- Keyboard shortcuts (j/k navigation, Escape to zoom out)

---

### Phase 6: CLI ↔ Canvas Sync

**Goal:** Real-time synchronization between interfaces

**Tasks:**
- CLI subscribes to Agent Bus events
- Canvas actions trigger agent messages
- Both interfaces show live updates
- "Agent is thinking..." indicators in both

**Files to Modify:**
- `letta-code/src/cli/App.tsx` - Add bus subscription
- `letta-code/src/agent-bus/server.ts` - Event types

---

### Phase 7: Interactive Canvas

**Goal:** Canvas can trigger agent actions

**Tasks:**
- Button clicks send messages to agent
- Form inputs captured and sent
- Choice selections for branching stories
- Event → Agent routing system

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interfaces                           │
│  ┌──────────────┐              ┌──────────────────────────┐ │
│  │ CLI (Ink)    │◄────────────►│ Canvas (React Web)       │ │
│  │              │   Agent Bus  │ - ImmersiveStoryReader   │ │
│  │              │   (8284)     │ - WelcomeHero            │ │
│  │              │              │ - AgentPresence          │ │
│  │              │              │ - WorldSpace             │ │
│  └──────┬───────┘              └──────────┬───────────────┘ │
│         │                                  │                 │
│         └──────────────┬───────────────────┘                 │
│                        ▼                                     │
│              ┌─────────────────┐                             │
│              │   Agent Bus     │                             │
│              │   Port: 8284    │                             │
│              └────────┬────────┘                             │
│                       ▼                                      │
│              ┌─────────────────┐                             │
│              │  Letta Server   │                             │
│              │  Port: 8283     │                             │
│              └────────┬────────┘                             │
│                       │                                      │
│         ┌─────────────┼─────────────┐                        │
│         ▼             ▼             ▼                        │
│  ┌────────────┐ ┌───────────┐ ┌──────────┐                  │
│  │   Tools    │ │  Memory   │ │   LLM    │                  │
│  │ - world    │ │           │ │ Provider │                  │
│  │ - story    │ │           │ │          │                  │
│  │ - image    │ │           │ │          │                  │
│  │ - canvas_ui│ │           │ │          │                  │
│  └────────────┘ └───────────┘ └──────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Library

### Primitives (Phase 2 Complete ✅)
- Image, Gallery, Card, Timeline
- Callout, Stats, Badge, Divider
- Button, Text

### Layout (Phase 2 Complete ✅)
- Stack, Grid

### Story (Phase 1 - Building Now)
- ImmersiveStoryReader
- StoryHero
- StorySection
- WorldContext
- StoryActions

### Navigation (Phase 5)
- FluidTransition
- ZoomContainer

### Agent (Phase 3)
- AgentPresence
- ThinkingIndicator
- SuggestionCard

---

## Success Metrics

| Phase | Metric | Target |
|-------|--------|--------|
| 1 | Story reading feels magical | Qualitative - "wow" factor |
| 2 | Return users see contextual hero | 100% of sessions with history |
| 3 | Agent suggestions are useful | Users click suggestions >20% |
| 4 | Worlds feel like spaces | Time spent exploring increases |
| 5 | Navigation feels fluid | No jarring transitions |

---

## Deprecated / Deferred

- Mobile app (later)
- VR/AR experiences (later)
- AI-generated music/sound (later)
- Community platform (later)
- Multi-user collaboration (later)

---

## Next Action

**Phase 1 Complete** - Experience primitives built, agent can compose.

**Next Steps (in priority order):**

1. **Agent System Prompt Enhancement**
   - Teach agent HOW to compose experiences
   - When to use Hero vs simple Text
   - When to add ScrollSection animations
   - How to structure immersive story presentations

2. **canvas_ui Tool Enhancement**
   - Currently sends to floating overlay
   - Need full-page takeover mode for immersive experiences
   - Target modes: "overlay", "fullscreen", "replace-content"

3. **Bidirectional Flow**
   - ActionBar clicks route back to agent
   - Agent responds to user choices
   - Continue/branch story based on selection

4. **World Experiences**
   - Same GenUI pattern for world exploration
   - Hero with world cover, ScrollSections with lore
   - Character/location/tech cards as ScrollSection children
