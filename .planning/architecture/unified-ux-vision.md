# Deep Sci-Fi: Unified Multi-Interface UX Architecture

## Vision Statement

Create a **seamless, agent-driven narrative experience** where users can fluidly move between CLI and web interfaces, with the agent dynamically composing rich, interactive experiences on-demand.

**Core Principles:**
1. **Interface-Agnostic Continuity** - Start anywhere, continue anywhere
2. **Agent-Driven UX** - AI composes experiences, not just content
3. **Rich Media Integration** - Images, visualizations, interactive elements throughout
4. **Real-Time Synchronization** - All interfaces see live updates
5. **Progressive Enhancement** - CLI works standalone, web adds richness

---

## Current State Analysis

### What Works
✅ Rich data models (World, Story, Segments)
✅ Agent-driven tool execution
✅ Multi-provider image generation
✅ File-based storage (simple, portable)
✅ Gallery server with file watching

### Critical Gaps
❌ **CLI-only workflow** - Web UI doesn't know about DSF
❌ **Gallery read-only** - Non-functional edit/create buttons
❌ **No cross-interface state** - Can't continue session in different interface
❌ **Images not displayed** - Generated but not shown inline
❌ **Fixed UI paradigm** - No dynamic, agent-composed experiences

---

## Architectural Vision

```
┌─────────────────────────────────────────────────────────────────┐
│  Multi-Interface User Layer                                     │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ CLI/TUI      │  │ Web UI       │  │ Mobile       │         │
│  │ (Terminal)   │  │ (Browser)    │  │ (Future)     │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                  │
│         └──────────────────┴──────────────────┘                  │
│                            │                                      │
│                    Unified API Layer                             │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│  DSF Server (Enhanced Gallery + New Capabilities)               │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ REST/GraphQL API                                           │ │
│  │  • Worlds (CRUD)                                           │ │
│  │  • Stories (CRUD + branching)                              │ │
│  │  • Assets (upload, serve, CDN)                             │ │
│  │  • Sessions (context tracking)                             │ │
│  │  • Experiences (agent-composed UIs)                        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ WebSocket Server                                           │ │
│  │  • Real-time updates (world/story changes)                 │ │
│  │  • Cross-interface sync (CLI ↔ Web)                       │ │
│  │  • Live agent activity (show AI thinking)                  │ │
│  │  • Collaborative sessions (future)                         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Agent Integration Layer                                    │ │
│  │  • Forward requests to Letta server                        │ │
│  │  • Execute agent operations from web UI                    │ │
│  │  • Stream agent responses to any interface                 │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│  Agent Runtime (Letta Server + Enhanced Tools)                  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Existing Tools                                             │ │
│  │  • world_manager (save, load, update, diff)                │ │
│  │  • story_manager (create, save_segment, branch, continue)  │ │
│  │  • asset_manager (save, load, list, delete)                │ │
│  │  • image_generator (OpenAI, Google providers)              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ NEW: Experience Composer Tools                             │ │
│  │                                                              │ │
│  │  • ui_composer - Dynamically create UI layouts             │ │
│  │     - Define components (gallery, timeline, graph)         │ │
│  │     - Position elements (grid, split, tabs)                │ │
│  │     - Inject into web UI as live experiences               │ │
│  │                                                              │ │
│  │  • session_manager - Track cross-interface context         │ │
│  │     - Current world, story, segment                        │ │
│  │     - User preferences, reading position                   │ │
│  │     - Active explorations, branches                        │ │
│  │                                                              │ │
│  │  • visual_composer - Rich image placement                  │ │
│  │     - Inline, full-width, gallery, background              │ │
│  │     - Parallax, fade-in, reveal effects                    │ │
│  │     - CLI: [Image] marker, Web: full render                │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│  Unified Storage Layer                                          │
│                                                                  │
│  .dsf/                                                           │
│  ├── worlds/                                                     │
│  │   ├── {checkpoint_name}.json                                 │
│  │   └── ...                                                     │
│  ├── stories/                                                    │
│  │   ├── {world_checkpoint}/                                    │
│  │   │   ├── {story_id}.json                                    │
│  │   │   └── ...                                                 │
│  │   └── ...                                                     │
│  ├── assets/                                                     │
│  │   ├── {story_id}/                                            │
│  │   │   ├── img_{timestamp}.png                                │
│  │   │   └── ...                                                 │
│  │   └── worlds/                                                 │
│  │       └── {world_checkpoint}/                                │
│  │           └── cover.png                                       │
│  ├── sessions/              (NEW)                               │
│  │   ├── {session_id}.json                                      │
│  │   └── ...                                                     │
│  └── experiences/            (NEW)                               │
│      ├── {experience_id}.json                                   │
│      └── ...                                                     │
└──────────────────────────────────────────────────────────────────┘
```

