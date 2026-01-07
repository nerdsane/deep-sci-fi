# Dynamic Canvas UX Vision: Seamless CLI/Canvas Integration

## Executive Summary

Transform DSF from a dual-interface system (static canvas + CLI) into a **unified experience** where the agent can dynamically create multimedia UX through the canvas while maintaining the power and flexibility of CLI interaction. Users should be able to seamlessly flow between interfaces based on their current context and needs.

## Current Architecture Analysis

### What Works Well

1. **Shared Agent Context** - Both interfaces use the same agent ID, ensuring conversation continuity
2. **File-Based Integration** - `.dsf/` directory serves as a universal data layer
3. **Real-time Sync** - WebSocket + file watching provides live updates
4. **Rich CLI** - Ink-based terminal UI is sophisticated and interactive
5. **Specialized Tools** - `world_manager`, `story_manager`, `image_generator`, `asset_manager` provide structured output

### Current Limitations

1. **One-Way Communication** - Agent → Files → Canvas (passive display only)
2. **Static Canvas** - Cannot create custom UI components dynamically
3. **No Direct Manipulation** - Agent cannot control canvas layout, interactions, or state
4. **Context Switching** - No seamless flow between CLI and canvas views
5. **Rigid Structure** - Canvas displays fixed views (World/Story/Canvas), no custom layouts
6. **No Multimedia Composition** - Cannot create complex multimedia presentations or interactive experiences

## Vision: Dynamic Multimedia Canvas

### Core Principles

1. **Agent as UI Composer** - Agent can orchestrate complex multimedia experiences
2. **Bidirectional Flow** - Canvas can trigger agent actions, agent can update canvas directly
3. **Contextual Interface** - Right interface for the task (CLI for conversation, Canvas for visual)
4. **Unified Experience** - Seamless transitions, shared state, single mental model
5. **Progressive Enhancement** - CLI works standalone, Canvas enhances when needed

### Key Use Cases

#### 1. **Story Presentation Mode**
- Agent creates custom layout for story segment
- Combines text, images, audio, interactive maps
- Reader can explore non-linearly
- Agent adapts presentation based on user interactions

#### 2. **World Building Workshop**
- Agent displays world elements as interactive cards
- User can drag, rearrange, edit inline
- Agent provides contextual suggestions in sidebar
- Changes sync instantly to CLI conversation

#### 3. **Multi-Modal Creation**
- Agent generates image while continuing conversation
- Shows progress in canvas (partial renders, iterations)
- User can provide feedback via canvas annotations
- Final result appears in both interfaces

#### 4. **Interactive Exploration**
- Agent creates a "control panel" for story branches
- User clicks to explore alternatives
- Canvas shows visual diff between branches
- Agent explains implications in CLI

#### 5. **Collaborative Editing**
- Split view: CLI conversation + live canvas preview
- Agent makes suggestions, user sees immediate visual feedback
- Can approve/reject via either interface
- Timeline shows evolution of world/story

## Architecture: Agent-Controlled Canvas

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                      DSF Unified System                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐              ┌──────────────────────┐ │
│  │   CLI Interface  │◄────────────►│  Canvas Interface    │ │
│  │   (Ink/React)    │   Sync       │  (Web/React)         │ │
│  │                  │   Events     │                      │ │
│  │  - Conversation  │              │  - Dynamic UI        │ │
│  │  - Tool calls    │              │  - Multimedia        │ │
│  │  - Approvals     │              │  - Interactions      │ │
│  └────────┬─────────┘              └──────────┬───────────┘ │
│           │                                   │             │
│           │          ┌─────────────┐          │             │
│           └─────────►│  Agent Bus  │◄─────────┘             │
│                      │  (Message   │                        │
│                      │   Broker)   │                        │
│                      └──────┬──────┘                        │
│                             │                               │
│                             ▼                               │
│                    ┌─────────────────┐                      │
│                    │  Letta Server   │                      │
│                    │  + Extensions   │                      │
│                    └────────┬────────┘                      │
│                             │                               │
│              ┌──────────────┼──────────────┐                │
│              │              │              │                │
│              ▼              ▼              ▼                │
│      ┌────────────┐  ┌───────────┐  ┌──────────┐          │
│      │   File     │  │  Canvas   │  │  State   │          │
│      │   System   │  │  State    │  │  Store   │          │
│      │  (.dsf/)   │  │  (JSON)   │  │ (Redis?) │          │
│      └────────────┘  └───────────┘  └──────────┘          │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### New Components

