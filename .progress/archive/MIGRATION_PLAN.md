# Deep Sci-Fi Migration - Revised Plan v3

## Migration Approach: Non-Destructive ✅

**IMPORTANT**: This migration preserves the original CLI completely:
- `letta-code/` - Original CLI (git submodule, untouched, still runnable)
- `letta-ui/` - Original UI (preserved)
- `letta/` - Letta backend (git submodule, untouched)
- `apps/web/` - **NEW** web application
- `packages/` - **NEW** shared infrastructure

**You can still run the CLI separately.** The web app is an additive migration, not a replacement.

**Future: CLI as Client to Web Agents**
- letta-code could be modified to connect to web backend agents
- Instead of creating its own agents, it talks to User/World agents via API
- Becomes a CLI interface to the same agent system

---

## Critical Architectural Decision: Two-Tier Agent System

### The Complete Architecture ✅

**IMPORTANT**: The User Agent is the **direct equivalent** of letta-code's `createAgent()` function. This creates a universal interface:
- **Web UI** → API → User Agent → World Agents
- **CLI (letta-code)** → API → Same User Agent → Same World Agents

Both clients use the same agent system. The CLI doesn't create its own agents anymore - it connects to the web backend.

**TWO agent tiers needed:**

```
User logs in (Web UI or CLI)
  ↓
User Agent (Orchestrator) - ONE per user
  │  Role: World creation, routing, meta-tasks
  │  Active: When no world is selected
  │  Tools: world_draft_generator, user_preferences
  │  Equivalent to: letta-code's createAgent()
  │
  ↓ User opens World A
  │
World Agent A - ONE per world
  │  Role: Manage World A + all stories in World A
  │  Active: When user is working in World A
  │  Tools: world_manager, story_manager, image_generator
  │
  ├─ Story 1 (in World A)
  ├─ Story 2 (in World A)
  └─ Story 3 (in World A)
```

### Why Two Tiers?

**Problem:** User logs in with no worlds
- Who do they talk to? ❌
- Need an agent to help create first world ✅

**Solution: User Agent (Orchestrator)**
- Exists before any worlds
- Generates world drafts from prompts
- Routes to world agents when user selects a world
- Handles meta-questions ("Which world should I work on?")

**World Agents (as before)**
- One per world
- Manages world + stories in that world
- Active when user is working in specific world

---

## User Flow with Two-Tier System

### 1. User Logs In (No Worlds Yet)

```
User logs in
  ↓
System creates/loads User Agent (orchestrator)
  ↓
User: "I want to write about a post-scarcity society"
  ↓
User Agent: "I can help generate world concepts. Let me create a few options..."
User Agent uses world_draft_generator tool
  ↓
User Agent: Shows 3-4 world draft cards
```

### 2. User Selects World Draft

```
User selects "World A: The Synthesis"
  ↓
System:
  1. Creates World A in database
  2. Creates World Agent A for World A
  ↓
User Agent: "World A created! Opening..."
User Agent routes user to World Agent A
```

### 3. User Works in World A

```
User is now talking to World Agent A
  ↓
User: "Tell me about the governance structure"
  ↓
World Agent A uses world_manager(load) to fetch World A data
World Agent A explains governance
  ↓
User: "I want to write a story about a judge"
  ↓
World Agent A uses story_manager(create) to create Story 1
World Agent A writes first story segment
```

### 4. User Switches Worlds

```
User clicks "Back to Worlds" in UI
  ↓
User Agent becomes active again
  ↓
User: "Show me my worlds"
  ↓
User Agent lists worlds
  ↓
User opens World B
  ↓
User Agent routes to World Agent B
World Agent B becomes active
```

### 5. User Creates Another World

```
User is at world list (User Agent active)
  ↓
User: "I want to write about a dystopian Earth"
  ↓
User Agent generates new world drafts
User selects one → Creates World C → Creates World Agent C
```

---

## Agent Lifecycle & Routing

### User Agent (Orchestrator)

**Created:** When user signs up (one-time)
**Persists:** Forever (one per user)
**Active when:**
- User is at world list
- User has no worlds
- User asks meta questions ("Which world should I work on?")

**Tools:**
- `world_draft_generator` - Generate world concepts from prompts
- `list_worlds` - Show user's worlds
- `user_preferences` - Remember user writing style preferences
- (Later) `suggest_next_action` - Proactive suggestions

