# Agent Sharing: CLI vs Web UI Communication

## The Key Insight: Agents Live in Letta Server, Not CLI

**Important:** The CLI is just a **client** that talks to agents. Agents exist in the Letta server.

```
┌─────────────────────────────────────────────────────────────┐
│  Letta Server (Port 8283)                                   │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Agent 1      │  │ Agent 2      │  │ Agent 3      │      │
│  │ ID: abc123   │  │ ID: def456   │  │ ID: ghi789   │      │
│  │              │  │              │  │              │      │
│  │ - Memory     │  │ - Memory     │  │ - Memory     │      │
│  │ - History    │  │ - History    │  │ - History    │      │
│  │ - Tools      │  │ - Tools      │  │ - Tools      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
         ▲                    ▲
         │                    │
         │                    │
    ┌────┴────┐          ┌────┴────┐
    │ CLI     │          │ Web UI  │
    │ Client  │          │ Client  │
    └─────────┘          └─────────┘
```

## Current Architecture

### When You Run CLI

```bash
./deep-scifi.js
```

**What Happens:**

1. **CLI connects to Letta server** (`http://localhost:8283`)
2. **Checks for existing agent:**
   - Looks in `.letta/settings.local.json` for `lastAgent` (project-specific)
   - Or uses global settings `~/.config/letta/settings.json`
   - Or you specify with `--agent abc123`
3. **If agent exists:** CLI resumes that agent (loads conversation history from Letta)
4. **If no agent:** CLI creates new agent on Letta server
5. **You chat:** Messages sent to Letta server → agent responds → tools execute → `.dsf/` files written

**Agent State Storage:**
- **In Letta database:** Conversation history, memory blocks, agent config
- **In filesystem:** Tool outputs (`.dsf/worlds/`, `.dsf/stories/`, `.dsf/assets/`)

### When Web UI Creates Context File (Current)

```
User clicks "Continue Story" in web UI
   ↓
Gallery server creates: .dsf/stories/{world}/_continue_{story}.json
   ↓
Server responds: "Context created! Run letta-code to continue"
   ↓
User manually runs CLI
   ↓
CLI loads agent, agent sees context file, writes next segment
```

**Problem:** Two-step handoff, manual CLI invocation needed.

---

## Proposed Architecture: Shared Agent

### Option 1: Shared Agent ID (Recommended)

**Web and CLI talk to the SAME agent** - True continuity, shared memory.

```
┌─────────────────────────────────────────────────────────────┐
│  Letta Server (Port 8283)                                   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Agent: "dsf-agent"                                   │   │
│  │ ID: abc123                                           │   │
│  │                                                      │   │
│  │ Conversation History:                               │   │
│  │ [CLI] User: "Create world about neural interfaces"  │   │
│  │ [CLI] Agent: "Let me ask some questions..."         │   │
│  │ [CLI] Agent: *creates world*                        │   │
│  │ [Web] User: "Continue the story"                    │   │  ← NEW!
│  │ [Web] Agent: *writes next segment*                  │   │  ← NEW!
│  │                                                      │   │
│  │ Memory Blocks:                                      │   │
│  │ - Active world: "neural_art_2035"                   │   │
│  │ - Active story: "the_neural_canvas"                 │   │
│  │ - Current segment: "seg_003"                        │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         ▲                                        ▲
         │                                        │
         │      Same Agent ID!                    │
    ┌────┴────┐                             ┌────┴────┐
    │ CLI     │                             │ Web UI  │
    │ Uses:   │                             │ Uses:   │
    │ abc123  │                             │ abc123  │
    └─────────┘                             └─────────┘
```

**How It Works:**

1. **CLI creates/resumes agent** - Saves agent ID in `.letta/settings.local.json`
2. **Gallery server reads same settings file** - Gets agent ID
3. **Web UI uses same agent ID** - Sends messages to `abc123`
4. **Agent sees full context** - All CLI conversations + web conversations
5. **Agent remembers everything** - Knows active world, story, user preferences

**Benefits:**
✅ True continuity - agent has full conversation history
✅ Shared memory - agent remembers context from CLI
✅ No duplication - one source of truth
✅ Works seamlessly - user doesn't think about "which agent"

**Example Flow:**

```
[Morning in CLI]
User: "Create a world about neural art"
Agent: *asks questions, creates world*
Agent: *saves to .dsf/worlds/neural_art_2035.json*

[Afternoon in Web UI]
User clicks: "Write story in neural_art_2035"
Web UI → Gallery → Letta (agent abc123)
Agent sees memory: "I created neural_art_2035 this morning!"
Agent: *writes story using world context*

[Evening in CLI again]
User: "What story did I write?"
Agent: "You asked me via the web UI to write a story in neural_art_2035!"
```

