# Agent-Driven Generative UI Research

**Created:** 2026-01-15
**Status:** COMPLETE
**Type:** Research & Analysis

---

## Executive Summary

The agent-driven generative UI space has rapidly matured in late 2025-early 2026, with **clear standards and patterns** emerging from major players (Vercel, Google, Anthropic). Deep Sci-Fi's custom agent-to-Canvas communication via WebSocket is a valid pattern, but we can significantly simplify and enhance it by leveraging existing standards.

**Key Finding:** We're not reinventing the wheel, but we're building a custom wheel when standard APIs exist. We should adopt industry standards while keeping our immersive 3D approach as our unique differentiator.

---

## The 2026 Landscape: Six Key Approaches

### 1. **Vercel json-render** (Declarative JSON with Guardrails) ⭐ **NEW**

**What it is:** "AI → JSON → UI" - Vercel's framework for safely constrained component generation.

**Key Features:**
- [json-render.dev](https://json-render.dev/) - Official documentation
- [GitHub: vercel-labs/json-render](https://github.com/vercel-labs/json-render)
- **Guardrailed**: AI can only use components in your catalog
- **Predictable**: JSON output matches your schema, every time
- **Fast**: Stream and render progressively as the model responds
- Uses Zod schemas for component props validation
- Works WITH Vercel AI SDK (not instead of)
- Framework-agnostic JSON format

**Pattern:**
```typescript
import { createCatalog } from '@json-render/core';
import { z } from 'zod';

// Define component catalog with Zod schemas
export const catalog = createCatalog({
  components: {
    WorldOrb: {
      props: z.object({
        worldId: z.string(),
        position: z.array(z.number()).length(3),
        scale: z.number().optional()
      }),
      hasChildren: false,
    },
    StoryCard: {
      props: z.object({
        title: z.string(),
        storyId: z.string(),
      }),
      hasChildren: true,
    },
  },
  actions: {
    navigateToWorld: {
      params: z.object({ worldId: z.string() })
    },
  },
});

// AI generates JSON constrained to catalog
{
  "type": "WorldOrb",
  "props": { "worldId": "abc123", "scale": 1.5 },
  "key": "orb-1"
}

// Render with React
import { Renderer } from '@json-render/react';
<Renderer catalog={catalog} tree={aiGeneratedJson} />
```

**Pros:**
- **Security first** - Component catalog prevents arbitrary code execution
- **Type safety** - Zod schemas validate all props
- **Cross-framework** - JSON can render in any framework
- **Streaming** - Progressive rendering as AI responds
- **Validation** - Built-in validation functions
- **Data binding** - Actions and data providers

**Cons:**
- More setup than pure AI SDK RSC
- Requires maintaining component catalog
- Newer project (less mature than AI SDK)

**Why This Matters for Deep Sci-Fi:**
This is **exactly the pattern** recommended in our research (Declarative Generative UI). It's like A2UI but from Vercel, with:
- Zod schemas (type safety)
- Component catalog (security)
- Framework-agnostic JSON
- Streaming support

**Sources:**
- [json-render.dev](https://json-render.dev/)
- [GitHub - vercel-labs/json-render](https://github.com/vercel-labs/json-render)

---

### 2. **Vercel AI SDK + Generative UI** (Web-Centric)

**What it is:** React-first framework where agents stream React components directly to the UI.

**Key Features:**
- [AI SDK 6](https://vercel.com/blog/ai-sdk-6) with agents, tool execution approval, DevTools, full MCP support
- [Generative UI](https://ai-sdk.dev/docs/ai-sdk-ui/generative-user-interfaces): Connect tool call results to React components
- React Server Components (RSC) for streaming
- Type-safe end-to-end (tool definitions type UI components)
- 20M+ monthly downloads

**Pattern:**
```tsx
// Agent defines tools with UI components
const tools = {
  showWorldMap: tool({
    description: 'Show an interactive world map',
    parameters: z.object({ worldId: z.string() }),
    generate: async ({ worldId }) => {
      return <InteractiveWorldMap worldId={worldId} />;
    }
  })
};

// UI automatically renders streamed components
const { messages } = useChat({ tools });
```

**Pros:**
- Zero-config React integration
- Streaming out-of-the-box
- Type safety
- Battle-tested (Vercel's v0 uses this)

**Cons:**
- Web-only (React-specific)
- Opinionated (Next.js focused)

**Sources:**
- [AI SDK by Vercel](https://ai-sdk.dev/docs/introduction)
- [Introducing AI SDK 3.0 with Generative UI support](https://vercel.com/blog/ai-sdk-3-generative-ui)
- [Generative UI Chatbot with React Server Components](https://vercel.com/templates/next.js/rsc-genui)

---

### 3. **Google A2UI** (Cross-Platform Standard)

**What it is:** Declarative JSON protocol for agent-generated UIs that render natively across platforms.

**Key Features:**
- [Open standard](https://developers.googleblog.com/introducing-a2ui-an-open-project-for-agent-driven-interfaces/) (v0.8 Public Preview, Dec 2025)
- [Declarative JSON format](https://github.com/google/A2UI) (not executable code)
- Client maintains "catalog" of trusted components
- Native rendering: Flutter, Angular, Lit, React, SwiftUI
- Part of Google's agent ecosystem: A2A (agent-to-agent), A2UI (agent-to-UI), ADK (Agent Development Kit)

**Pattern:**
```json
{
  "type": "container",
  "layout": "column",
  "children": [
    {
      "type": "text",
      "content": "Your world: {{worldName}}"
    },
    {
      "type": "button",
      "label": "Explore",
      "action": "navigate_to_world"
    }
  ]
}
```

**Pros:**
- Cross-platform (same JSON → web/mobile/desktop)
- Security (pre-approved component catalog)
- Framework-agnostic

**Cons:**
- More boilerplate (need client-side catalog)
- Less dynamic than React components
- Still evolving (v0.8)

**Sources:**
- [Introducing A2UI: An open project for agent-driven interfaces](https://developers.googleblog.com/introducing-a2ui-an-open-project-for-agent-driven-interfaces/)
- [Agent UI Standards Multiply: MCP Apps and Google's A2UI](https://thenewstack.io/agent-ui-standards-multiply-mcp-apps-and-googles-a2ui/)
- [The Complete Guide to A2UI Protocol](https://dev.to/czmilo/the-complete-guide-to-a2ui-protocol-building-agent-driven-uis-with-googles-a2ui-in-2026-146p)
- [Google's open standard lets AI agents build user interfaces on the fly](https://the-decoder.com/googles-open-standard-lets-ai-agents-build-user-interfaces-on-the-fly/)

---

### 4. **AG-UI Protocol + CopilotKit** (Event-Based Runtime)

**What it is:** Lightweight event protocol for agent-UI communication with React runtime.

**Key Features:**
- [AG-UI](https://www.copilotkit.ai/ag-ui): Event-based protocol (open standard)
- [CopilotKit](https://github.com/CopilotKit/CopilotKit): React components for AG-UI rendering
- Works with any agent framework: LangGraph, Mastra, Pydantic AI
- Supports [A2UI spec](https://www.copilotkit.ai/blog/build-with-googles-new-a2ui-spec-agent-user-interfaces-with-a2ui-ag-ui) (can render Google's A2UI JSON)
- 50K+ monthly downloads (YC W25)
- Shared state between frontend and backend

**Pattern:**
```tsx
// Agent sends events
{
  type: "generative_ui",
  component: "WorldMap",
  props: { worldId: "abc123" }
}

// CopilotKit runtime renders
<CopilotKit>
  <CopilotChat />
</CopilotKit>
```

**Pros:**
- Framework flexibility (works with any agent backend)
- A2UI compatibility
- Event-driven (clean separation)
- YC-backed, active development

**Cons:**
- Requires CopilotKit runtime
- Less mature than Vercel AI SDK

**Sources:**
- [CopilotKit GitHub](https://github.com/CopilotKit/CopilotKit)
- [AG-UI Protocol](https://www.copilotkit.ai/ag-ui)
- [Build with Google's new A2UI Spec](https://www.copilotkit.ai/blog/build-with-googles-new-a2ui-spec-agent-user-interfaces-with-a2ui-ag-ui)
- [AG-UI Overview: A Lightweight Protocol for Agent-User Interaction](https://www.datacamp.com/tutorial/ag-ui)

---

### 5. **assistant-ui** (Radix-Style Primitives)

**What it is:** Composable React primitives for AI chat (like Radix for AI).

**Key Features:**
- [Radix-style approach](https://github.com/assistant-ui/assistant-ui) (composable primitives, not monolithic components)
- [6,900+ GitHub stars](https://www.saastr.com/ai-app-of-the-week-assistant-ui-the-react-library-thats-eating-the-ai-chat-interface-market/), 50K+ monthly downloads
- First-class integrations: Vercel AI SDK, LangGraph, Mastra
- [Generative UI support](https://www.assistant-ui.com/docs/guides/ToolUI) (maps tool calls to custom UI)
- Human-in-the-loop approval workflows
- Stateful conversations

**Pattern:**
```tsx
import { AssistantRuntimeProvider } from "@assistant-ui/react";

<AssistantRuntimeProvider runtime={myRuntime}>
  <Thread />
</AssistantRuntimeProvider>
```

**Pros:**
- Highly composable
- Framework-agnostic runtime
- Active development (YC W25)
- Clean API

**Cons:**
- Requires custom runtime integration
- Less opinionated (more setup needed)

**Sources:**
- [assistant-ui GitHub](https://github.com/assistant-ui/assistant-ui)
- [AI App of the Week: Assistant UI](https://www.saastr.com/ai-app-of-the-week-assistant-ui-the-react-library-thats-eating-the-ai-chat-interface-market/)
- [Generative UI | assistant-ui](https://www.assistant-ui.com/docs/guides/ToolUI)

---

### 6. **Model Context Protocol (MCP) + MCP Apps**

**What it is:** Anthropic's protocol for agent-to-tool communication, now with UI generation.

**Key Features:**
- [MCP](https://modelcontextprotocol.io/) donated to Linux Foundation's Agentic AI Foundation (Dec 2025)
- [MCP Apps](https://dev.to/blackgirlbytes/my-predictions-for-mcp-and-ai-assisted-coding-in-2026-16bm): Embedded web UIs, buttons, toggles (successor to MCP-UI)
- Agents render interactive interfaces in host environment
- Vercel AI SDK has [full MCP support](https://vercel.com/blog/ai-sdk-6)
- Called "the iPhone moment for agent UX"

**Pattern:**
```typescript
// MCP tool returns UI specification
{
  type: "ui",
  content: {
    component: "form",
    fields: [...]
  }
}
```

**Pros:**
- Industry standard (backed by Anthropic, OpenAI, Block)
- Works across all MCP clients (Claude Desktop, Cursor, etc.)
- Rich UI support

**Cons:**
- Still evolving
- UI format not fully standardized yet

**Sources:**
- [What is the Model Context Protocol (MCP)?](https://modelcontextprotocol.io/)
- [Building effective AI agents with MCP](https://developers.redhat.com/articles/2026/01/08/building-effective-ai-agents-mcp)
- [My Predictions for MCP and AI-Assisted Coding in 2026](https://dev.to/blackgirlbytes/my-predictions-for-mcp-and-ai-assisted-coding-in-2026-16bm)
- [Introducing the Model Context Protocol](https://www.anthropic.com/news/model-context-protocol)

---

## Three Generative UI Patterns

According to [2026 research](https://medium.com/@akshaychame2/the-complete-guide-to-generative-ui-frameworks-in-2026-fde71c4fa8cc), there are three main approaches:

### 1. Static Generative UI
**Pattern:** Engineers hand-craft components; agents only choose which to use.

**Example:**
```tsx
// Pre-defined components
const COMPONENTS = {
  worldMap: WorldMapComponent,
  characterCard: CharacterCardComponent,
  storyReader: StoryReaderComponent
};

// Agent selects
agent.emit({ component: 'worldMap', props: {...} });
```

**Pros:** Type-safe, predictable, secure
**Cons:** Limited flexibility

### 2. Declarative Generative UI (A2UI approach)
**Pattern:** Agents return structured JSON; client renders from catalog.

**Example:**
```json
{
  "type": "card",
  "title": "World: Proxima Colony",
  "actions": [
    { "type": "button", "label": "Explore", "action": "navigate" }
  ]
}
```

**Pros:** Flexible, secure, cross-platform
**Cons:** Requires catalog maintenance

### 3. Open-Ended Generative UI
**Pattern:** Agents generate complete UI (HTML/iframes).

**Example:**
```tsx
agent.emit({ html: '<div>...</div>' });
```

**Pros:** Maximum flexibility
**Cons:** Security risks, inconsistent UX

**Recommendation:** **Declarative (A2UI-style)** is the sweet spot for Deep Sci-Fi.

---

## Deep Sci-Fi's Current Approach: Analysis

### What We Have
**Architecture:** Custom WebSocket-based Agent Bus
- Letta-Code CLI ↔ Agent Bus (WebSocket) ↔ Canvas UI
- Message types: `CanvasUIMessage`, `InteractionMessage`, `StateChangeMessage`, `SuggestionMessage`
- Dynamic component rendering at mount points

**Code:**
```typescript
// letta-code/src/agent-bus/types.ts
export type CanvasUIMessage = {
  type: 'canvas_ui';
  component: string;
  props: Record<string, unknown>;
  mountPoint: 'overlay' | 'fullscreen' | 'inline';
};
```

### Strengths ✅
1. **Bidirectional real-time communication** (WebSocket)
2. **Multiple mount points** (overlay, fullscreen, inline)
3. **Interaction feedback** (Canvas → Agent)
4. **State synchronization**
5. **Suggestion system**

### Gaps 🔴
1. **Custom protocol** (not industry standard)
2. **No streaming support** (messages are atomic)
3. **No type safety** (props are `Record<string, unknown>`)
4. **No component catalog** (security risk)
5. **Manual serialization** (no standard format)
6. **No cross-platform support** (Canvas UI only)

### Are We Reinventing the Wheel?

**Yes, partially.** We've built a custom Agent Bus that solves similar problems to AG-UI, but without:
- Industry-standard protocol
- Type safety
- Streaming
- Cross-platform support
- Security guarantees (component catalog)

**However:** Our **3D Observatory approach is unique** and not covered by any standard. The immersive spatial UI is our differentiator.

---

## Recommendations: Leverage Standards, Keep Innovation

### Option 1: Adopt json-render (Top Recommendation) ⭐

**What:** Use Vercel's json-render with custom Agent Bus (keeping WebSocket transport)

**Why:**
- **Perfect fit for our pattern** - Declarative JSON with component catalog (exactly what we need)
- **Security first** - Component catalog prevents arbitrary code execution
- **Type safety** - Zod schemas validate all props (catch errors at definition time)
- **Framework-agnostic** - JSON format works anywhere (future mobile/desktop ready)
- **Streaming support** - Progressive rendering as AI responds
- **Works WITH Vercel AI SDK** - Not mutually exclusive, can use both
- **Minimal migration** - Keep Agent Bus architecture, just change message format

**Migration:**
```typescript
// 1. Install json-render
// npm install @json-render/core @json-render/react

// 2. Define component catalog (apps/web/lib/agent-ui/catalog.ts)
import { createCatalog } from '@json-render/core';
import { z } from 'zod';

export const catalog = createCatalog({
  components: {
    WorldOrb: {
      component: WorldOrb,
      props: z.object({
        worldId: z.string(),
        position: z.array(z.number()).length(3),
        scale: z.number().optional()
      }),
    },
    ImmersiveStoryReader: {
      component: ImmersiveStoryReader,
      props: z.object({
        storyId: z.string(),
        mode: z.enum(['scroll', 'vn', 'hybrid'])
      }),
    }
    // ... rest of our 3D components
  },
  actions: {
    navigateToWorld: {
      params: z.object({ worldId: z.string() })
    },
    startStory: {
      params: z.object({ storyId: z.string() })
    }
  }
});

// 3. Update Agent Bus messages (letta-code/src/tools/canvas_ui.ts)
// Before (custom)
agentBus.emit({
  type: 'canvas_ui',
  component: 'WorldOrb',
  props: { worldId: 'abc' }
});

// After (json-render)
agentBus.emit({
  type: 'canvas_ui',
  tree: {
    type: 'WorldOrb',
    props: { worldId: 'abc', position: [0, 0, 0], scale: 1.5 },
    key: 'world-abc'
  }
});

// 4. Render with json-render (apps/web/components/canvas/DynamicRenderer.tsx)
import { Renderer } from '@json-render/react';

<Renderer
  catalog={catalog}
  tree={message.tree}
  onAction={(action, params) => {
    // Send interaction back to agent
    agentBus.send({ type: 'interaction', action, params });
  }}
/>
```

**Keep Custom:**
- Agent Bus WebSocket transport (works great!)
- 3D Observatory (unique spatial UI)
- World exploration UX
- Immersive story reading
- Cinematic transitions

**Use json-render For:**
- Component catalog with Zod schemas (type safety + security)
- JSON tree format (standardized structure)
- Streaming renderer
- Action handling
- Validation

**Result:** Best of both worlds - our innovative spatial UX with industry-standard protocol.

---

### Option 2: Adopt AG-UI Protocol

**What:** Replace custom Agent Bus with AG-UI + CopilotKit runtime

**Why:**
- Industry standard (works with all agent frameworks)
- Streaming support
- A2UI compatibility (cross-platform ready)
- Active development + community
- Maintains our unique immersive UX

**Migration:**
```typescript
// Before (custom)
agentBus.emit({
  type: 'canvas_ui',
  component: 'WorldOrb',
  props: { worldId: 'abc' }
});

// After (AG-UI)
copilot.emitGenerativeUI({
  component: 'WorldOrb',
  props: { worldId: 'abc' }
});
```

**Keep Custom:**
- 3D Observatory (unique spatial UI)
- World exploration UX
- Immersive story reading
- Cinematic transitions

**Use Standard:**
- Agent-to-UI protocol (AG-UI)
- Component rendering (CopilotKit or assistant-ui)
- Streaming (React Server Components)
- Type safety (Zod schemas)

### Option 3: Hybrid (Custom Bus + A2UI JSON)

**What:** Keep Agent Bus but use A2UI JSON format for messages

**Why:**
- Minimal changes to existing code
- Cross-platform ready (A2UI JSON can render on mobile/desktop later)
- Security (component catalog)
- Standard format (easier for other developers)

**Migration:**
```typescript
// Agent Bus sends A2UI JSON
agentBus.emit({
  type: 'canvas_ui',
  payload: {
    type: 'container',
    children: [
      { type: 'world_orb', props: { worldId: 'abc' } }
    ]
  }
});

// Canvas UI uses A2UI renderer
<A2UIRenderer spec={message.payload} catalog={COMPONENT_CATALOG} />
```

### Option 4: Vercel AI SDK (Web-Only)

**What:** Use Vercel AI SDK + Generative UI for agent-driven components

**Why:**
- Zero-config React integration
- Streaming out-of-the-box
- Type-safe
- Battle-tested

**Cons:**
- Web-only (no mobile/desktop)
- Requires Next.js migration (we're already on Next.js ✅)
- Less control over transport layer

---

## Spatial UI + Agent-Driven Interfaces: 2026 Trends

### Key Insights from Research

From [Top UI/UX Design Trends for 2026](https://dev.to/pixel_mosaic/top-uiux-design-trends-for-2026-ai-first-context-aware-interfaces-spatial-experiences-166j) and [State of Design 2026](https://tejjj.medium.com/state-of-design-2026-when-interfaces-become-agents-fc967be10cba):

1. **Agentic AI is mainstream** - Interfaces anticipate needs, suggest actions, take initiative
2. **Spatial computing market: $280.5B by 2028** (23.4% CAGR)
3. **Multimodal interactions** - Voice, gesture, gaze, touch combined fluidly
4. **Trust is key UX currency** - Explainability moved from compliance to core design
5. **Agency requires control** - Users grant autonomy only to transparent systems

### Deep Sci-Fi's Unique Position

**Our Opportunity:** Combine industry-standard agent protocols with cutting-edge spatial UX.

| Layer | Use Standard | Be Unique |
|-------|-------------|-----------|
| **Agent Protocol** | AG-UI or A2UI | ❌ |
| **Component Rendering** | CopilotKit / assistant-ui | ❌ |
| **Spatial Experience** | ❌ | ✅ 3D Observatory |
| **World Exploration** | ❌ | ✅ Interactive maps |
| **Story Reading** | ❌ | ✅ Cinematic immersion |
| **Agent Presence** | ❌ | ✅ 3D glyph in space |

**Strategy:** Be standards-compliant where it matters (protocol, security, type safety), be innovative where it counts (spatial UX, immersion, storytelling).

---

## Implementation Recommendations

### Phase 1: Adopt Standard Protocol (2 weeks)

**Goal:** Replace custom Agent Bus with AG-UI or A2UI

**Tasks:**
1. **Install CopilotKit** or build A2UI renderer
2. **Define component catalog** (security + type safety)
3. **Migrate message types** to AG-UI events or A2UI JSON
4. **Update agent tools** to emit standard format
5. **Add streaming support** (React Server Components)

**Files to Change:**
```
letta-code/src/agent-bus/
├── types.ts              → Use AG-UI event types
├── server.ts             → Replace WebSocket with standard runtime
└── client.ts             → Use CopilotKit or A2UI renderer

letta-code/src/tools/
└── canvas_ui.ts          → Emit AG-UI or A2UI format
```

### Phase 2: Build Component Catalog (1 week)

**Goal:** Define trusted UI components with type-safe props

**Example:**
```typescript
// apps/web/lib/agent-ui/catalog.ts
import { z } from 'zod';

export const COMPONENT_CATALOG = {
  WorldOrb: {
    component: WorldOrb,
    schema: z.object({
      worldId: z.string(),
      position: z.array(z.number()).length(3),
      scale: z.number().optional()
    })
  },
  StoryReader: {
    component: ImmersiveStoryReader,
    schema: z.object({
      storyId: z.string(),
      segmentId: z.string().optional(),
      mode: z.enum(['scroll', 'vn', 'hybrid'])
    })
  }
  // ... rest of components
};
```

### Phase 3: Add Streaming (1 week)

**Goal:** Stream components as agent thinks (progressive rendering)

**Pattern:**
```tsx
// Agent streams thoughts + UI
for await (const chunk of agentStream) {
  if (chunk.type === 'thought') {
    streamText(chunk.content);
  }
  if (chunk.type === 'ui') {
    streamComponent(chunk.component, chunk.props);
  }
}
```

### Phase 4: Keep Innovation (Ongoing)

**Focus on:**
- 3D spatial experiences (Observatory, World Space)
- Cinematic story reading
- Agent presence in 3D
- Immersive transitions
- Multi-sensory atmosphere (audio, particles, shaders)

---

## Framework Recommendation Matrix

| Use Case | Recommended Framework | Why |
|----------|----------------------|-----|
| **Web-only, React** | Vercel AI SDK | Zero-config, streaming, type-safe |
| **Declarative + Safety** | **json-render** | Component catalog, Zod schemas, streaming |
| **Cross-platform future** | A2UI + custom renderer | Framework-agnostic, mobile-ready |
| **Agent flexibility** | AG-UI + CopilotKit | Works with any agent backend |
| **Maximum control** | assistant-ui | Composable primitives, no opinions |
| **Deep Sci-Fi (Now)** | **json-render + Agent Bus** ⭐ | Security + type safety + our spatial UX |
| **Deep Sci-Fi (Alt)** | AG-UI + CopilotKit | Event-based, framework flexibility |
| **Deep Sci-Fi (Future)** | A2UI hybrid | Cross-platform ready |

---

## Conclusion: The Path Forward

### What We Should Do

1. **Adopt json-render** (Vercel's declarative JSON framework) for component catalog + schemas
2. **Keep Agent Bus architecture** (WebSocket is fine, just use json-render tree format)
3. **Build component catalog** with Zod schemas (type safety + security)
4. **Add streaming support** for progressive rendering (json-render supports this)
5. **Focus innovation on spatial UX** (3D Observatory, immersive world exploration)

### What We Should NOT Do

1. ❌ Keep custom protocol without type safety
2. ❌ Try to standardize our 3D spatial UX (that's our differentiator)
3. ❌ Rebuild everything from scratch (incremental migration)
4. ❌ Ignore security (component catalog is essential)

### The Big Picture

**Industry is converging on:**
- Declarative UI specs (A2UI-style JSON)
- Event-based protocols (AG-UI)
- Component catalogs (security)
- Streaming (progressive rendering)
- Type safety (Zod schemas)

**Deep Sci-Fi should excel at:**
- Spatial 3D experiences
- Immersive storytelling
- Cinematic transitions
- Multi-sensory atmosphere
- Agent as creative collaborator

**Be boring where it helps, be innovative where it matters.**

---

## Sources

### Standards & Protocols
- [AI SDK by Vercel](https://ai-sdk.dev/docs/introduction)
- [AI SDK 6 - Vercel](https://vercel.com/blog/ai-sdk-6)
- [AI SDK UI: Generative User Interfaces](https://ai-sdk.dev/docs/ai-sdk-ui/generative-user-interfaces)
- [Introducing A2UI: An open project for agent-driven interfaces](https://developers.googleblog.com/introducing-a2ui-an-open-project-for-agent-driven-interfaces/)
- [GitHub - google/A2UI](https://github.com/google/A2UI)
- [The A2UI Protocol: A 2026 Complete Guide](https://dev.to/czmilo/the-a2ui-protocol-a-2026-complete-guide-to-agent-driven-interfaces-2l3c)
- [CopilotKit GitHub](https://github.com/CopilotKit/CopilotKit)
- [AG-UI Protocol | CopilotKit](https://www.copilotkit.ai/ag-ui)
- [assistant-ui GitHub](https://github.com/assistant-ui/assistant-ui)
- [What is the Model Context Protocol (MCP)?](https://modelcontextprotocol.io/)

### Patterns & Best Practices
- [The Complete Guide to Generative UI Frameworks in 2026](https://medium.com/@akshaychame2/the-complete-guide-to-generative-ui-frameworks-in-2026-fde71c4fa8cc)
- [Generative UI: Understanding Agent-Powered Interfaces](https://www.copilotkit.ai/generative-ui)
- [AI SDK Architecture: Streaming & Tool Calling Patterns](https://learnwebcraft.com/learn/ai/vercel-ai-sdk-advanced-guide)
- [React Stack Patterns](https://www.patterns.dev/react/react-2026/)
- [AI UI Patterns](https://www.patterns.dev/react/ai-ui-patterns/)

### Trends & Analysis
- [Top UI/UX Design Trends for 2026: AI-First, Context-Aware Interfaces & Spatial Experiences](https://dev.to/pixel_mosaic/top-uiux-design-trends-for-2026-ai-first-context-aware-interfaces-spatial-experiences-166j)
- [State of Design 2026: When Interfaces Become Agents](https://tejjj.medium.com/state-of-design-2026-when-interfaces-become-agents-fc967be10cba)
- [Generative UI: The AI agent is the front end | InfoWorld](https://www.infoworld.com/article/4110010/generative-ui-the-ai-agent-is-the-front-end.html)
- [Agent UI Standards Multiply: MCP Apps and Google's A2UI](https://thenewstack.io/agent-ui-standards-multiply-mcp-apps-and-googles-a2ui/)
- [UI UX Trends 2026: 7 Game-Changing Shifts](https://ultimez.com/blog/designing/ui-ux-trends-2026-7-game-changing-shifts-with-expert-insights/)
- [Mobile UI Trends 2026: Glassmorphism to Spatial Computing](https://www.sanjaydey.com/mobile-ui-trends-2026-glassmorphism-spatial-computing/)