**Memory blocks:**
- `persona.mdx` - Deep Sci-Fi assistant personality
- `human.mdx` - User preferences, writing style
- `active_world.mdx` - Currently selected world (for routing)

### World Agents

**Created:** When user selects a world draft or opens existing world
**Persists:** Forever (one per world)
**Active when:**
- User is working in this specific world
- User is in a story that belongs to this world

**Tools:**
- `world_manager` - save/load/update/diff THIS world
- `story_manager` - create/save stories IN THIS world
- `image_generator` - Generate images for THIS world
- `canvas_ui` - Create UI components
- `send_suggestion` - Proactive suggestions

**Memory blocks:**
- `persona.mdx` - Deep Sci-Fi world-building assistant
- `project.mdx` - THIS world's foundation
- `human.mdx` - User preferences (shared from User Agent)
- `current_story.mdx` - Active story context

---

## Database Schema Updates

```prisma
model User {
  id              String   @id @default(cuid())
  email           String   @unique
  name            String
  userAgentId     String?  @unique  // ONE orchestrator agent per user
  // ... other fields
}

model World {
  id              String   @id @default(cuid())
  name            String
  ownerId         String
  worldAgentId    String?  @unique  // ONE world agent per world
  // ... other fields
}

// Optional: Cache agent sessions
model AgentSession {
  id              String   @id @default(cuid())
  agentId         String   @unique  // Letta agent ID
  userId          String?  @unique  // For user agents
  worldId         String?  @unique  // For world agents
  memoryBlocks    Json     // Cached memory blocks
  lastActiveAt    DateTime @updatedAt

  user            User?    @relation(fields: [userId], references: [id])
  world           World?   @relation(fields: [worldId], references: [id])
}
```

---

## LettaOrchestrator Implementation

```typescript
class LettaOrchestrator {
  /**
   * Get or create user's orchestrator agent
   */
  async getOrCreateUserAgent(userId: string, user: User): Promise<string> {
    // Check if user already has orchestrator
    if (user.userAgentId) {
      return user.userAgentId;
    }

    // Create new user agent
    const agent = await this.client.agents.create({
      name: `user-agent-${userId}`,
      system: generateUserAgentPrompt(),
      tools: [
        'world_draft_generator',
        'list_worlds',
        'user_preferences'
      ],
      memory: {
        persona: userAgentPersona,
        human: {
          userId: user.id,
          name: user.name,
          preferences: {}
        },
        active_world: null
      }
    });

    // Save to database
    await db.user.update({
      where: { id: userId },
      data: { userAgentId: agent.id }
    });

    return agent.id;
  }

  /**
   * Get or create world agent
   */
  async getOrCreateWorldAgent(worldId: string, world: World): Promise<string> {
    if (world.worldAgentId) {
      return world.worldAgentId;
    }

    const agent = await this.client.agents.create({
      name: `world-agent-${worldId}`,
      system: generateWorldAgentPrompt(world),
      tools: [
        'world_manager',
        'story_manager',
        'image_generator',
        'canvas_ui',
        'send_suggestion'
      ],
      memory: {
        persona: worldAgentPersona,
        project: world.foundation,
        human: await getUserPreferences(world.ownerId),
        current_story: null
      }
    });

    await db.world.update({
      where: { id: worldId },
      data: { worldAgentId: agent.id }
    });

    return agent.id;
  }

  /**
   * Route message to appropriate agent
   */
  async sendMessage(userId: string, message: string, context: {
    worldId?: string;
    storyId?: string;
  }): Promise<AgentResponse> {
    // If user is in a world, route to world agent
    if (context.worldId) {
      const world = await db.world.findUnique({ where: { id: context.worldId } });
      const worldAgentId = await this.getOrCreateWorldAgent(context.worldId, world);

      // Set story context if in a story
      if (context.storyId) {
        const story = await db.story.findUnique({ where: { id: context.storyId } });
        await this.setStoryContext(worldAgentId, story);
      }

      return await this.sendToAgent(worldAgentId, message);
    }

    // Otherwise, route to user's orchestrator agent
    const user = await db.user.findUnique({ where: { id: userId } });
    const userAgentId = await this.getOrCreateUserAgent(userId, user);

    return await this.sendToAgent(userAgentId, message);
  }

  /**
   * Send message to specific agent
   */
  private async sendToAgent(agentId: string, message: string): Promise<AgentResponse> {
    const response = await this.client.agents.messages.send({
      agentId,
      message,
      streamSteps: true
    });

    return this.parseResponse(response);
  }

  /**
   * Set story context in world agent memory
   */
  async setStoryContext(worldAgentId: string, story: Story) {
    await this.client.agents.blocks.update({
      agentId: worldAgentId,
      blockName: 'current_story',
      value: {
        storyId: story.id,
        title: story.title,
        description: story.description
      }
    });
  }
}
```