#### 1. **Agent Bus** (Message Broker)
- Central event system for real-time communication
- Publishes: `agent.tool_call`, `agent.message`, `canvas.interaction`, `cli.command`
- Both CLI and Canvas subscribe to relevant events
- Enables true bidirectional communication

#### 2. **Canvas State Manager**
- Separate state layer for UI composition
- Stored as JSON alongside worlds/stories
- Version controlled (can rewind UI states)
- Schema: layouts, components, bindings, interactions

#### 3. **UI Component Library**
- Reusable primitives agent can compose
- Server-side rendered React components
- Supports custom properties and event handlers

#### 4. **Canvas Tool** (New Agent Tool)
- Allows agent to manipulate canvas directly
- Operations: `render`, `update`, `remove`, `layout`, `bind`
- Returns canvas state and user interactions

## UI Primitives & Component System

### Core Primitives

Agent has access to a rich component library:

```typescript
// Layout Primitives
Grid, Stack, Split, Tabs, Accordion, Modal, Sidebar

// Content Primitives
Text, Markdown, Code, Image, Video, Audio, Iframe

// Interactive Primitives
Button, Input, Select, Slider, Toggle, DatePicker

// Visualization Primitives
Timeline, Graph, Map, Chart, Diff, Tree

// Composition Primitives
Card, Panel, Gallery, Carousel, Masonry, Feed

// Story-Specific
StorySegment, WorldCard, CharacterCard, AssetViewer, BranchExplorer
```

### Component Definition Format

Agent describes UI declaratively:

```json
{
  "id": "story-explorer-v1",
  "layout": {
    "type": "Split",
    "direction": "horizontal",
    "sizes": [60, 40],
    "children": [
      {
        "type": "Stack",
        "children": [
          {
            "type": "StorySegment",
            "content": "markdown content...",
            "assets": ["asset-123", "asset-456"]
          },
          {
            "type": "Gallery",
            "items": ["asset-789", "asset-012"],
            "layout": "masonry"
          }
        ]
      },
      {
        "type": "Sidebar",
        "title": "Navigation",
        "children": [
          {
            "type": "Timeline",
            "events": [...],
            "onSelect": "agent.navigate_to_segment"
          }
        ]
      }
    ]
  },
  "interactions": {
    "agent.navigate_to_segment": {
      "type": "send_message",
      "template": "Show me segment {segment_id}"
    }
  }
}
```

### Canvas Tool API

New agent tool for direct canvas manipulation:

```typescript
// Tool Definition
canvas_ui({
  operation: "render" | "update" | "remove" | "layout" | "query",
  component_id?: string,
  definition?: ComponentDefinition,
  layout?: LayoutConfig,
  query?: string
})

// Examples

// 1. Render new UI
canvas_ui({
  operation: "render",
  component_id: "world-workshop",
  definition: {
    type: "Grid",
    cols: 3,
    children: [/* component tree */]
  }
})

// 2. Update existing component
canvas_ui({
  operation: "update",
  component_id: "story-text",
  definition: {
    type: "Markdown",
    content: "Updated content..."
  }
})

// 3. Change layout
canvas_ui({
  operation: "layout",
  component_id: "main-split",
  layout: {
    sizes: [70, 30],
    direction: "vertical"
  }
})

// 4. Query user interactions
canvas_ui({
  operation: "query",
  query: "What did user last interact with?"
})
```

## Seamless CLI/Canvas Switching

### Context-Aware Interface Selection

System intelligently suggests/switches interfaces based on:

1. **Content Type**
   - Heavy multimedia → Canvas
   - Code/text editing → CLI
   - Conversation → CLI
   - Visual exploration → Canvas

