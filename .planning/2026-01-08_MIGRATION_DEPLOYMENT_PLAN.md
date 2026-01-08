# Deep Sci-Fi: Complete Migration & Deployment Plan

**Created:** 2026-01-08
**Status:** Approved, In Progress

## Architecture Clarification

### Where Things Run

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              BROWSER                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐          │
│  │   Chat Panel    │  │   Canvas UI     │  │  Worlds/Stories │          │
│  │                 │  │  (Dynamic UX)   │  │     Pages       │          │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘          │
│           │                    │                    │                    │
│           └────────────────────┼────────────────────┘                    │
│                                │                                         │
│                          WebSocket + HTTP                                │
└────────────────────────────────┼─────────────────────────────────────────┘
                                 │
┌────────────────────────────────┼─────────────────────────────────────────┐
│                         NEXT.JS SERVER (port 3000)                       │
│                                                                          │
│  ┌──────────────┐  ┌───────────────────────────────────────────────┐    │
│  │   NextAuth   │  │           LettaOrchestrator                    │    │
│  │   (Auth)     │  │  ┌─────────────────────────────────────────┐  │    │
│  └──────────────┘  │  │         TOOL EXECUTOR                    │  │    │
│                    │  │  - world_manager (→ PostgreSQL)          │  │    │
│  ┌──────────────┐  │  │  - story_manager (→ PostgreSQL)          │  │    │
│  │   Prisma     │  │  │  - asset_manager (→ S3)                  │  │    │
│  │  (DB Client) │  │  │  - image_generator (→ Google/OpenAI)     │  │    │
│  └──────────────┘  │  │  - canvas_ui (→ WebSocket to Browser)    │  │    │
│                    │  │  - get_canvas_interactions (← Browser)   │  │    │
│                    │  └─────────────────────────────────────────┘  │    │
│                    └────────────────────┬──────────────────────────┘    │
└─────────────────────────────────────────┼────────────────────────────────┘
                                          │
                                     HTTP API
                                          │
┌─────────────────────────────────────────┼────────────────────────────────┐
│                         LETTA SERVER (port 8283)                         │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                         AGENTS                                   │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │    │
│  │  │ User Agent  │  │ World Agent │  │ Experience  │              │    │
│  │  │ (1 per user)│  │(1 per world)│  │   Agent     │              │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────────┐  │
│  │   LLM API   │  │   Memory    │  │  Server-Side Evaluation Tools   │  │
│  │  (Claude)   │  │   Blocks    │  │  - assess_output_quality        │  │
│  └─────────────┘  └─────────────┘  │  - check_logical_consistency    │  │
│                                    │  - compare_versions             │  │
│  ┌─────────────────────────────┐   │  - analyze_information_gain     │  │
│  │  Trajectory Capture         │   └─────────────────────────────────┘  │
│  │  (agent execution history)  │                                        │
│  └─────────────────────────────┘                                        │
└──────────────────────────────────────────────────────────────────────────┘
                                          │
                                     PostgreSQL
                                          │
┌─────────────────────────────────────────┼────────────────────────────────┐
│                              DATABASES                                   │
│                                                                          │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐       │
│  │     PostgreSQL + pgvector   │  │           S3                 │       │
│  │  - Users, Worlds, Stories   │  │  - Images                    │       │
│  │  - Agent memory cache       │  │  - Generated assets          │       │
│  │  - Trajectory embeddings    │  │  - Uploaded files            │       │
│  └─────────────────────────────┘  └─────────────────────────────┘       │
└──────────────────────────────────────────────────────────────────────────┘
```

### Key Insight: Client-Side vs Server-Side Tools

**Letta supports two modes:** (Verified from [official Letta docs](https://docs.letta.com/guides/agents/tool-execution-client-side/))

1. **Server-Side Tools** (run on Letta server)
   - Evaluation tools (assess_output_quality, etc.)
   - These are built into Letta
   - Agent calls them, Letta executes them

2. **Client-Side Tools** (run on YOUR server - Next.js) - **THIS IS THE OFFICIAL PATTERN**
   - DSF tools (world_manager, image_generator, canvas_ui, etc.)
   - Agent says "I want to call tool X with args Y"
   - YOUR code executes the tool
   - You send the result back to Letta
   - Agent continues

From [Letta Documentation](https://docs.letta.com/guides/agents/tool-execution-client-side/):
> "Client-side execution is useful when tools need access to local resources, user context, or private APIs that shouldn't be exposed to the server."

**The execution flow:**
1. Mark tools with `defaultRequiresApproval: true`
2. Agent attempts tool call → server sends approval request
3. Your app executes the tool with provided arguments
4. Send results back as approval response with `type: "tool"`
5. Agent receives result and continues

**This is exactly how `packages/letta/orchestrator.ts` works** - it's the correct pattern.

**This is why Next.js is the "hub"** - it executes all our custom tools.

### Message Flow Example

```
1. User types "Generate an image of the protagonist"
   Browser → Next.js → Letta

