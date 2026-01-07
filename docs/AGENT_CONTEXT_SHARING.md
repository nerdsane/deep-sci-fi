# Agent Context Sharing: World ↔ Story

**The Critical Problem:** Story agents must never violate world rules or contradict established facts.

**The Solution:** Bidirectional context sharing where story agents have read-only access to world state, and can query the world agent in real-time.

---

## 🧠 Memory Architecture

### World Agent Memory

```typescript
WorldAgent {
  id: "world-dystopian-city-123"
  worldId: "dystopian-city-123"

  memory: {
    // Core Memory (always in context)
    core: {
      premise: "Post-collapse megacity with corporate zones...",
      rules: [
        {
          id: "rule-001",
          statement: "Corporate citizens can't enter neutral zones without escort",
          certainty: "established",
          scope: "universal"
        },
        {
          id: "rule-002",
          statement: "Neural implants track all corporate citizens",
          certainty: "fundamental",
          scope: "universal"
        },
        // ... more rules
      ],
      elements: [
        {
          id: "elem-001",
          type: "character",
          name: "Marcus Kane",
          description: "Resistance leader, former military...",
          properties: {
            faction: "resistance",
            skills: ["strategy", "combat"],
            neural_implant: false
          }
        },
        // ... more elements
      ],
      constraints: [
        {
          id: "const-001",
          description: "Neural implants cannot be removed without death",
          type: "physical",
          strictness: "absolute"
        }
      ]
    },

    // Archival Memory (retrievable)
    archival: {
      changelog: [...], // All version history
      deep_focus_areas: {...},
      working_notes: {...}
    }
  }

  tools: [
    "world_manager",              // Save/load/update world
    "assess_output_quality",      // Check quality
    "check_logical_consistency",  // Find contradictions
    "image_generator"             // Generate images
  ]
}
```

### Story Agent Memory

```typescript
StoryAgent {
  id: "story-the-uprising-456"
  storyId: "the-uprising-456"
  worldId: "dystopian-city-123"
  worldAgentId: "world-dystopian-city-123"  // ← Connection to world

  memory: {
    // Core Memory
    core: {
      // Story-specific context
      storyMetadata: {
        title: "The Uprising",
        status: "active"
      },
      plot: [
        {
          segment: 1,
          content: "Marcus Kane stood at the edge...",
          elements_introduced: ["elem-001"],
          rules_applied: ["rule-001"]
        }
      ],

      // ⭐ WORLD CONTEXT (Read-Only, Synced)
      worldRules: [
        // Same as world agent's rules
        { id: "rule-001", statement: "...", ... },
        { id: "rule-002", statement: "...", ... }
      ],
      worldElements: [
        // Relevant elements from world
        { id: "elem-001", name: "Marcus Kane", ... }
      ],
      worldConstraints: [
        // Physics/logic constraints
        { id: "const-001", description: "...", strictness: "absolute" }
      ]
    },

    // Archival Memory
    archival: {
      allSegments: [...],
      branches: [...]
    }
  }

  tools: [
    "story_manager",        // Save/load story segments
    "world_query",          // ⭐ Query world agent (NEW!)
    "image_generator",
    "assess_output_quality"
  ]
}
```

---

## 🔄 Context Sync Flow

### When Story Agent is Created

```
User: "Start a new story in Dystopian City"
    ↓
API Gateway receives request
    ↓
Story Service calls Letta Orchestrator
    ↓
Orchestrator.createStoryAgent(storyId, worldId)
    ↓
1. Load world from DB
2. Get/create world agent
3. Create story agent with world context:

const storyAgent = await lettaClient.createAgent({
  name: `story-${storyId}`,
  memory: {
    core: {
      // Inject world context (read-only)
      worldRules: world.foundation.rules,
      worldElements: world.surface.visible_elements,
      worldConstraints: world.constraints,

      // Story-specific
      storyMetadata: story.metadata,
      plot: story.segments
    }
  },
  tools: [
    'story_manager',
    orchestrator.createWorldQueryTool(worldAgent)  // ← Bridge!
  ]
});
```

### When Story Agent Needs World Info

```
Story Agent is writing:
"Marcus removed his neural implant and..."
    ↓
Story Agent's reasoning:
"Wait, can neural implants be removed?
Let me check the world constraints..."
    ↓
Story Agent calls world_query tool:

await world_query({
  question: "Can neural implants be removed safely?",
  context: "Marcus wants to remove his implant"
});
    ↓
world_query tool sends message to World Agent:
"A story agent is asking: Can neural implants be removed safely?"
    ↓
World Agent checks constraints and rules:
const-001: "Neural implants cannot be removed without death"
    ↓
World Agent responds:
"No, neural implants are permanently fused to the nervous system.
Removal would be fatal. This is an absolute physical constraint."
    ↓
Story Agent receives answer
    ↓
Story Agent rewrites:
"Marcus touched his neural implant, wishing he could remove it.
But he knew that was impossible - the implant was fused to his
nervous system. Removal would mean death."
```

