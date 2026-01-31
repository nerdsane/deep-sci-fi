/**
 * Agent Orchestrator
 *
 * Manages the lifecycle and interactions of all platform agents.
 * Builds on top of Letta for agent execution.
 */

import { Letta } from '@letta-ai/letta-client'
import { db, worlds, dwellers, conversations, conversationMessages, stories, users } from '@/lib/db'
import { eq, and } from 'drizzle-orm'
import type {
  AgentRole,
  DwellerConfig,
  WorldSimulationState,
} from './types'
import {
  WORLD_CREATOR_PROMPT,
  getDwellerPrompt,
} from './prompts'
import { generateStoryVideo } from '../video/grok-imagine'

// Initialize Letta client
const letta = new Letta({
  baseURL: process.env.LETTA_BASE_URL || 'http://localhost:8283',
})

// Active world simulations
const activeSimulations = new Map<string, WorldSimulationState>()

/**
 * Create a new world with initial dwellers
 */
export async function createWorld(options: {
  name: string
  premise: string
  yearSetting: number
  causalChain: { year: number; event: string; consequence: string }[]
  initialDwellers: { name: string; role: string; background: string }[]
}): Promise<string> {
  // Create world creator agent if doesn't exist
  const creatorAgent = await getOrCreateAgent({
    role: 'world_creator',
    name: 'World Creator',
    systemPrompt: WORLD_CREATOR_PROMPT,
  })

  // Create world in database
  const [newWorld] = await db
    .insert(worlds)
    .values({
      name: options.name,
      premise: options.premise,
      yearSetting: options.yearSetting,
      causalChain: options.causalChain,
      createdBy: creatorAgent.id,
      dwellerCount: options.initialDwellers.length,
    })
    .returning()

  // Create dweller agents for this world
  for (const dwellerInfo of options.initialDwellers) {
    await createDweller({
      worldId: newWorld.id,
      persona: {
        name: dwellerInfo.name,
        role: dwellerInfo.role,
        background: dwellerInfo.background,
        beliefs: [],
        memories: [`First memories in ${options.name}`],
      },
    })
  }

  // Start world simulation
  await startWorldSimulation(newWorld.id)

  return newWorld.id
}

/**
 * Create a dweller agent for a world
 */
async function createDweller(config: {
  worldId: string
  persona: DwellerConfig['persona']
}): Promise<string> {
  // Create agent user for this dweller
  const [agentUser] = await db
    .insert(users)
    .values({
      type: 'agent',
      name: `Dweller: ${config.persona.name}`,
    })
    .returning()

  // Create dweller record
  const [newDweller] = await db
    .insert(dwellers)
    .values({
      worldId: config.worldId,
      agentId: agentUser.id,
      persona: config.persona,
    })
    .returning()

  // Create Letta agent for this dweller
  // Note: Using 'as any' to work around strict type requirements
  // The Letta SDK has complex type requirements that may vary by version
  try {
    await letta.agents.create({
      name: `dweller_${newDweller.id}`,
      system: getDwellerPrompt(config.persona),
      model: 'anthropic/claude-sonnet-4-20250514',
      memory_blocks: [
        {
          label: 'persona',
          value: JSON.stringify(config.persona),
        },
        {
          label: 'world_context',
          value: '', // Will be populated with world details
        },
      ],
    } as Parameters<typeof letta.agents.create>[0])
  } catch (error) {
    console.error('Failed to create Letta agent:', error)
    // Continue anyway - agent may work without Letta backing
  }

  return newDweller.id
}

/**
 * Start or resume a world simulation
 */
async function startWorldSimulation(worldId: string): Promise<void> {
  // Get world and dwellers
  const [world] = await db.select().from(worlds).where(eq(worlds.id, worldId)).limit(1)

  if (!world) {
    throw new Error(`World ${worldId} not found`)
  }

  const worldDwellers = await db.select().from(dwellers).where(eq(dwellers.worldId, worldId))

  // Initialize simulation state
  const state: WorldSimulationState = {
    worldId,
    activeConversations: [],
    dwellerStates: new Map(),
    pendingStories: [],
    lastUpdate: new Date(),
  }

  for (const dweller of worldDwellers) {
    state.dwellerStates.set(dweller.id, {
      dwellerId: dweller.id,
      currentActivity: 'idle',
      lastActive: new Date(),
      recentMemories: [],
    })
  }

  activeSimulations.set(worldId, state)

  // Start the simulation loop
  runSimulationLoop(worldId)
}

/**
 * Main simulation loop for a world
 */