---

## Tool Implementations

### User Agent Tools

**world_draft_generator.ts:**
```typescript
export async function world_draft_generator(params: {
  prompt: string;
  count: number;
}, context: { userId: string }) {
  // Use LLM to generate world concepts from prompt
  const drafts = await generateWorldConcepts(params.prompt, params.count);

  // Return structured drafts
  return drafts.map(draft => ({
    name: draft.name,
    summary: draft.summary,
    foundation: {
      premise: draft.premise,
      technology: draft.technology,
      society: draft.society
    }
  }));
}
```

**list_worlds.ts:**
```typescript
export async function list_worlds(params: {}, context: { userId: string, db: PrismaClient }) {
  const worlds = await context.db.world.findMany({
    where: { ownerId: context.userId },
    include: { _count: { select: { stories: true } } }
  });

  return worlds;
}
```

### World Agent Tools (Same as Before)

**world_manager.ts:**
```typescript
export async function world_manager(params: {
  operation: 'save' | 'load' | 'diff' | 'update';
  world_id: string;
  data?: Partial<World>;
}, context: { db: PrismaClient }) {
  // Implementation as before...
}
```

**story_manager.ts:**
```typescript
export async function story_manager(params: {
  operation: 'create' | 'save_segment' | 'load' | 'list' | 'branch';
  world_id: string;
  story_id?: string;
  segment?: StorySegmentData;
}, context: { db: PrismaClient, userId: string }) {
  // Implementation as before...
}
```

---

## UI Integration with Two-Tier Agents

### Worlds List Page (`/worlds`)

**Agent active:** User Agent (orchestrator)

```typescript
export default function WorldsPage() {
  const { data: session } = useSession();
  const { data: worlds } = trpc.worlds.list.useQuery();

  // Get user agent for chat
  const { data: userAgent } = trpc.agents.getUserAgent.useQuery();

  return (
    <div className="worlds-page">
      <WorldsList worlds={worlds} />
      <ChatPanel
        agentId={userAgent?.id}
        context={{ worldId: null }}  // No world selected
        placeholder="Ask me to create a world, or select a world to work on..."
      />
    </div>
  );
}
```

**Chat behavior:**
- User: "I want to write about X" → User Agent generates drafts
- User: "Show my worlds" → User Agent lists worlds
- User clicks world card → Navigate to world view

### World View Page (`/worlds/[worldId]`)

**Agent active:** World Agent for this world

```typescript
export default function WorldPage() {
  const { worldId } = useParams();
  const { data: world } = trpc.worlds.getById.useQuery({ id: worldId });
  const { data: stories } = trpc.stories.list.useQuery({ worldId });

  // Get world agent
  const { data: worldAgent } = trpc.agents.getOrCreateWorldAgent.useQuery({ worldId });

  return (
    <div className="world-page">
      <WorldDetails world={world} />
      <StoriesList stories={stories} />
      <ChatPanel
        agentId={worldAgent?.id}
        context={{ worldId }}
        placeholder="Ask me about this world or create a story..."
      />
    </div>
  );
}
```

**Chat behavior:**
- User: "Tell me about the governance" → World Agent loads world data
- User: "I want to write a story" → World Agent creates story
- User: "Update the world rules" → World Agent uses world_manager(update)

### Story View Page (`/worlds/[worldId]/stories/[storyId]`)

**Agent active:** Same World Agent (with story context set)

```typescript
export default function StoryPage() {
  const { worldId, storyId } = useParams();
  const { data: story } = trpc.stories.getById.useQuery({ id: storyId });

  // Same world agent, but with story context
  const { data: worldAgent } = trpc.agents.getOrCreateWorldAgent.useQuery({ worldId });

  // Set story context
  useEffect(() => {
    if (worldAgent && story) {
      trpc.agents.setStoryContext.mutate({ agentId: worldAgent.id, storyId });
    }
  }, [worldAgent, story]);

  return (
    <div className="story-page">
      <VisualNovelReader segments={story?.segments} />
      <ChatPanel
        agentId={worldAgent?.id}
        context={{ worldId, storyId }}
        placeholder="Continue the story, or ask about the world..."
      />
    </div>
  );
}
```