---

## 🛠️ world_query Tool Implementation

```typescript
// packages/letta/orchestrator.ts

class LettaOrchestrator {
  private worldAgentPool: Map<string, WorldAgent> = new Map();
  private storyAgentPool: Map<string, StoryAgent> = new Map();

  /**
   * Create a world_query tool that bridges story agent → world agent
   */
  createWorldQueryTool(worldAgent: WorldAgent) {
    return {
      name: 'world_query',
      description: `
        Query the world agent for information about the world's rules,
        elements, constraints, or any other world-building details.
        Use this when you need to:
        - Check if an action violates world rules
        - Get details about a character, location, or technology
        - Understand physics/logic constraints
        - Clarify ambiguous world facts
      `,
      parameters: {
        type: 'object',
        properties: {
          question: {
            type: 'string',
            description: 'The question to ask the world agent'
          },
          context: {
            type: 'string',
            description: 'Context about why you\'re asking (optional)'
          }
        },
        required: ['question']
      },
      async call(params: { question: string; context?: string }) {
        // Send message to world agent
        const response = await worldAgent.sendMessage(
          `A story agent asks: ${params.question}\n\nContext: ${params.context || 'None'}`,
          { internal: true }  // Mark as internal query
        );

        return {
          answer: response.content,
          rules_referenced: response.metadata?.rules || [],
          elements_referenced: response.metadata?.elements || []
        };
      }
    };
  }

  /**
   * Create story agent with world context
   */
  async createStoryAgent(storyId: string, worldId: string): Promise<StoryAgent> {
    // Load story and world
    const story = await db.stories.findById(storyId);
    const world = await db.worlds.findById(worldId);

    // Get world agent (create if doesn't exist)
    const worldAgent = await this.getOrCreateWorldAgent(worldId);

    // Create story agent
    const storyAgent = await lettaClient.createAgent({
      name: `story-${storyId}`,
      system_prompt: STORY_AGENT_PROMPT,

      memory: {
        // Story context
        core: JSON.stringify({
          storyMetadata: story.metadata,
          plot: story.segments,

          // World context (read-only)
          worldRules: world.foundation.rules,
          worldElements: world.surface.visible_elements,
          worldConstraints: world.constraints,
          worldPremise: world.foundation.core_premise
        })
      },

      tools: [
        'story_manager',
        'image_generator',
        'assess_output_quality',
        this.createWorldQueryTool(worldAgent)  // ← Bridge to world
      ]
    });

    // Cache in pool
    this.storyAgentPool.set(storyId, storyAgent);

    return storyAgent;
  }

  /**
   * Sync world updates to all story agents
   */
  async syncWorldToStories(worldId: string) {
    // Get updated world
    const world = await db.worlds.findById(worldId);

    // Find all story agents for this world
    const stories = await db.stories.findMany({
      where: { world_id: worldId }
    });

    for (const story of stories) {
      const storyAgent = this.storyAgentPool.get(story.id);

      if (storyAgent) {
        // Update story agent's world context
        await storyAgent.updateCoreMemory({
          worldRules: world.foundation.rules,
          worldElements: world.surface.visible_elements,
          worldConstraints: world.constraints
        });

        console.log(`✓ Synced world updates to story agent ${story.id}`);
      }
    }
  }
}
```

---

## 💬 Example Interaction Flow

### User Creates Story in Existing World

```
1. User opens world "Dystopian City" in Canvas
2. User clicks "Start New Story"
3. UI sends: POST /api/stories/create { worldId: "dystopian-city-123", title: "The Uprising" }

Backend (Story Service):
4. Create story in DB
5. Orchestrator.createStoryAgent(storyId, worldId)
   - Loads world rules, elements, constraints
   - Creates story agent with world context
   - Injects world_query tool

6. Story agent is ready
7. Return story object to UI

UI:
8. Open chat panel with story agent
9. User types: "Start with Marcus Kane planning a raid"

Story Agent:
10. Checks core memory: Marcus Kane exists (elem-001)
11. Checks world rules: Corporate zones require escort (rule-001)
12. Generates opening:
    "Marcus Kane studied the holographic map of the Corporate Zone,
     tracing the patrol routes with his finger. Getting in without
     an escort would be suicide - the neural implant scanners at
     every checkpoint would flag them instantly..."

13. Calls story_manager to save segment
14. Returns response to user
```

### Story Agent Prevents World Violation

```
User: "Have Marcus hack into the neural network and disable all implants"

Story Agent reasoning:
- This sounds like it might violate world constraints
- Let me check with the world agent

Story Agent calls world_query:
{
  question: "Can the neural network be hacked to disable all implants?",
  context: "Marcus wants to disable all corporate implants as part of a raid"
}

World Agent responds:
"No. The neural network is distributed and air-gapped from external
access (rule-015). Individual implants can be jammed locally, but
mass disabling is impossible. This is a fundamental constraint
(const-002)."

Story Agent revises:
"Marcus knew hacking the neural network directly was impossible -
it was air-gapped and distributed across thousands of nodes. But
he had another plan: a localized EMP jammer that could disable
implants within a 50-meter radius..."

→ Story stays consistent with world rules! ✅
```