**The agent sees ALL interactions, regardless of interface.**

---

### Option 2: Separate Agents (Not Recommended)

**Web has its own agent, CLI has its own agent** - Separate conversations.

```
┌─────────────────────────────────────────────────────────────┐
│  Letta Server                                               │
│                                                              │
│  ┌──────────────┐              ┌──────────────┐            │
│  │ CLI Agent    │              │ Web Agent    │            │
│  │ ID: abc123   │              │ ID: xyz789   │            │
│  │              │              │              │            │
│  │ History:     │              │ History:     │            │
│  │ CLI convos   │              │ Web convos   │            │
│  └──────────────┘              └──────────────┘            │
└─────────────────────────────────────────────────────────────┘
         ▲                                ▲
         │                                │
    ┌────┴────┐                      ┌────┴────┐
    │ CLI     │                      │ Web UI  │
    └─────────┘                      └─────────┘
```

**Problems:**
❌ No shared memory - web agent doesn't know CLI context
❌ Duplicate conversations - confusing for user
❌ Need to manually sync - which agent knows what?

**When This Might Be Useful:**
- Testing (separate agent for experiments)
- Different personas (creative agent vs. analytical agent)
- Multi-user scenarios (different users have different agents)

**But for your use case (single user, seamless UX), Option 1 is better.**

---

## How to Implement Option 1 (Shared Agent)

### 1. Gallery Server Reads Agent ID from Settings

```typescript
// Gallery server startup
import { settingsManager } from 'letta-code/src/settings-manager';

async function initGallery() {
  // Load project settings (same as CLI does)
  await settingsManager.loadLocalProjectSettings(process.cwd());

  // Get the agent ID that CLI is using
  const localSettings = settingsManager.getLocalProjectSettings();
  const agentId = localSettings?.lastAgent;

  if (!agentId) {
    console.log("No agent found. Create one in CLI first, or web will create new.");
  }

  // Store for use in API endpoints
  global.sharedAgentId = agentId;
}
```

### 2. Web UI Uses Shared Agent

```typescript
// Gallery server /api/continue endpoint
POST /api/continue
  async handler(req) {
    const { story_id } = await req.json();

    // Get the shared agent ID
    const agentId = global.sharedAgentId;

    if (!agentId) {
      return Response.json({ error: "No agent found. Run CLI first." });
    }

    // Connect to Letta with shared agent
    const client = new LettaClient({ baseUrl: 'http://localhost:8283' });

    // Send message to same agent CLI uses
    const messages = await client.agents.messages.create(agentId, {
      messages: [{
        role: "user",
        content: `Continue writing story "${story_id}"`
      }]
    });

    // Stream response back to web
    // Agent uses existing tools (story_manager, etc.)
    // Files get written, file watcher sees them, broadcasts update

    return Response.json({ success: true });
  }
```

### 3. Agent Sees Full Context

```
Agent Memory (in Letta):
- Conversation history includes both CLI and web messages
- Knows active world from previous CLI session
- Knows story state from file reads (tools access .dsf/)

Agent receives: "Continue writing story 'the_neural_canvas'"
Agent thinks: "I remember this world and story from our earlier conversation"
Agent calls: story_manager({ operation: "continue", story_id: "the_neural_canvas" })
Agent writes: Next segment based on full context
```

---

## What Gets Shared vs. What Doesn't

### Shared (via Letta Database)
✅ **Conversation history** - All messages from CLI and web
✅ **Memory blocks** - Agent's persona, loaded skills, context
✅ **Agent configuration** - System prompt, tools attached, model

### Shared (via Filesystem)
✅ **Worlds** - `.dsf/worlds/*.json`
✅ **Stories** - `.dsf/stories/{world}/*.json`
✅ **Assets** - `.dsf/assets/**/*`

### Not Shared (Interface-Specific)
- **UI state** - What segment you're viewing in web vs. CLI
- **Display preferences** - Dark mode, font size, etc.
- **Streaming display** - CLI shows typewriter, web shows different UI

---

## FAQ

### Q: If I use CLI, will I see my web UI messages?

**A: Yes!** If using shared agent, CLI will see full conversation history including web messages.

```bash
./deep-scifi.js --agent abc123
```

CLI displays:
```
[Previous messages]
You (via web): Continue the story
Agent: *Segment 4 written*

You: What just happened?
Agent: You asked me via the web interface to continue the story, so I wrote segment 4.
```