---

## World Creation Flow (Enhanced)

### Option 1: Form-Based (Current)

```
User fills form → worlds.create → Creates world in DB → Redirects
```

### Option 2: Chat-Based (New)

```
User at /worlds (User Agent active)
  ↓
User: "I want to write about a post-scarcity society"
  ↓
User Agent calls world_draft_generator tool
  ↓
User Agent: "I've created 3 world concepts. Which appeals to you?"
  [Shows 3 draft cards in chat via canvas_ui]
  ↓
User clicks draft 2
  ↓
System creates world from draft
System creates world agent
  ↓
Navigate to /worlds/[newWorldId]
```

---

## CLI Integration - Universal Agent Interface

**Key Insight:** The User Agent **IS** the replacement for letta-code's `createAgent()`.

**Current CLI behavior:**
```typescript
// letta-code/src/agent.ts
function createAgent(userId: string) {
  // Creates a new Letta agent with tools
  // User talks to this agent
}
```

**New behavior (both CLI and Web UI):**
```typescript
// Unified backend API
async function getUserAgent(userId: string) {
  // Returns existing User Agent (orchestrator)
  // Same for CLI and Web UI
  // Same tools, same memory, same state
}
```

**Architecture:**
```
Web UI ──┐
         ├─→ Backend API ─→ User Agent ─→ World Agents
CLI ─────┘
```

**Implementation:**
1. Add REST/tRPC endpoints for agent access
2. Modify letta-code to call API instead of creating local agents
3. Same authentication (NextAuth session)
4. Same agent persistence (database)

**Benefits:**
- ✅ User can start world in CLI, continue in Web UI
- ✅ Same conversation history across interfaces
- ✅ Unified agent state and memory
- ✅ CLI becomes lightweight client
- ✅ No duplicate agent logic

---

## Revised Roadmap

### Phase 2A: Two-Tier Agent System (Week 1)

#### 1. Update Database Schema
- Add `userAgentId` to User model
- Add `worldAgentId` to World model (already exists)
- Add optional `AgentSession` model

#### 2. Implement User Agent (Orchestrator)
- `getOrCreateUserAgent(userId)`
- Generate user agent with `world_draft_generator` tool
- System prompt for orchestrator role

#### 3. Update World Agent System
- Keep `getOrCreateWorldAgent(worldId)` as before
- Add routing logic (`sendMessage` with context)

#### 4. Implement Tools
- **User Agent tools:**
  - `world_draft_generator` - Generate world concepts
  - `list_worlds` - List user's worlds
- **World Agent tools:**
  - `world_manager` (port from CLI)
  - `story_manager` (port from CLI)
  - `image_generator` (stub for later)
  - `canvas_ui` (port from CLI)

#### 5. Update Routers (Universal API for Web UI + CLI)
- `agents.getUserAgent` - Get user's orchestrator (replaces createAgent)
- `agents.getOrCreateWorldAgent` - Get world agent
- `agents.setStoryContext` - Update story context
- `chat.sendMessage` - Route to appropriate agent based on context
- `chat.streamMessages` - Stream agent responses (for real-time chat)

**Success criteria for Phase 2A:**
- ✅ Database schema supports two-tier agents
- ✅ Architecture defined and documented
- ✅ Routers defined with clear errors
- ✅ User Agent tools defined
- ❌ **BLOCKER: Letta SDK integration not implemented**

---

## **Phase 2A-SDK: Letta SDK Integration** (CRITICAL - CURRENT PHASE)

**STATUS**: This phase was MISSED in initial implementation. All agent methods are stubs.

**BLOCKER**: Nothing works until this is complete. All endpoints throw "Not yet implemented" errors.

### What We Learned from letta-code:

**Letta Client Initialization:**
```typescript
// letta-code/src/agent/client.ts
import Letta from "@letta-ai/letta-client";

const client = new Letta({
  apiKey: process.env.LETTA_API_KEY || settings.LETTA_API_KEY,
  baseURL: process.env.LETTA_BASE_URL || "http://localhost:8283",
  defaultHeaders: {
    "X-Letta-Source": "deep-sci-fi",
    "User-Agent": "deep-sci-fi/0.1.0",
  },
});
```

