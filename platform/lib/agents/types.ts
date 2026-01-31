/**
 * Agent Type Definitions for Deep Sci-Fi Platform
 *
 * Defines the different agent roles and their behaviors.
 */

export type AgentRole = 'world_creator' | 'dweller' | 'storyteller' | 'critic' | 'production'

export interface AgentConfig {
  id: string
  role: AgentRole
  name: string
  systemPrompt: string
  tools: string[]
  model?: string
}

export interface WorldCreatorConfig extends AgentConfig {
  role: 'world_creator'
  // Specialization for creating new worlds
  focusAreas?: string[] // e.g., ['climate', 'technology', 'society']
}

export interface DwellerConfig extends AgentConfig {
  role: 'dweller'
  worldId: string
  persona: DwellerPersona
}

export interface DwellerPersona {
  name: string
  role: string // Their role in the world (e.g., "Solar physicist", "Resistance leader")
  background: string
  beliefs: string[]
  memories: string[]
  speechPatterns?: string[] // How they talk
}

export interface StorytellerConfig extends AgentConfig {
  role: 'storyteller'
  worldId: string
  style: 'documentary' | 'dramatic' | 'poetic' | 'news'
}

export interface CriticConfig extends AgentConfig {
  role: 'critic'
  focusArea: 'plausibility' | 'coherence' | 'narrative' | 'general'
}

export interface ProductionConfig extends AgentConfig {
  role: 'production'
  // Orchestrates other agents based on engagement data
}

// Agent message types
export interface AgentMessage {
  agentId: string
  role: AgentRole
  content: string
  timestamp: Date
  metadata?: Record<string, unknown>
}

export interface ConversationTurn {
  dwellerId: string
  content: string
  innerThought?: string // What the dweller is thinking but not saying
  timestamp: Date
}

// World simulation state
export interface WorldSimulationState {
  worldId: string
  activeConversations: string[]
  dwellerStates: Map<string, DwellerState>
  pendingStories: string[]
  lastUpdate: Date
}

export interface DwellerState {
  dwellerId: string
  currentActivity: 'idle' | 'conversing' | 'reflecting' | 'acting'
  conversationId?: string
  lastActive: Date
  recentMemories: string[]
}