---

## Key Innovations

### 1. Session Management (Cross-Interface Continuity)

**Problem:** User starts in CLI, wants to continue in web UI - but context is lost.

**Solution:** Persistent session state tracked across interfaces.

**Session Model:**
```typescript
interface Session {
  id: string;
  user_id: string;
  created: string;
  last_active: string;

  // Current narrative context
  context: {
    active_world?: string;        // checkpoint name
    active_story?: string;         // story ID
    current_segment?: string;      // segment ID
    reading_position?: number;     // word offset
    active_branches?: string[];    // endpoints being explored
  };

  // User preferences
  preferences: {
    interface: "cli" | "web" | "mobile";
    theme: "light" | "dark";
    reading_speed?: "slow" | "medium" | "fast";
    image_display: "inline" | "gallery" | "minimal";
  };

  // Live state
  state: {
    connected_interfaces: string[];  // ["cli", "web"]
    agent_active: boolean;
    pending_operations?: string[];   // ["generating_image", "writing_segment"]
  };
}
```

**Tool: `session_manager`**
```typescript
interface SessionManagerTool {
  operation:
    | "create"           // Start new session
    | "load"             // Resume existing session
    | "update_context"   // Set active world/story/segment
    | "update_prefs"     // Change user preferences
    | "sync"             // Force sync across interfaces
    | "close";           // End session

  session_id?: string;
  context?: Partial<SessionContext>;
  preferences?: Partial<SessionPreferences>;
}
```

**UX Flow:**
1. User starts in CLI: `./deep-scifi.js`
2. Agent creates session, stores in `.dsf/sessions/{id}.json`
3. User opens web UI, authenticates
4. Web loads active session, shows exact same context
5. User clicks "Continue Story" in web
6. Agent resumes from last segment, writes next part
7. CLI (if still open) sees live update via WebSocket
8. User can switch interfaces at any time, zero friction

---

### 2. Agent-Composed Experiences (Dynamic UI)

**Problem:** Fixed UI layouts can't adapt to unique narrative moments.

**Solution:** Agent dynamically creates custom UI experiences using a component library.

**Experience Model:**
```typescript
interface Experience {
  id: string;
  type:
    | "story_moment"         // Special narrative reveal
    | "world_exploration"    // Interactive world diving
    | "character_focus"      // Character deep-dive
    | "choice_point"         // Branching decision
    | "visualization";       // Data/timeline/graph

  layout: {
    type: "grid" | "split" | "tabs" | "modal" | "fullscreen";
    regions: LayoutRegion[];
  };

  components: ExperienceComponent[];

  triggers?: {
    on_load?: AgentAction[];    // Agent actions when experience loads
    on_interact?: AgentAction[]; // Agent responds to user input
  };

  metadata: {
    story_id?: string;
    segment_id?: string;
    created: string;
    duration?: number;  // Auto-dismiss after N seconds
  };
}

interface ExperienceComponent {
  id: string;
  type:
    | "narrative"           // Story text
    | "image"               // Single image
    | "gallery"             // Image carousel
    | "timeline"            // Historical events
    | "graph"               // Relationship/concept map
    | "character_card"      // Character bio + portrait
    | "location_map"        // World geography
    | "rule_explorer"       // Physics/tech rules
    | "choice_buttons"      // Branching options
    | "agent_chat";         // Live conversation

  props: Record<string, any>;  // Component-specific props
  position: { region: string; order: number };
  styling?: {
    animation?: "fade" | "slide" | "reveal";
    theme?: "dramatic" | "technical" | "mysterious";
  };
}
```