**Agent Creation:**
```typescript
// letta-code/src/agent/create.ts
const agent = await client.agents.create({
  agent_type: "letta_v1_agent",
  system: systemPromptContent,
  name: `user-agent-${userId}`,
  description: "Deep Sci-Fi User Agent (Orchestrator)",
  embedding: "openai/text-embedding-3-small",
  model: "anthropic/claude-opus-4-5-20251101",
  context_window_limit: 200000,
  tools: toolNames,
  block_ids: blockIds,
  include_base_tools: false,
  parallel_tool_calls: true,
  enable_sleeptime: false,
});
```

**Memory Blocks:**
```typescript
// letta-code/src/agent/memory.ts
// Memory blocks are created from .mdx files
const block = await client.blocks.create({
  label: "persona",
  value: personaContent,
  description: "Agent personality and role",
  limit: 2000,
  read_only: false,
});
```

**Message Sending:**
```typescript
// letta-code/src/agent/message.ts
const stream = await client.agents.messages.create(agentId, {
  messages: [{ role: "user", content: message }],
  streaming: true,
  stream_tokens: true,
  background: true,
  client_tools: getClientToolsFromRegistry(),
});

for await (const chunk of stream) {
  // Handle: reasoning_message, assistant_message, tool_call_message,
  //         tool_return_message, approval_request_message, ping
}
```

**Tool Registration:**
```typescript
// letta-code/src/tools/manager.ts
const clientTools = toolRegistry.map(tool => ({
  name: tool.name,
  description: tool.description,
  parameters: tool.schema.input_schema,
}));

// Tools are passed in messages.create() call
```

---

### Implementation Tasks:

#### 1. Initialize Letta Client (packages/letta/orchestrator.ts)
- Import `Letta` from `@letta-ai/letta-client`
- Create singleton Letta client instance
- Use `LETTA_API_KEY` and `LETTA_BASE_URL` from environment
- Add custom headers for tracking
- Handle connection errors gracefully

**Files to modify:**
- `packages/letta/orchestrator.ts` - Add client initialization

#### 2. Create Memory Block System (packages/letta/memory/)
- Create memory block definitions (persona, human, project, etc.)
- Implement memory block creation and caching
- Store block IDs in database (AgentSession model)
- Support updating memory blocks

**Files to create:**
- `packages/letta/memory/blocks.ts` - Memory block definitions
- `packages/letta/memory/manager.ts` - Memory block CRUD

**Memory Blocks Needed:**
- **User Agent**: `persona` (orchestrator role), `human` (user preferences)
- **World Agent**: `persona` (world agent role), `project` (world foundation), `human` (user preferences), `current_story` (active story)

#### 3. Implement getOrCreateUserAgent()
- Check if user has `userAgentId` in database
- If exists, return existing agent ID
- If not, create new User Agent:
  - Create memory blocks (persona, human)
  - Get tool names from User Agent tools
  - Call `client.agents.create()` with proper config
  - Save agent ID to `User.userAgentId`
  - Cache in `AgentSession` table

**Files to modify:**
- `packages/letta/orchestrator.ts` - Implement method

#### 4. Implement getOrCreateWorldAgent()
- Check if world has `worldAgentId` in database
- If exists, return existing agent ID
- If not, create new World Agent:
  - Create memory blocks (persona, project, human, current_story)
  - Get tool names from World Agent tools
  - Call `client.agents.create()` with world-specific config
  - Save agent ID to `World.worldAgentId`
  - Cache in `AgentSession` table

**Files to modify:**
- `packages/letta/orchestrator.ts` - Implement method

#### 5. Implement Tool Registration
- Port User Agent tools to Letta SDK format
- Create tool registry similar to letta-code
- Map tool names to implementations
- Register tools with client

**Files to create:**
- `packages/letta/tools/registry.ts` - Tool registry
- `packages/letta/tools/executor.ts` - Tool execution

**Tools to register:**
- User Agent: `world_draft_generator`, `list_worlds`, `user_preferences`
- World Agent: (to be ported later) `world_manager`, `story_manager`, etc.

#### 6. Implement sendMessage() with Streaming
- Route to correct agent based on context (worldId presence)
- Call `client.agents.messages.create()` with streaming
- Handle stream chunks (reasoning, assistant, tool_call, tool_return)
- Parse responses into `AgentResponse` format
- Handle errors and retries

**Files to modify:**
- `packages/letta/orchestrator.ts` - Implement sendMessage and sendToAgent

#### 7. Implement setStoryContext()
- Update `current_story` memory block in world agent
- Call `client.agents.blocks.update()` with story info

**Files to modify:**
- `packages/letta/orchestrator.ts` - Implement method