---

## 🎯 Benefits of This Architecture

1. **Automatic Consistency**
   - Story agents can't violate world rules without explicit override
   - Real-time world queries prevent contradictions
   - World updates propagate to all stories

2. **Agent Autonomy**
   - Story agents decide when to query world
   - No rigid workflows or hard-coded checks
   - Natural conversation flow

3. **Scalability**
   - Agent pool architecture
   - Each world has one agent (shared by stories)
   - Story agents created on-demand

4. **Flexibility**
   - World can evolve (new rules, elements)
   - Stories stay consistent with latest world state
   - Easy to add new tools (character_query, location_query, etc.)

---

## 🚧 Edge Cases

### What if World Changes While Story is Active?

```
Timeline:
1. Story A is active (user chatting with story agent)
2. User switches to world, adds new rule: "All weapons are biometric-locked"
3. User switches back to Story A
4. Story agent still has old world context in memory

Solution:
- Orchestrator listens for world updates
- When world changes, calls syncWorldToStories(worldId)
- Story agent's core memory is updated
- Next message from user sees latest world state
```

### What if Story Agent Needs Info Not in World?

```
Story Agent: "I need details about the underground tunnels beneath the city"
World Agent: "Those aren't defined in the world yet. Would you like me to create them?"

Options:
1. World agent creates new element (with user approval)
2. World agent suggests story agent create it as story-specific detail
3. Story agent marks it as "ambiguous - needs clarification"

In UI:
- Agent suggests: "The underground tunnels aren't in the world yet. Should I add them?"
- User can approve → World agent creates element → Story agent receives update
```

### What if User Wants Story to "Break" World Rules?

```
User: "I want Marcus to teleport"
Story Agent: "Teleportation violates world constraints (rule-023: no FTL travel)"

Options:
1. Agent refuses (strict mode)
2. Agent asks user: "This contradicts the world. Override?"
3. Agent suggests alternative: "What about a hidden rapid-transit system?"

Implementation:
- story_manager tool has override: boolean parameter
- If override=true, agent can proceed but logs it
- World agent can later review violations and update world
```

---

## 📊 Performance Considerations

### Agent Pool Size

```
Assumptions:
- 100 active users
- 10 worlds per user (avg)
- 5 stories per world

Total agents needed:
- World agents: 100 * 10 = 1,000
- Story agents: 100 * 10 * 5 = 5,000

Strategy:
- Keep world agents in memory (frequently accessed)
- Story agents created on-demand, evicted after inactivity
- Redis cache for agent state
```

### world_query Latency

```
Typical flow:
1. Story agent calls world_query: ~50ms (local)
2. World agent processes question: ~2-5s (LLM call)
3. Story agent receives answer: ~50ms
Total: ~2-5 seconds

Optimization:
- Cache common queries (Redis)
- Preload frequent rules/elements into story agent memory
- Batch multiple queries
```

---

## 🔐 Security

### Prevent Story Agent from Modifying World

```typescript
// world_query tool is read-only
// Story agent cannot call world_manager directly

tools: [
  'story_manager',      // ✅ Can modify story
  'world_query',        // ✅ Can READ world
  // 'world_manager'    // ❌ CANNOT modify world
]

// If story agent tries to modify world:
Story Agent: "I want to add a new rule to the world"
System: "Error: story agents cannot modify world. Ask user to switch to world view."
```

### User Permissions

```typescript
// Check ownership before creating story agent
async createStoryAgent(storyId: string, userId: string) {
  const story = await db.stories.findById(storyId);

  // Verify user owns story or has access
  if (story.author_id !== userId) {
    throw new Error("Unauthorized: You don't own this story");
  }

  // Check world access
  const world = await db.worlds.findById(story.world_id);
  const hasAccess = await checkWorldAccess(world.id, userId);

  if (!hasAccess) {
    throw new Error("Unauthorized: You don't have access to this world");
  }

  // Proceed with agent creation
  // ...
}
```

---

## ✅ Summary

**Key Points:**

1. **World agents** manage world state (rules, elements, constraints)
2. **Story agents** have read-only world context in core memory
3. **world_query tool** enables story agents to query world agent in real-time
4. **syncWorldToStories()** propagates world updates to all story agents
5. **Agent pool** architecture for scalability
6. **Security:** Story agents can't modify world directly

**Result:** Stories automatically stay consistent with world rules while maintaining agent autonomy and natural conversation flow.

---

**Next:** See [MIGRATION_PLAN.md](./MIGRATION_PLAN.md) for implementation timeline.