2. **User Activity**
   - Typing → CLI gains focus
   - Clicking canvas → Canvas gains focus
   - Agent output → Shows in both (smart routing)

3. **Explicit Commands**
   - `/canvas` - Switch to canvas view
   - `/cli` - Switch to CLI view
   - `/split` - Show both side-by-side

### Smart Output Routing

Agent decides where output should appear:

```typescript
// In agent's system prompt
When responding, consider:
- Text responses → CLI
- Images/multimedia → Canvas (with CLI notification)
- Interactive elements → Canvas
- Code/diffs → CLI
- Complex layouts → Canvas
- Quick confirmations → CLI

You can use canvas_ui tool to create rich presentations,
while maintaining conversation flow in CLI.
```

### Unified Conversation History

Both interfaces show full conversation, but render differently:

**CLI View:**
```
You: Create a cyberpunk city scene
Assistant: I'll create an immersive visual presentation...
[Image generated: cyberpunk-city-001.png]
[Canvas updated: Split view with image gallery]
The city sprawls endlessly...
```

**Canvas View:**
- Shows the generated image in full resolution
- Provides interactive gallery for exploring details
- Displays text as styled overlays
- Includes zoom/pan controls

### Keyboard Shortcuts for Flow

- `Cmd+\` - Toggle between CLI and Canvas
- `Cmd+Shift+\` - Split view
- `Cmd+K` - Focus CLI input (from anywhere)
- `Cmd+J` - Focus Canvas (from anywhere)
- `Esc` - Return to last active interface

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

**Goal:** Enable basic agent-to-canvas communication

- [ ] Implement Agent Bus (WebSocket-based message broker)
- [ ] Create Canvas State Manager (JSON store + versioning)
- [ ] Add basic `canvas_ui` tool with `render` operation
- [ ] Build 5 core primitives: `Text`, `Image`, `Stack`, `Grid`, `Card`
- [ ] Update canvas to consume canvas state JSON
- [ ] Test: Agent can create simple card layouts

### Phase 2: Bidirectional Communication (Week 3-4)

**Goal:** Canvas can talk back to agent

- [ ] Add interaction handlers to components
- [ ] Implement `canvas_ui` `query` operation
- [ ] Create event routing from Canvas → Agent Bus → Agent
- [ ] Add `update` and `remove` operations to canvas_ui
- [ ] Test: User clicks button in canvas, agent receives event and responds

### Phase 3: Rich Component Library (Week 5-6)

**Goal:** Expand UI primitives

- [ ] Implement interactive primitives: `Button`, `Input`, `Select`, `Slider`
- [ ] Add visualization primitives: `Timeline`, `Gallery`, `Diff`
- [ ] Create story-specific components: `StorySegment`, `WorldCard`, `BranchExplorer`
- [ ] Build composition primitives: `Split`, `Tabs`, `Modal`, `Sidebar`
- [ ] Test: Agent creates complex multi-panel story presentation

### Phase 4: Seamless Switching (Week 7-8)

**Goal:** Unified CLI/Canvas experience

- [ ] Implement smart output routing logic
- [ ] Add keyboard shortcuts for interface switching
- [ ] Build split-view mode (CLI + Canvas side-by-side)
- [ ] Create unified conversation history renderer
- [ ] Add context-aware interface suggestions
- [ ] Test: User flows seamlessly between interfaces during session

### Phase 5: Advanced Features (Week 9-10)

**Goal:** Polish and power features

- [ ] Add canvas state versioning (rewind UI)
- [ ] Implement canvas templates (agent can save/reuse layouts)
- [ ] Build collaborative editing mode (live preview while conversing)
- [ ] Add canvas state to agent memory (remember user preferences)
- [ ] Create canvas state inspector (debug UI compositions)
- [ ] Performance optimization (lazy loading, virtual scrolling)

### Phase 6: Polish & Launch (Week 11-12)

**Goal:** Production ready

- [ ] Comprehensive testing (unit, integration, E2E)
- [ ] Documentation (user guide, tool API reference)
- [ ] Example workflows (story presentation, world building, etc.)
- [ ] Performance benchmarking
- [ ] User testing and feedback integration
- [ ] Release v1.0

## Technical Decisions

### Agent Bus Implementation

**Option A: WebSocket Server** (Recommended)
- Pros: Real-time, low latency, bidirectional
- Cons: Requires persistent connection
- Implementation: Extend existing canvas WebSocket server

**Option B: Server-Sent Events (SSE)**
- Pros: Simpler, built-in reconnection
- Cons: One-way (need separate POST for Canvas → Agent)
- Implementation: Add SSE endpoint to canvas server

**Option C: Redis Pub/Sub**
- Pros: Scalable, decoupled
- Cons: Additional dependency, complexity
- Implementation: Add Redis to docker-compose

**Decision: Start with Option A** (WebSocket) as it's already partially implemented and provides the best UX. Can migrate to Redis later for scalability.

### Canvas State Storage

**Option A: File System** (`.dsf/canvas/states/*.json`)
- Pros: Consistent with current architecture, simple
- Cons: Performance, no real-time queries
- Implementation: Extend existing file watching

**Option B: In-Memory + Persistence**
- Pros: Fast, flexible querying
- Cons: Lost on restart (need to persist)
- Implementation: JSON files + in-memory cache

**Option C: Database** (Postgres/SQLite)
- Pros: Queryable, transactional, scalable
- Cons: Over-engineering for current scale
- Implementation: Add to Letta's existing DB

**Decision: Start with Option B** (in-memory + JSON persistence). This provides speed for real-time updates while maintaining simplicity. Can migrate to DB later if needed.

### Component Rendering

**Option A: Server-Side React**
- Pros: Type-safe, reusable, rich ecosystem
- Cons: Complexity, serialization overhead
- Implementation: React Server Components or custom renderer

**Option B: JSON → Client-Side React**
- Pros: Simple, flexible, agent outputs pure data
- Cons: Security (eval), client-side complexity
- Implementation: JSON schema + React component mapping

**Option C: Hybrid** (Templates + Slots)
- Pros: Balance of structure and flexibility
- Cons: Learning curve, custom system
- Implementation: Predefined templates with customizable slots

**Decision: Option B** (JSON → Client-Side React). Agent outputs declarative JSON, canvas client interprets. This keeps agent logic simple and provides maximum flexibility. Use strict schema validation for security.

## Security Considerations

1. **Component Injection** - Validate all component definitions against schema
2. **Event Handlers** - Whitelist allowed interaction types, no arbitrary code execution
3. **Asset Access** - Scope asset loading to user's `.dsf/` directory only
4. **WebSocket Auth** - Verify agent ID matches session
5. **Rate Limiting** - Prevent canvas update spam

## Success Metrics

1. **Seamless Flow** - Users switch <3 times per session (down from ~10)
2. **Rich Presentations** - 80% of stories include custom canvas layouts
3. **Interaction** - Users interact with canvas UI (clicks, inputs) 5+ times per session
4. **Performance** - Canvas updates render <100ms
5. **Adoption** - 90% of users enable canvas (vs 20% currently)

## Open Questions

1. Should canvas state be part of world/story checkpoints? (Can you "rewind" UI?)
2. How to handle canvas state in multi-user scenarios? (Shared worlds)
3. Should agent be able to create reusable canvas templates?
4. How to preview canvas changes before applying? (Like diff for UI)
5. Should CLI have inline canvas preview? (Terminal-based rendering)
6. How to export canvas presentations? (PDF, standalone HTML)

## Conclusion

By transforming the canvas from a passive viewer into an agent-controllable dynamic UI platform, we unlock new possibilities for multimedia storytelling and world building. The key is maintaining the power and flexibility of CLI interaction while enhancing visual/interactive experiences through the canvas.

The architecture prioritizes:
- **Simplicity** - Start with WebSocket + JSON, evolve as needed
- **Flexibility** - Agent has full control over UI composition
- **Performance** - Real-time updates without sacrificing responsiveness
- **Usability** - Seamless switching based on context

This vision transforms DSF from a "CLI with a viewer" into a "unified creative environment" where the agent can orchestrate rich multimedia experiences while maintaining conversational interaction.