**Tool: `ui_composer`**
```typescript
interface UIComposerTool {
  operation:
    | "create"      // Create new experience
    | "update"      // Modify existing experience
    | "show"        // Display to user
    | "dismiss";    // Close experience

  experience_id?: string;
  experience?: Experience;
  target_interface?: "web" | "all";  // CLI gets simplified version
}
```

**Example: Agent creates character reveal moment**

Agent decides: "Nia's backstory is a critical reveal - create immersive experience"

```typescript
agent calls ui_composer({
  operation: "create",
  experience: {
    type: "character_focus",
    layout: {
      type: "split",
      regions: [
        { id: "left", width: "40%" },
        { id: "right", width: "60%" }
      ]
    },
    components: [
      {
        type: "image",
        props: {
          src: "assets/the_neural_canvas/nia_portrait.png",
          caption: "Nia Chen, Neural Artist"
        },
        position: { region: "left", order: 1 },
        styling: { animation: "fade" }
      },
      {
        type: "narrative",
        props: {
          content: "Nia never wanted to be an artist. She wanted to be a surgeon...",
          voice: "introspective"
        },
        position: { region: "right", order: 1 }
      },
      {
        type: "timeline",
        props: {
          events: [
            { year: 2025, event: "Neural interface accident" },
            { year: 2027, event: "First artistic breakthrough" },
            { year: 2035, event: "Present day" }
          ]
        },
        position: { region: "right", order: 2 }
      },
      {
        type: "choice_buttons",
        props: {
          prompt: "How do you want to explore Nia's story?",
          choices: [
            { label: "The accident", value: "branch_accident" },
            { label: "Her art", value: "branch_art" },
            { label: "Continue main story", value: "continue_main" }
          ]
        },
        position: { region: "right", order: 3 }
      }
    ],
    triggers: {
      on_interact: [
        { type: "agent_message", message: "User chose: {{choice}}" }
      ]
    }
  }
})
```

**Web UI Rendering:**
- React component library interprets experience JSON
- Renders dynamic layout with positioned components
- User interactions sent back to agent
- Agent continues narrative based on choice

**CLI Rendering:**
- Simplified text-based version
- Shows narrative, lists choices
- Images shown as `[Portrait: Nia Chen]`
- Timeline rendered as ASCII art or bullet points

---

### 3. Rich Image Integration

**Problem:** Images generated but not displayed, no placement control.

**Solution:** Agent specifies image placement/presentation, interfaces render appropriately.

**Enhanced Story Segment with Visual Data:**
```typescript
interface StorySegment {
  id: string;
  content: string;  // Markdown with image markers: ![](asset_id)
  word_count: number;
  parent_segment: string | null;

  // NEW: Visual composition
  visuals?: {
    hero_image?: {  // Primary image for segment
      asset_id: string;
      placement: "top" | "background" | "inline";
      effects?: ("parallax" | "fade" | "blur")[];
    };
    inline_images?: {  // Images within narrative
      asset_id: string;
      position: number;  // Word offset
      size: "small" | "medium" | "large" | "full";
      caption?: string;
    }[];
    gallery?: {  // Carousel of related images
      asset_ids: string[];
      trigger: "manual" | "auto";  // User opens or auto-plays
    };
  };

  world_evolution: { /* ... existing ... */ };
  assets?: StoryAsset[];
  branches?: StoryBranch[];
}
```

**Tool: `visual_composer`**
```typescript
interface VisualComposerTool {
  operation:
    | "set_hero"        // Set primary segment image
    | "add_inline"      // Place image at position
    | "create_gallery"  // Multi-image carousel
    | "apply_effects";  // Visual effects

  story_id: string;
  segment_id: string;
  asset_id: string;

  placement?: {
    type: "top" | "background" | "inline";
    position?: number;  // For inline: word offset
    size?: "small" | "medium" | "large" | "full";
  };

  effects?: ("parallax" | "fade" | "blur" | "reveal")[];
}
```

**Enhanced Image Generation Flow:**

1. Agent writing story, decides image needed:
   ```typescript
   image_generator({
     prompt: "Watercolor: Neural interface headset, soft blues and purples",
     provider: "google",
     save_as_asset: true,
     story_id: "the_neural_canvas"
   })
   // Returns: { asset_id: "img_1735635000000", url: "..." }
   ```

