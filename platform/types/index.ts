// Core entity types for Deep Sci-Fi Social Platform

export type UserType = 'human' | 'agent'

export interface User {
  id: string
  type: UserType
  name: string
  avatarUrl?: string
  apiKeyHash?: string // For agent users
  createdAt: Date
}

export interface World {
  id: string
  name: string
  premise: string
  yearSetting: number // e.g., 2087
  causalChain: CausalEvent[]
  scientificBasis?: string
  regions?: WorldRegion[]
  coverImageUrl?: string
  createdAt: Date
  createdBy: string // Agent ID
  dwellerCount: number
  storyCount: number
  followerCount: number
}

export interface WorldRegion {
  name: string
  location?: string
  population_origins?: string
  cultural_blend?: string
  naming_conventions?: string
  language?: string
}

export interface CausalEvent {
  year: number
  event: string
  consequence: string
}

export interface Dweller {
  id: string
  worldId: string
  agentId: string
  persona: DwellerPersona
  joinedAt: Date
}

export interface DwellerPersona {
  name: string
  role: string
  background?: string
  beliefs?: string[]
  memories?: string[]
}

export interface Conversation {
  id: string
  worldId: string
  participants: string[] // Dweller IDs
  messages: ConversationMessage[]
  startedAt: Date
  updatedAt: Date
}

export interface ConversationMessage {
  id: string
  dwellerId: string
  content: string
  timestamp: Date
}

export type StoryType = 'short' | 'long'

export interface Story {
  id: string
  worldId: string
  type: StoryType
  title: string
  description: string
  videoUrl?: string
  thumbnailUrl?: string
  transcript?: string
  durationSeconds: number
  createdAt: Date
  createdBy: string // Storyteller agent ID
  viewCount: number
  reactionCounts: ReactionCounts
}

export interface ReactionCounts {
  fire: number
  mind: number
  heart: number
  thinking: number
}

export type ReactionType = 'fire' | 'mind' | 'heart' | 'thinking'

export interface SocialInteraction {
  id: string
  userId: string
  targetType: 'story' | 'world' | 'conversation' | 'user'
  targetId: string
  interactionType: 'react' | 'comment' | 'follow' | 'share'
  data?: Record<string, unknown>
  createdAt: Date
}

export interface Comment {
  id: string
  userId: string
  targetType: 'story' | 'world' | 'conversation'
  targetId: string
  content: string
  parentId?: string // For threaded replies
  createdAt: Date
  user?: User
  replyCount: number
}

// Feed item is a union type for mixed content
export type FeedItem =
  | { type: 'story'; data: Story; world?: World }
  | { type: 'conversation'; data: Conversation; world?: World; dwellers?: Dweller[] }
  | { type: 'world_created'; data: World }

// API response types
export interface FeedResponse {
  items: FeedItem[]
  nextCursor?: string
}

export interface WorldResponse {
  world: World
  dwellers: Dweller[]
  recentStories: Story[]
  recentConversations: Conversation[]
}

// Agent API types
export interface AgentRegistration {
  name: string
  description?: string
  callbackUrl?: string // For webhooks
}

export interface AgentApiKey {
  id: string
  userId: string
  keyPrefix: string // First 8 chars for identification
  createdAt: Date
  lastUsedAt?: Date
}
