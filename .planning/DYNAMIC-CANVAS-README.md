# Dynamic Canvas: Agent-Controlled Multimedia UX

## Vision

Transform DSF from a dual-interface system (static canvas + CLI) into a **unified multimedia experience** where the agent can dynamically create rich, interactive UI presentations while users seamlessly flow between CLI conversation and visual exploration.

## Current State

**What we have:**
- CLI chat interface (Ink-based terminal UI)
- Canvas web UI (static viewer for worlds/stories)
- File-based integration (`.dsf/` directory)
- Specialized tools: `world_manager`, `story_manager`, `image_generator`, `asset_manager`

**Limitations:**
- Canvas is passive - just displays files
- Agent cannot control UI directly
- No bidirectional communication
- Awkward context switching between CLI and canvas

## Future State

**What we're building:**
- Agent composes dynamic UI layouts through `canvas_ui` tool
- Real-time bidirectional communication via Agent Bus
- Rich component library (cards, galleries, timelines, interactive widgets)
- Seamless CLI/Canvas integration (one conversation, multiple views)
- User interactions in canvas trigger agent responses

**Example Use Case:**

```
User: "Create an immersive presentation for the cyberpunk city story"

Agent: (via canvas_ui tool)
- Creates split layout: story text (65%) + navigation sidebar (35%)
- Renders story segment with embedded images
- Adds interactive timeline for exploring chapters
- Includes "Continue Story" button

User: (clicks timeline event in canvas)

Agent: (receives canvas interaction)
- Updates story segment with selected chapter
- Highlights active timeline item
- Continues conversation in CLI about the chapter
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  DSF Unified System                  │
├─────────────────────────────────────────────────────┤
│                                                       │
│  ┌──────────┐         ┌──────────────┐         ┌────┴─────┐
│  │   CLI    │◄───────►│  Agent Bus   │◄───────►│  Canvas  │
│  │  (Ink)   │  Events │ (WebSocket)  │  Events │  (React) │
│  └──────────┘         └──────┬───────┘         └──────────┘
│                              │                              │
│                              ▼                              │
│                    ┌──────────────────┐                     │
│                    │  Letta Server    │                     │
│                    │  + canvas_ui     │                     │
│                    └────────┬─────────┘                     │
│                             │                               │
│              ┌──────────────┼──────────────┐                │
│              │              │              │                │
│              ▼              ▼              ▼                │
│      ┌─────────────┐ ┌─────────────┐ ┌─────────────┐      │
│      │  File Sys   │ │ Canvas State│ │  Agent Mem  │      │
│      │  (.dsf/)    │ │   (JSON)    │ │  (Letta DB) │      │
│      └─────────────┘ └─────────────┘ └─────────────┘      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Agent Bus** - Real-time message broker (WebSocket) for bidirectional communication
2. **canvas_ui Tool** - Agent tool for creating/updating UI components
3. **Canvas State Manager** - Stores and manages UI component definitions
4. **Component Library** - Reusable UI primitives (layouts, content, interactive, visualizations)
5. **Event Handlers** - Routes user interactions back to agent

## Documentation Structure

### 📄 [Dynamic Canvas UX Vision](./ux/dynamic-canvas-ux-vision.md)
**Comprehensive vision document covering:**
- Current architecture analysis
- Vision for dynamic multimedia canvas
- Agent-controlled canvas architecture
- UI primitives & component system
- Seamless CLI/Canvas switching UX
- 12-week implementation roadmap
- Technical decisions and trade-offs
- Success metrics

**Read this first** to understand the full vision and strategic direction.

### 📄 [Component Strategy](./ux/component-strategy.md)
**How to build agent-composable UI with your styling:**
- Why Radix UI is the perfect fit
- Component architecture and mapping
- Keeping your neon cyberpunk aesthetic
- Complete styling approach with code examples
- 3-week implementation roadmap

**Read this** to understand the component library approach.

### 📄 [Canvas Architecture Decision](./ux/canvas-architecture-decision.md)
**Should canvas be in letta-code or separate?**
- Analysis of monorepo vs separate projects
- Current tight coupling points
- When to separate (and when not to)
- Future-proofing strategies

**Read this** to understand the architectural decisions.

### 📄 [Radix Integration Quickstart](./ux/radix-integration-quickstart.md)
**Get your first agent-composable component working in 30 minutes:**
- Install Radix packages
- Create styled Dialog component
- Add CSS matching your aesthetic
- Make it agent-controllable
- Test end-to-end

**Read this** when ready to start building. Get hands-on quickly!

### 📄 [Implementation Guide](./ux/implementation-guide.md)
**Step-by-step walkthrough for building Phase 1 (Foundation):**
- Week 1: Agent Bus & State Management
- Week 2: Canvas Client & UI Components
- Day-by-day tasks with code examples
- Testing procedures
- Success checklist
- Troubleshooting tips

**Read this** for the complete 2-week implementation plan.

### 📄 [Agent Bus Technical Spec](./technical-specs/agent-bus.md)
**Detailed specification for the message broker:**
- Event types (agent, canvas, CLI, system)
- WebSocket protocol
- Message routing and subscription management
- Event store and persistence
- Security and performance considerations
- Implementation guide
- Testing strategy

**Read this** when implementing real-time communication between components.

### 📄 [Canvas UI Tool Technical Spec](./technical-specs/canvas-ui-tool.md)
**Complete specification for the canvas_ui agent tool:**
- Tool definition and operations (render, update, remove, layout, query)
- Component definitions (layouts, content, interactive, visualizations)
- Event handlers and interactions
- Implementation details
- System prompt integration
- Error handling and testing

**Read this** when implementing the agent's ability to control canvas UI.

## Quick Start

### Prerequisites
- Existing DSF system running (Letta server, CLI, Canvas)
- Bun runtime
- Basic understanding of WebSockets and React

### Phase 1: Foundation (2 weeks)

**Goal:** Enable basic agent-to-canvas communication with 5 core UI primitives.

**Week 1: Infrastructure**
1. Implement Agent Bus (WebSocket server + client)
2. Create Canvas State Manager
3. Build canvas_ui tool
4. Register tool with Letta

**Week 2: UI Components**
1. Connect Canvas to Agent Bus
2. Build ComponentRenderer
3. Implement 5 core primitives: Text, Button, Stack, Card, Image
4. Test end-to-end flow

**Success Criteria:**
- Agent can create simple card layouts via canvas_ui
- Canvas displays agent-created UI in real-time
- User can click buttons in canvas
- Agent receives interaction events

**Follow:** [Implementation Guide](./ux/implementation-guide.md) for detailed steps.

## Component Library (Phase 1)

### Layout Components
- **Stack** - Vertical/horizontal stack with spacing
- **Grid** - CSS Grid layout
- **Split** - Two-pane split view

### Content Components
- **Text** - Styled text content
- **Markdown** - Rendered markdown
- **Image** - Image display

### Interactive Components
- **Button** - Clickable button with event handler

### Composition Components
- **Card** - Container with border/shadow

## Example Usage

### Agent Creates Simple UI

```typescript
// Agent executes canvas_ui tool
canvas_ui({
  operation: "render",
  component_id: "welcome-card",
  definition: {
    type: "Card",
    children: {
      type: "Stack",
      spacing: 16,
      children: [
        {
          type: "Text",
          content: "Welcome to the Neon Underground",
          variant: "heading",
          size: "xl"
        },
        {
          type: "Image",
          src: "asset-city-001",
          alt: "Cyberpunk city street"
        },
        {
          type: "Button",
          label: "Begin Story",
          variant: "primary",
          onClick: "agent.start_story"
        }
      ]
    }
  }
})
```

### Canvas Displays UI

The canvas receives this via Agent Bus and renders:

```
┌─────────────────────────────────────┐
│                                     │
│  Welcome to the Neon Underground    │
│                                     │
│  [Image: Cyberpunk city street]    │
│                                     │
│          [ Begin Story ]            │
│                                     │
└─────────────────────────────────────┘
```

### User Interacts

User clicks "Begin Story" button.

Canvas publishes interaction event:
```json
{
  "type": "canvas.interaction",
  "payload": {
    "component_id": "welcome-card",
    "interaction_type": "click",
    "data": {},
    "target": "agent.start_story"
  }
}
```

### Agent Responds

Agent receives event and responds:
```typescript
// Agent sees: "User clicked 'Begin Story' button"