2. Agent places image in narrative:
   ```typescript
   visual_composer({
     operation: "add_inline",
     story_id: "the_neural_canvas",
     segment_id: "seg_003",
     asset_id: "img_1735635000000",
     placement: {
       type: "inline",
       position: 450,  // After "She put on the headset."
       size: "medium"
     }
   })
   ```

3. Agent saves segment with visual metadata:
   ```typescript
   story_manager({
     operation: "save_segment",
     story_id: "the_neural_canvas",
     segment: {
       content: "She put on the headset. The world shifted...",
       visuals: {
         inline_images: [{
           asset_id: "img_1735635000000",
           position: 450,
           size: "medium",
           caption: "The neural interface headset"
         }]
       }
     }
   })
   ```

4. **Web UI:** Renders markdown, injects image at position 450
5. **CLI:** Shows `[Image: The neural interface headset]` at position 450

---

### 4. Real-Time Cross-Interface Synchronization

**Problem:** Changes in one interface not visible in others.

**Solution:** WebSocket broadcasts + shared session state.

**WebSocket Event Types:**
```typescript
type WebSocketEvent =
  | { type: "world.updated", world_checkpoint: string }
  | { type: "story.segment_added", story_id: string, segment_id: string }
  | { type: "story.branched", story_id: string, branch_from: string, branch_to: string }
  | { type: "asset.created", asset_id: string, story_id: string }
  | { type: "session.context_changed", session_id: string, context: SessionContext }
  | { type: "agent.thinking", status: "active" | "idle", message?: string }
  | { type: "experience.created", experience_id: string, target: "web" | "all" };
```

**UX Flow:**

1. **User in CLI:** Asks agent to continue story
2. **Agent:** Starts writing, broadcasts `agent.thinking`
3. **Web UI (if open):** Shows "Agent is writing..." indicator
4. **Agent:** Completes segment, calls `story_manager({ operation: "save_segment" })`
5. **DSF Server:** Saves segment, broadcasts `story.segment_added`
6. **All interfaces:** Update story view, show new segment
7. **CLI:** Displays new text
8. **Web UI:** Animates new segment sliding in

**Benefits:**
- **Live collaboration** - See agent work in real-time
- **Cross-device** - Start on desktop CLI, continue on mobile web
- **Multi-user future** - Multiple people exploring same world

---

## Implementation Roadmap

### Phase 1: Unified Data Layer (Foundation)
**Goal:** Make worlds/stories accessible to both CLI and web

**Tasks:**
1. **Enhance Gallery Server → DSF Server**
   - Add REST API endpoints (CRUD for worlds/stories/assets)
   - Add WebSocket server for real-time updates
   - Keep file watching for hot-reload
   - Port: 3030 (or separate for API)

2. **Update CLI to use DSF Server**
   - Optional mode: Use server API instead of direct file access
   - Environment variable: `DSF_API_URL=http://localhost:3030`
   - Fallback: Direct file access if server not running
   - Backwards compatible: Existing file-based workflow still works

3. **Update Letta UI for DSF**
   - New route: `/dsf` (DSF-specific interface)
   - Views: World browser, Story reader
   - Use DSF Server API
   - Separate from standard Letta agent UI

**Success Criteria:**
✅ CLI can read/write via API or files
✅ Web UI can read/write via API
✅ Both see same data
✅ No breaking changes to existing workflows

---

### Phase 2: Session Management (Cross-Interface Continuity)
**Goal:** User can seamlessly switch between CLI and web

**Tasks:**
1. **Create Session Data Model**
   - `.dsf/sessions/{id}.json` structure
   - Session context (world, story, segment, position)
   - User preferences

2. **Implement `session_manager` Tool**
   - Operations: create, load, update_context, sync
   - Agent uses to track user's current state
   - Automatic context updates on world/story changes

3. **Update Interfaces for Session Awareness**
   - CLI: Load session on startup, update on changes
   - Web: Load session on auth, show "Continue where you left off"
   - Both: Subscribe to session updates via WebSocket

4. **Add "Handoff" UX**
   - CLI: Show QR code → scan to open web at exact position
   - Web: Show "Open in CLI" with command to copy
   - Instant context transfer