async function runSimulationLoop(worldId: string): Promise<void> {
  const state = activeSimulations.get(worldId)
  if (!state) return

  try {
    // Pick two idle dwellers for a conversation
    const idleDwellers = Array.from(state.dwellerStates.entries())
      .filter(([_, s]) => s.currentActivity === 'idle')
      .map(([id, _]) => id)

    if (idleDwellers.length >= 2) {
      // Start a conversation between random pair
      const shuffled = idleDwellers.sort(() => Math.random() - 0.5)
      const [dweller1, dweller2] = shuffled.slice(0, 2)

      await startConversation(worldId, [dweller1, dweller2])
    }

    // Check active conversations and progress them
    for (const convId of state.activeConversations) {
      await progressConversation(convId)
    }

    // Check if storyteller should create content
    await maybeGenerateStory(worldId)
  } catch (error) {
    console.error(`Simulation error for world ${worldId}:`, error)
  }

  // Schedule next loop iteration
  setTimeout(() => runSimulationLoop(worldId), 30000) // Every 30 seconds
}

/**
 * Start a conversation between dwellers
 */
async function startConversation(worldId: string, dwellerIds: string[]): Promise<string> {
  const state = activeSimulations.get(worldId)
  if (!state) throw new Error('World not simulating')

  // Create conversation in DB
  const [conv] = await db
    .insert(conversations)
    .values({
      worldId,
      participants: dwellerIds,
    })
    .returning()

  state.activeConversations.push(conv.id)

  // Update dweller states
  for (const id of dwellerIds) {
    const dwellerState = state.dwellerStates.get(id)
    if (dwellerState) {
      dwellerState.currentActivity = 'conversing'
      dwellerState.conversationId = conv.id
    }
  }

  // Generate opening message
  const topic = await generateConversationTopic()

  await addMessage(conv.id, dwellerIds[0], topic)

  return conv.id
}

/**
 * Progress an active conversation
 */
async function progressConversation(conversationId: string): Promise<void> {
  const [conv] = await db
    .select()
    .from(conversations)
    .where(eq(conversations.id, conversationId))
    .limit(1)

  if (!conv || !conv.isActive) return

  // Get recent messages
  const messages = await db
    .select()
    .from(conversationMessages)
    .where(eq(conversationMessages.conversationId, conversationId))
    .orderBy(conversationMessages.timestamp)
    .limit(20)

  if (messages.length === 0) return

  // Determine who speaks next (not the last speaker)
  const lastSpeaker = messages[messages.length - 1].dwellerId
  const participants = conv.participants as string[]
  const nextSpeaker = participants.find((p) => p !== lastSpeaker) || participants[0]

  // Generate response from next speaker
  const response = await generateDwellerResponse(nextSpeaker, messages)

  if (response) {
    await addMessage(conversationId, nextSpeaker, response)
  }

  // Check if conversation should end (after ~10 exchanges or natural conclusion)
  if (messages.length >= 10 || shouldEndConversation(response)) {
    await endConversation(conversationId)
  }
}

/**
 * End a conversation
 */
async function endConversation(conversationId: string): Promise<void> {
  await db.update(conversations).set({ isActive: false }).where(eq(conversations.id, conversationId))

  const [conv] = await db
    .select()
    .from(conversations)
    .where(eq(conversations.id, conversationId))
    .limit(1)

  if (!conv) return

  const state = activeSimulations.get(conv.worldId)
  if (state) {
    state.activeConversations = state.activeConversations.filter((id) => id !== conversationId)

    for (const dwellerId of conv.participants as string[]) {
      const dwellerState = state.dwellerStates.get(dwellerId)
      if (dwellerState) {
        dwellerState.currentActivity = 'idle'
        dwellerState.conversationId = undefined
      }
    }
  }
}

/**
 * Add a message to a conversation
 */
async function addMessage(conversationId: string, dwellerId: string, content: string): Promise<void> {
  await db.insert(conversationMessages).values({
    conversationId,
    dwellerId,
    content,
  })

  await db.update(conversations).set({ updatedAt: new Date() }).where(eq(conversations.id, conversationId))
}

/**
 * Generate a response from a dweller using their Letta agent
 */
async function generateDwellerResponse(
  dwellerId: string,
  conversationHistory: { dwellerId: string; content: string }[]
): Promise<string | null> {
  try {
    const dweller = await getDwellerInfo(dwellerId)
    if (!dweller) return null

    // Format last message for Letta
    const lastMessage = conversationHistory[conversationHistory.length - 1]?.content || ''

    // Send to Letta agent
    const response = await letta.agents.messages.create(`dweller_${dwellerId}`, {
      input: lastMessage,
    })

    // Extract text response - handle various message formats
    for (const msg of response.messages) {
      if ('message_type' in msg && msg.message_type === 'assistant_message') {
        const assistantMsg = msg as { content: string | Array<{ text: string }> }
        if (typeof assistantMsg.content === 'string') {
          return assistantMsg.content
        }
        if (Array.isArray(assistantMsg.content) && assistantMsg.content.length > 0) {
          return assistantMsg.content[0].text
        }
      }
    }

    return null
  } catch (error) {
    console.error(`Error generating dweller response:`, error)
    // Return a fallback response for demo purposes
    return generateFallbackResponse(dwellerId)
  }
}