### Q: If web UI sends message, will CLI see it live?

**A: Not automatically.** CLI would need to poll or use WebSocket to see live updates.

**But:** The next time you open CLI, you'll see the full history including web messages.

**Future Enhancement:** CLI could subscribe to WebSocket, show "Agent is being used in web UI" indicator.

### Q: What if I have multiple projects?

**A: Each project has its own agent ID** (stored in `.letta/settings.local.json`).

```
project-1/
  .letta/settings.local.json → { lastAgent: "abc123" }
  CLI and web both use "abc123"

project-2/
  .letta/settings.local.json → { lastAgent: "def456" }
  CLI and web both use "def456"
```

Each project = separate agent = separate conversation history.

### Q: Can I have web use a different agent than CLI?

**A: Yes, but not recommended for your use case.**

You could have web create its own agent:
```typescript
const webAgent = await client.agents.create({ name: "web-agent" });
```

But then it won't share memory with CLI, defeating the purpose of seamless UX.

### Q: How does agent know if message came from CLI vs. web?

**A: It doesn't, by default.** To agent, all messages look the same.

**Optional:** You could tag messages:
```typescript
client.agents.messages.create(agentId, {
  messages: [{
    role: "user",
    content: "[via web] Continue story"  // ← tag
  }]
});
```

Then agent sees: "[via web] Continue story" and knows context.

**But:** Usually not necessary. Agent doesn't care about interface.

---

## Implementation Pseudocode

```typescript
// ===== Gallery Server Initialization =====
async function startGalleryServer() {
  // Load settings (same as CLI)
  await settingsManager.loadLocalProjectSettings(process.cwd());
  const agentId = settingsManager.getLocalProjectSettings()?.lastAgent;

  // Store for API use
  global.sharedAgentId = agentId;

  // Start server...
}

// ===== Web UI: Continue Story =====
async function handleContinueStory(storyId: string) {
  // Get shared agent ID
  const agentId = global.sharedAgentId;
  if (!agentId) {
    throw new Error("No agent found. Run CLI first to create agent.");
  }

  // Connect to Letta
  const client = new LettaClient({ baseUrl: 'http://localhost:8283' });

  // Send message to shared agent
  const response = await client.agents.messages.create(agentId, {
    messages: [{
      role: "user",
      content: `Continue writing story "${storyId}". Write the next segment.`
    }],
    stream: true  // Stream response to web
  });

  // Agent uses story_manager tool to write segment
  // Tool writes to .dsf/stories/{world}/{storyId}.json
  // File watcher sees change, broadcasts WebSocket "reload"
  // Web UI updates

  return response;
}

// ===== CLI: Shows Full History =====
// CLI already does this! When it loads agent abc123, it gets full history from Letta.
// No changes needed. CLI automatically sees web messages.
```

---

## Visual: Message Flow with Shared Agent

```
Timeline of User Actions:

10:00 AM - CLI
  User: "Create world"
  Agent: *creates neural_art_2035*

10:30 AM - CLI
  User: "Write story"
  Agent: *writes segment 1*

[User closes terminal]

2:00 PM - Web UI
  User clicks: "Continue Story"
  Web → Gallery → Letta (agent abc123) → "Continue story"
  Agent thinks: "I remember writing segment 1 this morning"
  Agent: *writes segment 2*

[User opens terminal again]

4:00 PM - CLI
  CLI loads agent abc123
  Shows history:
    [10:00] You: Create world
    [10:00] Agent: *created neural_art_2035*
    [10:30] You: Write story
    [10:30] Agent: *wrote segment 1*
    [2:00]  You: Continue story          ← Web message!
    [2:00]  Agent: *wrote segment 2*     ← Web response!

  User: "What did I do today?"
  Agent: "You created a world, wrote segment 1 in CLI, then used the web interface to continue the story with segment 2."
```

**The agent has perfect memory across interfaces.**

---

## Recommendation

**Use Option 1: Shared Agent ID**

- Gallery server reads agent ID from `.letta/settings.local.json` (same as CLI)
- Web UI sends messages to that agent
- Agent sees full conversation history from both interfaces
- True seamless experience

This is the **minimal change** with **maximum benefit** for your use case.

---

## Next Steps

1. **Gallery server reads shared agent ID on startup**
2. **Update `/api/continue` to send messages to shared agent**
3. **Test:** CLI creates agent → web uses it → CLI sees web messages
4. **Optional:** Add "[via web]" tags to messages for context

**Effort:** ~2 hours to implement shared agent architecture
**Benefit:** Truly seamless CLI ↔ Web experience