**Success Criteria:**
✅ User starts in CLI, opens web → exact same position
✅ User makes changes in web → CLI updates live
✅ Zero-friction interface switching

---

### Phase 3: Rich Visual Integration
**Goal:** Images displayed inline, agent controls placement

**Tasks:**
1. **Enhance Story Segment Model**
   - Add `visuals` field with hero_image, inline_images, gallery
   - Markdown with image markers: `![](asset_id)`

2. **Implement `visual_composer` Tool**
   - Operations: set_hero, add_inline, create_gallery, apply_effects
   - Agent specifies placement/presentation
   - Updates segment's visual metadata

3. **Update Image Generation Workflow**
   - `image_generator` returns asset_id
   - Agent calls `visual_composer` to place image
   - Agent saves segment with visual data

4. **Render Images in Interfaces**
   - Web: Full rendering with effects (parallax, fade, etc.)
   - CLI: Show `[Image: caption]` markers
   - Both: Link to open in viewer

**Success Criteria:**
✅ Agent can place images at specific narrative positions
✅ Web renders images inline with effects
✅ CLI shows image markers with option to view
✅ Images feel integrated, not tacked-on

---

### Phase 4: Agent-Composed Experiences (Innovation)
**Goal:** Agent creates dynamic, custom UI for unique moments

**Tasks:**
1. **Create Experience Data Model**
   - `.dsf/experiences/{id}.json` structure
   - Layout definitions (grid, split, tabs, modal)
   - Component specifications

2. **Implement `ui_composer` Tool**
   - Operations: create, update, show, dismiss
   - Agent defines experience structure
   - Saved to `.dsf/experiences/`

3. **Build Web Component Library**
   - React components: Gallery, Timeline, Graph, CharacterCard, etc.
   - Interpreter: Reads experience JSON, renders components
   - Interactive: User actions sent back to agent

4. **Update Agent System Prompt**
   - Teach agent when to create experiences
   - Examples of good use cases (character reveals, choice points, world exploration)
   - Guidelines for component composition

5. **CLI Fallback Rendering**
   - Simplified text-based version of experiences
   - ASCII art for timelines/graphs
   - Choice lists for interactions

**Success Criteria:**
✅ Agent can create custom UI layouts for narrative moments
✅ Web renders dynamic experiences from JSON
✅ User interactions flow back to agent
✅ CLI gets simplified but functional version
✅ Experiences feel magical, not gimmicky

---

### Phase 5: Real-Time Synchronization (Polish)
**Goal:** All interfaces update live, collaborative feel

**Tasks:**
1. **Implement WebSocket Event System**
   - Event types: world.updated, story.segment_added, agent.thinking, etc.
   - Broadcast from DSF Server on all mutations
   - Subscribe in CLI and Web

2. **Update Interfaces for Live Updates**
   - Web: Animate new content sliding in
   - CLI: Show live updates in status line
   - Both: "Agent is thinking..." indicators

3. **Add Presence Awareness**
   - Show which interfaces are active
   - "You're also connected in: Web UI"
   - Future: Show other users (collaborative mode)