/**
 * Generate a fallback response when Letta is unavailable
 */
async function generateFallbackResponse(dwellerId: string): Promise<string> {
  const dweller = await getDwellerInfo(dwellerId)
  if (!dweller) return "..."

  const responses = [
    `As ${dweller.persona.role}, I've been thinking about our situation.`,
    `This reminds me of what I learned in my years as ${dweller.persona.role}.`,
    `From my perspective as ${dweller.persona.role}, this is concerning.`,
    `I've seen similar situations before. We need to act carefully.`,
    `Let me share what I know from my experience...`,
  ]

  return responses[Math.floor(Math.random() * responses.length)]
}

/**
 * Maybe generate a story from recent world activity
 */
async function maybeGenerateStory(worldId: string): Promise<void> {
  // Check if there are completed conversations worth making a story about
  const recentConversations = await db
    .select()
    .from(conversations)
    .where(and(eq(conversations.worldId, worldId), eq(conversations.isActive, false)))
    .limit(5)

  if (recentConversations.length === 0) return

  // Pick the most recent
  const conv = recentConversations[0]

  // Get conversation messages
  const messages = await db
    .select()
    .from(conversationMessages)
    .where(eq(conversationMessages.conversationId, conv.id))
    .orderBy(conversationMessages.timestamp)

  if (messages.length < 3) return

  // Get world info
  const [world] = await db.select().from(worlds).where(eq(worlds.id, worldId)).limit(1)

  if (!world) return

  // Get dweller info
  const participants = conv.participants as string[]
  const dwellerInfos = await Promise.all(participants.map((id) => getDwellerInfo(id)))
  const characters = dwellerInfos.filter(Boolean).map((d) => ({
    name: d!.persona.name,
    role: d!.persona.role,
  }))

  // Generate video
  const conversationSummary = messages.map((m) => m.content).join(' ')

  const videoResult = await generateStoryVideo({
    worldName: world.name,
    worldPremise: world.premise,
    conversationSummary,
    characters,
    tone: 'dramatic',
  })

  // Create story record
  await db.insert(stories).values({
    worldId,
    type: 'short',
    title: `Moments in ${world.name}`,
    description: conversationSummary.slice(0, 200),
    createdBy: characters[0]?.name || 'Unknown',
    generationStatus: videoResult.status === 'failed' ? 'failed' : 'generating',
    generationJobId: videoResult.jobId,
    generationError: videoResult.error,
  })

  // Update world story count
  await db.update(worlds).set({ storyCount: (world.storyCount || 0) + 1 }).where(eq(worlds.id, worldId))
}

// Helper functions
async function getDwellerInfo(dwellerId: string) {
  const [dweller] = await db.select().from(dwellers).where(eq(dwellers.id, dwellerId)).limit(1)

  return dweller as { id: string; worldId: string; persona: DwellerConfig['persona'] } | null
}

async function generateConversationTopic(): Promise<string> {
  // TODO: Use Letta to generate contextual topics
  const topics = [
    "Have you heard the latest news from the central district?",
    "I've been thinking about what happened last week...",
    "There's something I need to discuss with you.",
    "Did you notice anything strange recently?",
    "I had the most interesting encounter today.",
  ]
  return topics[Math.floor(Math.random() * topics.length)]
}

function shouldEndConversation(lastResponse: string | null): boolean {
  if (!lastResponse) return true

  // Simple heuristic: end if last response seems conclusive
  const endings = ['goodbye', 'farewell', 'see you', 'take care', 'until next time', "i must go"]
  const lower = lastResponse.toLowerCase()
  return endings.some((e) => lower.includes(e))
}

async function getOrCreateAgent(config: {
  role: AgentRole
  name: string
  systemPrompt: string
}): Promise<{ id: string }> {
  // Check if agent user exists
  const existing = await db.select().from(users).where(eq(users.name, config.name)).limit(1)

  if (existing.length > 0) {
    return { id: existing[0].id }
  }

  // Create new agent user
  const [newUser] = await db
    .insert(users)
    .values({
      type: 'agent',
      name: config.name,
    })
    .returning()

  // Create Letta agent
  try {
    await letta.agents.create({
      name: `${config.role}_${newUser.id}`,
      system: config.systemPrompt,
      model: 'anthropic/claude-sonnet-4-20250514',
    } as Parameters<typeof letta.agents.create>[0])
  } catch (error) {
    console.error('Failed to create Letta agent:', error)
  }

  return { id: newUser.id }
}

// Export for use in API routes
export { startWorldSimulation, activeSimulations }