// Agent updates canvas
canvas_ui({
  operation: "update",
  component_id: "welcome-card",
  definition: {
    children: {
      children: [
        {
          type: "Text",
          content: "Chapter 1: The Market",
          variant: "heading"
        },
        {
          type: "Markdown",
          content: "The neon signs flickered overhead as Alex..."
        }
      ]
    }
  }
})

// Agent also responds in CLI
"I've loaded Chapter 1. The story begins in a bustling market..."
```

## Roadmap

### Phase 1: Foundation (Weeks 1-2) ✓ Planned
- Agent Bus implementation
- Canvas State Manager
- canvas_ui tool
- 5 core primitives

### Phase 2: Bidirectional Communication (Weeks 3-4)
- Interaction handlers
- Event routing from Canvas → Agent
- Query operations
- Update/remove operations

### Phase 3: Rich Component Library (Weeks 5-6)
- Interactive primitives (Input, Select, Slider, Toggle)
- Visualization primitives (Timeline, Gallery, Diff)
- Story-specific components (StorySegment, WorldCard, BranchExplorer)
- Composition primitives (Tabs, Modal, Sidebar)

### Phase 4: Seamless Switching (Weeks 7-8)
- Smart output routing
- Keyboard shortcuts
- Split-view mode
- Context-aware interface suggestions

### Phase 5: Advanced Features (Weeks 9-10)
- Canvas state versioning
- Canvas templates
- Collaborative editing
- Performance optimization

### Phase 6: Polish & Launch (Weeks 11-12)
- Comprehensive testing
- Documentation
- Example workflows
- User testing

## Technical Decisions

### Communication: WebSocket (Agent Bus)
**Why:** Real-time, bidirectional, low latency, already partially implemented
**Alternative considered:** Redis Pub/Sub (more scalable but adds complexity)

### State Storage: In-Memory + JSON Files
**Why:** Fast for real-time updates, simple persistence
**Alternative considered:** PostgreSQL (over-engineering for current scale)

### Component Rendering: JSON → Client-Side React
**Why:** Agent outputs declarative data, maximum flexibility
**Alternative considered:** Server-Side React (more complex serialization)

## Success Metrics

1. **Seamless Flow** - Users switch <3 times per session (down from ~10)
2. **Rich Presentations** - 80% of stories include custom canvas layouts
3. **Interaction** - Users interact with canvas UI 5+ times per session
4. **Performance** - Canvas updates render <100ms
5. **Adoption** - 90% of users enable canvas (vs 20% currently)

## FAQ

**Q: Will this break existing file-based workflow?**
A: No. Canvas will support both file-based content and dynamic UI components. Existing stories/worlds continue to work.

**Q: Can I use canvas without CLI?**
A: Yes. Canvas can trigger agent operations independently (already supported).

**Q: What about mobile?**
A: Phase 1 focuses on desktop. Mobile support comes in later phases with responsive components.

**Q: How does this affect agent memory/tokens?**
A: Canvas state is external to agent memory. Agent only sees interaction events, not full UI state.

**Q: Can users customize canvas appearance?**
A: Phase 5 includes canvas templates. Users can save/reuse layouts.

**Q: What about accessibility?**
A: All components will follow ARIA guidelines. Keyboard navigation support in Phase 4.

## Contributing

1. Read the vision document to understand the direction
2. Review technical specs for the component you want to work on
3. Follow the implementation guide for step-by-step instructions
4. Test your changes with the test scripts provided
5. Submit PRs with clear descriptions

## Resources

- [Letta Server Docs](https://github.com/letta-ai/letta)
- [Ink Terminal UI](https://github.com/vadimdemedes/ink)
- [WebSocket API](https://github.com/websockets/ws)
- [React Component Patterns](https://reactpatterns.com/)

## Contact

For questions or discussions about the Dynamic Canvas project:
- Create an issue in the repo
- Tag @sesh for architecture questions
- Join the DSF development channel

---

**Status:** 📋 Planning Complete → 🚀 Ready for Implementation

**Next Action:** Follow [Implementation Guide](./ux/implementation-guide.md) to build Phase 1

**Estimated Timeline:** 2 weeks for Phase 1, 12 weeks total for full vision