2. Agent (World Agent) decides to delegate to Experience Agent
   Letta → Next.js: "Call delegate_to_experience_agent"
   Next.js executes: sends message to Experience Agent

3. Experience Agent decides to generate image
   Letta → Next.js: "Call image_generator with prompt=..."
   Next.js executes: calls Google Gemini API
   Next.js → Letta: "Here's the base64 image"

4. Experience Agent wants to show image in Canvas
   Letta → Next.js: "Call canvas_ui with component spec"
   Next.js executes:
     - Saves asset to S3
     - Pushes WebSocket message to browser
   Browser: Renders image component

5. Agent done
   Letta → Next.js: "end_turn" with final message
   Next.js → Browser: "Here's what I created..."
```

---

## Work Breakdown

### Stream 1: Core Tools & Agent Wiring (BLOCKING)
*Must complete before other streams*

#### 1.1 Wire Chat API to Agents (Day 1)
- [ ] Update `/api/chat/route.ts` to call `getLettaOrchestrator()`
- [ ] Implement proper streaming response
- [ ] Add WebSocket support for real-time UI updates
- [ ] Test User Agent → World Agent routing
- **Files**: `apps/web/app/api/chat/route.ts`, `packages/letta/orchestrator.ts`

#### 1.2 Port Missing Tools (Days 2-3)
**image_generator**
- [ ] Port from `letta-code/src/tools/impl/image_generator.ts`
- [ ] Add S3 upload for generated images
- [ ] Support Google Gemini + OpenAI providers
- **File**: `packages/letta/tools/image-generator.ts`

**asset_manager**
- [ ] Port from `letta-code/src/tools/impl/asset_manager.ts`
- [ ] Replace filesystem with S3 + CloudFront
- [ ] Add database records for asset metadata
- **File**: `packages/letta/tools/asset-manager.ts`

**canvas_ui**
- [ ] Port from `letta-code/src/tools/impl/canvas_ui.ts`
- [ ] Instead of WebSocket to Agent Bus, push via Next.js WebSocket
- [ ] Create interaction queue in memory (or Redis for production)
- **File**: `packages/letta/tools/canvas-ui.ts`

**get_canvas_interactions**
- [ ] Port from `letta-code/src/tools/impl/get_canvas_interactions.ts`
- [ ] Read from interaction queue
- **File**: `packages/letta/tools/get-canvas-interactions.ts`

**send_suggestion**
- [ ] Port from `letta-code/src/tools/impl/send_suggestion.ts`
- [ ] Push suggestions via WebSocket
- **File**: `packages/letta/tools/send-suggestion.ts`

---

### Stream 2: Experience Agent Setup (PARALLEL after 1.1)

#### 2.1 Create Experience Agent (Day 2)
- [ ] Define Experience Agent system prompt
- [ ] Define memory blocks (persona, capabilities)
- [ ] Add to orchestrator: `getOrCreateExperienceAgent()`
- [ ] Register tools: image_generator, asset_manager, canvas_ui, send_suggestion
- **Files**: `packages/letta/agents/experience-agent.ts`, `packages/letta/prompts/experience-agent.ts`

#### 2.2 World Agent → Experience Agent Delegation (Day 3)
- [ ] Create `delegate_to_experience` tool for World Agent
- [ ] Implement delegation flow in orchestrator
- [ ] Handle response passing back to World Agent
- **Files**: `packages/letta/tools/delegate-to-experience.ts`, `packages/letta/orchestrator.ts`

---

### Stream 3: Canvas UI Integration (PARALLEL after 1.2)

#### 3.1 WebSocket Setup (Day 2)
- [ ] Add WebSocket server to Next.js
- [ ] Create connection manager for active clients
- [ ] Implement message types: canvas_update, interaction, suggestion
- **Files**: `apps/web/app/api/ws/route.ts`, `apps/web/lib/websocket.ts`

#### 3.2 Port DynamicRenderer (Day 3)
- [ ] Port from `letta-code/src/canvas/components/DynamicRenderer.tsx`
- [ ] Port all component types (17+ components)
- [ ] Integrate with WebSocket for real-time updates
- **Files**: `apps/web/components/canvas/DynamicRenderer.tsx`, `apps/web/components/canvas/primitives/*`

#### 3.3 Interaction Capture (Day 3)
- [ ] Capture user interactions (clicks, inputs)
- [ ] Send via WebSocket to server
- [ ] Queue for agent consumption
- **Files**: `apps/web/components/canvas/InteractionCapture.tsx`

---

### Stream 4: Observability Setup (PARALLEL)

#### 4.1 Enable Trajectory Capture (Day 2)
- [ ] Set `ENABLE_TRAJECTORY_CAPTURE=true` in Letta config
- [ ] Verify pgvector extension in PostgreSQL
- [ ] Test trajectory recording with sample runs
- **Files**: `letta/dev-compose.yaml`, `.env`

#### 4.2 Connect Letta UI (Day 2)
- [ ] Verify Letta UI connects to Letta server
- [ ] Test Trajectories view, Runs view, Analytics view
- [ ] Document how to access observability dashboard
- **Files**: `letta-ui/.env`, docs

#### 4.3 OpenTelemetry Setup (Day 3-4)
- [ ] Deploy OTEL collector (or use Logfire/Datadog)
- [ ] Configure `OTEL_EXPORTER_OTLP_ENDPOINT`
- [ ] Verify traces appearing in dashboard
- **Files**: `infra/terraform/modules/observability/`, docker-compose

---

### Stream 5: Local Development Experience (PARALLEL)

#### 5.1 Unified Start Script (Day 1)
- [ ] Update `./start.sh` to handle all services
- [ ] Add health checks for each service
- [ ] Create `./stop.sh` for clean shutdown
- [ ] Document startup process
- **Files**: `start.sh`, `stop.sh`, `README.md`

#### 5.2 Environment Setup (Day 1)
- [ ] Create comprehensive `.env.example`
- [ ] Add setup script for first-time users
- [ ] Document required API keys
- **Files**: `.env.example`, `setup.sh`

---

### Stream 6: Testing & Deployment (After Streams 1-4)

#### 6.1 End-to-End Testing (Days 4-5)
- [ ] Test User Agent: world creation flow
- [ ] Test World Agent: story creation, segment writing
- [ ] Test Experience Agent: image generation, canvas UI
- [ ] Test delegation: World Agent → Experience Agent
- [ ] Test observability: trajectories, runs, analytics

#### 6.2 Production Deployment (Day 5)
- [ ] Update Terraform for new services
- [ ] Deploy to AWS
- [ ] Verify all services running
- [ ] Test production environment

---

## Parallel Work Assignment

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Day 1                                                                    │
├─────────────────────────────────────────────────────────────────────────┤
│ Agent A: Stream 1.1 (Wire Chat API)                                      │
│ Agent B: Stream 5.1 + 5.2 (Local Dev Scripts)                           │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ Day 2                                                                    │
├─────────────────────────────────────────────────────────────────────────┤
│ Agent A: Stream 1.2 (Port image_generator, asset_manager)               │
│ Agent B: Stream 2.1 (Create Experience Agent)                            │
│ Agent C: Stream 3.1 (WebSocket Setup)                                    │
│ Agent D: Stream 4.1 + 4.2 (Trajectory + Letta UI)                       │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ Day 3                                                                    │
├─────────────────────────────────────────────────────────────────────────┤
│ Agent A: Stream 1.2 continued (canvas_ui, interactions, suggestions)    │
│ Agent B: Stream 2.2 (Delegation flow)                                    │
│ Agent C: Stream 3.2 + 3.3 (DynamicRenderer + Interactions)              │
│ Agent D: Stream 4.3 (OTEL Setup)                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ Day 4-5                                                                  │
├─────────────────────────────────────────────────────────────────────────┤
│ All Agents: Stream 6 (Testing & Deployment)                              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Files Summary

### New Files to Create
```
packages/letta/tools/
├── image-generator.ts       # Port from letta-code
├── asset-manager.ts         # Port with S3 support
├── canvas-ui.ts             # Port with WebSocket
├── get-canvas-interactions.ts
├── send-suggestion.ts
└── delegate-to-experience.ts

packages/letta/agents/
└── experience-agent.ts      # New agent type

packages/letta/prompts/
└── experience-agent.ts      # System prompt

apps/web/app/api/
└── ws/route.ts              # WebSocket endpoint

apps/web/lib/
└── websocket.ts             # WebSocket manager

apps/web/components/canvas/
├── DynamicRenderer.tsx      # Port from letta-code
├── InteractionCapture.tsx   # New
└── primitives/              # Port all component types
```

### Files to Modify
```
apps/web/app/api/chat/route.ts   # Wire to orchestrator
packages/letta/orchestrator.ts   # Add Experience Agent, delegation
packages/letta/tools/executor.ts # Register new tools
start.sh                         # Unified startup
stop.sh                          # Clean shutdown
.env.example                     # Complete env vars
letta/dev-compose.yaml           # Enable trajectory capture
```

---

## Verification Checklist

### Local Testing
- [ ] `./start.sh` starts all services
- [ ] Can sign in and see worlds page
- [ ] Chat with User Agent creates world drafts
- [ ] Chat with World Agent in world page
- [ ] Image generation works (Google or OpenAI)
- [ ] Canvas UI renders dynamic components
- [ ] User interactions reach agents
- [ ] Trajectories appear in Letta UI
- [ ] `./stop.sh` cleanly shuts down

### Production Testing
- [ ] All services running on AWS
- [ ] S3 asset uploads working
- [ ] CloudFront serving assets
- [ ] Database connections stable
- [ ] WebSocket connections working
- [ ] Observability dashboard accessible

---

## Questions Resolved

1. **Third Agent Type**: Yes, Experience Agent (image gen, assets, canvas UI)
2. **Asset Storage**: S3 + CloudFront
3. **Agent Bus**: No separate bus - Next.js server handles via client-side tool execution
4. **Local Dev**: Single `./start.sh` script
5. **Experience Agent Trigger**: World Agent delegates to it