4. **Optimize for Performance**
   - Debounce rapid updates
   - Incremental rendering (don't re-render whole story)
   - Asset caching and CDN-like serving

**Success Criteria:**
✅ Changes appear instantly across interfaces
✅ Live agent activity visible to user
✅ Smooth animations, no jarring updates
✅ Feels like single, coherent experience

---

## Technical Specifications

### DSF Server API

**Base URL:** `http://localhost:3030/api/v1`

**Endpoints:**

```
# Worlds
GET    /worlds                    # List all worlds
GET    /worlds/:checkpoint        # Get world by checkpoint name
POST   /worlds                    # Create/update world
DELETE /worlds/:checkpoint        # Delete world

# Stories
GET    /stories                   # List all stories (query: ?world=...)
GET    /stories/:id               # Get story with segments
POST   /stories                   # Create story
PUT    /stories/:id/segments      # Add segment
POST   /stories/:id/branch        # Create branch
DELETE /stories/:id               # Delete story

# Assets
GET    /assets                    # List assets (query: ?story=..., ?world=...)
GET    /assets/:id                # Get asset metadata
GET    /assets/:id/data           # Download asset file
POST   /assets                    # Upload asset
DELETE /assets/:id                # Delete asset

# Sessions
GET    /sessions/:id              # Get session
POST   /sessions                  # Create session
PUT    /sessions/:id              # Update session
DELETE /sessions/:id              # Close session

# Experiences
GET    /experiences/:id           # Get experience
POST   /experiences               # Create experience
PUT    /experiences/:id           # Update experience
DELETE /experiences/:id           # Delete experience

# Agent Integration
POST   /agent/send                # Send message to agent
GET    /agent/status              # Check agent status
WS     /agent/stream              # Stream agent responses
```

**WebSocket Endpoint:** `ws://localhost:3030/ws`

**Authentication:**
- Development: No auth (localhost)
- Production: JWT tokens, same as Letta server

---

### Data Schema Updates

**Session Schema (New):**
```json
{
  "id": "session_abc123",
  "user_id": "user_xyz",
  "created": "2035-01-15T10:30:00Z",
  "last_active": "2035-01-15T14:22:13Z",
  "context": {
    "active_world": "neural_art_2035",
    "active_story": "the_neural_canvas",
    "current_segment": "seg_003",
    "reading_position": 1247,
    "active_branches": []
  },
  "preferences": {
    "interface": "web",
    "theme": "dark",
    "image_display": "inline"
  },
  "state": {
    "connected_interfaces": ["web"],
    "agent_active": false
  }
}
```

**Experience Schema (New):**
```json
{
  "id": "exp_nia_reveal",
  "type": "character_focus",
  "layout": {
    "type": "split",
    "regions": [
      { "id": "left", "width": "40%" },
      { "id": "right", "width": "60%" }
    ]
  },
  "components": [
    {
      "id": "portrait",
      "type": "image",
      "props": {
        "src": "assets/the_neural_canvas/nia_portrait.png",
        "caption": "Nia Chen, Neural Artist"
      },
      "position": { "region": "left", "order": 1 },
      "styling": { "animation": "fade" }
    },
    {
      "id": "narrative",
      "type": "narrative",
      "props": {
        "content": "Nia never wanted to be an artist...",
        "voice": "introspective"
      },
      "position": { "region": "right", "order": 1 }
    }
  ],
  "triggers": {
    "on_interact": [
      { "type": "agent_message", "message": "User chose: {{choice}}" }
    ]
  },
  "metadata": {
    "story_id": "the_neural_canvas",
    "segment_id": "seg_003",
    "created": "2035-01-15T14:22:13Z"
  }
}
```

**Enhanced Story Segment:**
```json
{
  "id": "seg_003",
  "content": "She put on the headset. The world shifted...",
  "word_count": 520,
  "parent_segment": "seg_002",
  "visuals": {
    "hero_image": {
      "asset_id": "img_1735635000001",
      "placement": "top",
      "effects": ["parallax"]
    },
    "inline_images": [
      {
        "asset_id": "img_1735635000000",
        "position": 450,
        "size": "medium",
        "caption": "The neural interface headset"
      }
    ]
  },
  "world_evolution": { /* ... */ },
  "assets": [
    {
      "id": "img_1735635000000",
      "type": "image",
      "url": "assets/the_neural_canvas/img_1735635000000.png"
    }
  ]
}
```

---

## System Prompt Updates

**Add to agent's system prompt:**

### Tool Usage: Experience Composition

You can create custom, dynamic UI experiences for special narrative moments using the `ui_composer` tool. This allows you to go beyond linear text and create immersive, interactive moments.

**When to create experiences:**
- **Character reveals:** Deep-dive into a character's backstory with portrait + timeline + narrative
- **Choice points:** Present branching story options with rich context
- **World exploration:** Let user interactively explore world elements (map, timeline, tech rules)
- **Dramatic moments:** Create special presentation for high-impact scenes

**Component types available:**
- `narrative` - Story text with styling
- `image` / `gallery` - Visual content
- `timeline` - Historical events
- `graph` - Relationships or concept maps
- `character_card` - Character bio + portrait
- `choice_buttons` - Branching decision points
- `agent_chat` - Live conversation

**Example: Create character reveal experience**
```typescript
ui_composer({
  operation: "create",
  experience: {
    type: "character_focus",
    layout: { type: "split", regions: [/* ... */] },
    components: [
      { type: "image", props: { src: "...", caption: "..." }, position: { region: "left" } },
      { type: "narrative", props: { content: "..." }, position: { region: "right" } },
      { type: "choice_buttons", props: { choices: [...] }, position: { region: "right" } }
    ]
  }
})
```

**Guidelines:**
- Use sparingly - save for moments that truly benefit from rich presentation
- In CLI, users see simplified text version
- Web UI renders full interactive experience
- User interactions come back to you as messages

---

### Tool Usage: Visual Composition

You can control how images appear in the story using the `visual_composer` tool.

**Placement options:**
- **Hero image:** Primary image at top of segment (dramatic impact)
- **Inline:** Place image at specific word position (contextual illustration)
- **Gallery:** Carousel of related images (exploration)

**Example: Place image inline**
```typescript
// First, generate image
image_generator({
  prompt: "Watercolor: Neural interface headset",
  save_as_asset: true,
  story_id: "the_neural_canvas"
})
// Returns: { asset_id: "img_123" }

// Then, place in narrative
visual_composer({
  operation: "add_inline",
  story_id: "the_neural_canvas",
  segment_id: "seg_003",
  asset_id: "img_123",
  placement: { type: "inline", position: 450, size: "medium" }
})

// Finally, save segment with visual metadata
story_manager({
  operation: "save_segment",
  story_id: "the_neural_canvas",
  segment: {
    content: "...",
    visuals: { inline_images: [{ asset_id: "img_123", position: 450, size: "medium" }] }
  }
})
```

---

### Tool Usage: Session Management

You can track the user's current context (active world, story, reading position) using `session_manager`. This enables seamless cross-interface continuity.

**Automatic tracking:**
- When user starts new world/story, update session context
- When user switches stories, update active_story
- When user makes choices, update active_branches

**Example: Update context when starting story**
```typescript
session_manager({
  operation: "update_context",
  context: {
    active_world: "neural_art_2035",
    active_story: "the_neural_canvas",
    current_segment: "seg_001"
  }
})
```

This allows user to seamlessly switch from CLI to web UI and continue exactly where they left off.

---

## Success Metrics

**Quantitative:**
- Session handoffs: ≥80% of users successfully continue in different interface
- Image integration: ≥60% of segments include visuals
- Experience creation: Agent creates ≥1 dynamic UI per story
- Real-time latency: <500ms for cross-interface updates
- CLI feature parity: ≥90% of features work in both CLI and web

**Qualitative:**
- Users describe experience as "seamless"
- Agent-composed UIs feel "natural, not gimmicky"
- Images feel "integrated into narrative"
- Cross-interface switching feels "effortless"

---

## Future Possibilities

### Multi-User Collaboration
- Multiple users exploring same world
- See each other's reading positions
- Agent responds to group conversations
- Shared story branches

### Mobile App
- Native iOS/Android apps
- Same API, optimized UI
- Push notifications for agent updates
- Read on-the-go, edit on desktop

### VR/AR Experiences
- Agent creates 3D spatial experiences
- World exploration in VR
- Character encounters in AR
- New component types: `spatial_scene`, `3d_model`

### AI-Generated Music/Sound
- Agent composes ambient music for scenes
- Sound effects for dramatic moments
- Voice narration (TTS)
- Audio player component in experiences

### Community Platform
- Share worlds and stories
- Remix others' worlds
- Collaborative worldbuilding
- Discovery and curation

---

## Conclusion

This architecture transforms Deep Sci-Fi from a CLI-only storytelling tool into a **seamless, multi-interface narrative platform** where the agent doesn't just write stories—it **composes experiences**.

**Core innovations:**
1. **Session management** - Effortless cross-interface continuity
2. **Agent-composed UIs** - Dynamic, just-in-time experiences
3. **Rich visual integration** - Images as first-class narrative elements
4. **Real-time sync** - All interfaces stay live-updated

**Implementation approach:**
- Incremental rollout (5 phases)
- Backwards compatible at each step
- CLI remains fully functional standalone
- Web adds progressive enhancements

**The result:**
Users can fluidly explore worlds and stories across CLI and web, with the agent dynamically creating rich, interactive moments—transforming storytelling from linear text to **immersive, adaptive experiences**.