#### 8. Environment Configuration
- Add Letta configuration to `.env.example`
- Document required environment variables
- Add validation for missing configuration

**Files to modify:**
- `apps/web/.env.example` - Add Letta config

#### 9. Error Handling & Logging
- Add proper error handling for SDK calls
- Log agent creation, message sending
- Handle network failures, token refresh
- Provide clear error messages to users

#### 10. Testing
- Test User Agent creation
- Test World Agent creation
- Test message routing (no worldId vs with worldId)
- Test tool execution
- Test memory block updates

---

### Critical Files to Create/Modify:

**Create:**
- `packages/letta/memory/blocks.ts` - Memory block definitions
- `packages/letta/memory/manager.ts` - Block CRUD operations
- `packages/letta/tools/registry.ts` - Tool registry singleton
- `packages/letta/tools/executor.ts` - Tool execution logic

**Modify:**
- `packages/letta/orchestrator.ts` - Implement ALL stub methods
- `packages/letta/tools/world-draft-generator.ts` - Remove stub error
- `packages/letta/tools/list-worlds.ts` - Already works (database query)
- `packages/letta/tools/user-preferences.ts` - Already works (database query)
- `apps/web/.env.example` - Add Letta configuration

**Environment Variables:**
```bash
# Letta Configuration
LETTA_BASE_URL=http://localhost:8283
LETTA_API_KEY=your-letta-api-key-here

# Model Configuration (optional)
LETTA_DEFAULT_MODEL=anthropic/claude-opus-4-5-20251101
LETTA_EMBEDDING_MODEL=openai/text-embedding-3-small
```

---

### Success Criteria for Phase 2A-SDK:

- [ ] Letta client initializes successfully
- [ ] User Agent can be created with memory blocks
- [ ] World Agent can be created with memory blocks
- [ ] Messages route correctly based on context
- [ ] Tools execute and return results
- [ ] Streaming responses work
- [ ] Agent IDs saved to database
- [ ] No more "Not yet implemented" errors in agent system
- [ ] Can have full conversation with User Agent
- [ ] Can have full conversation with World Agent
- [ ] Story context updates work

---

### Phase 2B: UI Integration

#### 6. Update Worlds List Page
- Add ChatPanel with User Agent
- Show world draft cards from agent
- Enable chat-based world creation

#### 7. Create/Update World View Page
- Show world details
- Add ChatPanel with World Agent
- Enable world exploration via chat

#### 8. Build Story View Page
- `/worlds/[worldId]/stories/[storyId]`
- VisualNovelReader for segments
- ChatPanel with World Agent (story context set)
- Enable story writing via chat

---

### Phase 2C: Polish & Enhancement (Week 3+)

#### 9. World Draft Generation UI
- Improve draft card display
- Add draft comparison
- Enable editing drafts before creating

#### 10. Advanced Features
- AWS S3 integration
- Agent-Bus (WebSockets)
- Story branching
- Proactive suggestions
- CLI integration

---

## Success Metrics

### MVP (Phase 2A-2B Complete)
- [ ] User logs in → User Agent created
- [ ] User can chat with orchestrator
- [ ] User can request world drafts via chat
- [ ] User can select draft → creates world + world agent
- [ ] User can chat with world agent about world
- [ ] User can create story → world agent writes segments
- [ ] Multiple stories in world use same world agent
- [ ] User can switch between worlds → different agents active

### Enhanced (Phase 2C+)
- [ ] Draft generation with rich UI
- [ ] Image generation works
- [ ] Agent creates UI components
- [ ] File uploads work
- [ ] Real-time updates
- [ ] CLI connects to web agents

---

## What This Fixes

### Before (Missing Layer)
- ❌ User logs in with no worlds → no agent to talk to
- ❌ World creation was form-only, no conversational assistance

### After (Two-Tier)
- ✅ User Agent always available
- ✅ Chat-based world creation
- ✅ Seamless routing between user/world agents
- ✅ Coherent experience from login to story writing

---

## Next Immediate Steps

1. **Update database schema:**
   - Add `userAgentId` to User model
   - Add `AgentSession` model

2. **Implement User Agent:**
   - Create orchestrator with world generation tools
   - Test world draft generation

3. **Update routing logic:**
   - Route messages based on context (worldId presence)
   - Create user agent on first login

4. **Build enhanced worlds list page:**
   - Add ChatPanel with User Agent
   - Show world drafts from chat

This completes the agent architecture and enables conversational world creation from login to story writing.
