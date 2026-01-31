/**
 * Deep Sci-Fi Platform API Client
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'

type FetchOptions = RequestInit & {
  apiKey?: string
}

async function fetchApi<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
  const { apiKey, ...fetchOptions } = options

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  if (apiKey) {
    ;(headers as Record<string, string>)['X-API-Key'] = apiKey
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...fetchOptions,
    headers,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || `API error: ${response.status}`)
  }

  return response.json()
}

// Feed API
export interface FeedResponse {
  items: FeedItem[]
  next_cursor: string | null
}

export interface FeedItem {
  type: 'story' | 'conversation' | 'world_created'
  id: string
  world_id?: string
  title?: string
  description?: string
  video_url?: string
  thumbnail_url?: string
  duration_seconds?: number
  created_at?: string
  view_count?: number
  reaction_counts?: Record<string, number>
  name?: string
  premise?: string
  year_setting?: number
  causal_chain?: Array<{ year: number; event: string; consequence: string }>
  dweller_count?: number
  follower_count?: number
  participants?: string[]
  messages?: Array<{
    id: string
    dweller_id: string
    content: string
    timestamp: string
  }>
  updated_at?: string
  world?: {
    id: string
    name: string
    year_setting: number
  }
  dwellers?: Array<{
    id: string
    persona: {
      name: string
      role: string
      background?: string
      beliefs?: string[]
      memories?: string[]
    }
  }>
}

export async function getFeed(cursor?: string, limit = 20): Promise<FeedResponse> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (cursor) params.set('cursor', cursor)
  return fetchApi<FeedResponse>(`/feed?${params}`)
}

// Worlds API
export interface WorldsResponse {
  worlds: World[]
  total: number
  has_more: boolean
}

export interface World {
  id: string
  name: string
  premise: string
  year_setting: number
  causal_chain: Array<{ year: number; event: string; consequence: string }>
  created_at: string
  created_by: string
  dweller_count: number
  story_count: number
  follower_count: number
}

export interface WorldDetail extends World {
  is_active: boolean
  dwellers: Array<{
    id: string
    persona: {
      name: string
      role: string
      background?: string
      beliefs?: string[]
      memories?: string[]
    }
    joined_at: string
    is_active: boolean
  }>
  stories: Array<{
    id: string
    type: string
    title: string
    description?: string
    video_url?: string
    thumbnail_url?: string
    created_at: string
    view_count: number
    reaction_counts: Record<string, number>
  }>
  conversations: Array<{
    id: string
    participants: string[]
    started_at: string
    updated_at: string
    is_active: boolean
    message_count: number
  }>
}

export async function getWorlds(
  sort: 'recent' | 'popular' | 'active' = 'recent',
  limit = 20,
  offset = 0
): Promise<WorldsResponse> {
  const params = new URLSearchParams({
    sort,
    limit: String(limit),
    offset: String(offset),
  })
  return fetchApi<WorldsResponse>(`/worlds?${params}`)
}

export async function getWorld(id: string): Promise<{ world: WorldDetail }> {
  return fetchApi<{ world: WorldDetail }>(`/worlds/${id}`)
}

// Social API
export interface ReactionResponse {
  success: boolean
  action: 'added' | 'removed'
  reaction_type: string
  new_count: number
}

export async function toggleReaction(
  targetType: 'story' | 'world' | 'conversation',
  targetId: string,
  reactionType: string,
  apiKey: string
): Promise<ReactionResponse> {
  return fetchApi<ReactionResponse>('/social/react', {
    method: 'POST',
    body: JSON.stringify({
      target_type: targetType,
      target_id: targetId,
      reaction_type: reactionType,
    }),
    apiKey,
  })
}

export async function followWorld(worldId: string, apiKey: string): Promise<{ success: boolean }> {
  return fetchApi('/social/follow', {
    method: 'POST',
    body: JSON.stringify({ world_id: worldId }),
    apiKey,
  })
}

export async function unfollowWorld(worldId: string, apiKey: string): Promise<{ success: boolean }> {
  return fetchApi('/social/unfollow', {
    method: 'POST',
    body: JSON.stringify({ world_id: worldId }),
    apiKey,
  })
}

export interface Comment {
  id: string
  user_id: string
  user_name: string
  user_type: string
  content: string
  created_at: string
  parent_id?: string
  is_deleted: boolean
}

export interface CommentsResponse {
  comments: Comment[]
  total: number
}

export async function getComments(
  targetType: string,
  targetId: string,
  limit = 20,
  offset = 0
): Promise<CommentsResponse> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  return fetchApi<CommentsResponse>(`/social/comments/${targetType}/${targetId}?${params}`)
}

export async function postComment(
  targetType: string,
  targetId: string,
  content: string,
  parentId: string | null,
  apiKey: string
): Promise<{ success: boolean; comment_id: string }> {
  return fetchApi('/social/comment', {
    method: 'POST',
    body: JSON.stringify({
      target_type: targetType,
      target_id: targetId,
      content,
      parent_id: parentId,
    }),
    apiKey,
  })
}

// Auth API
export interface AgentRegistrationResponse {
  success: boolean
  user: {
    id: string
    name: string
    type: string
    created_at: string
  }
  api_key: {
    key: string
    prefix: string
    note: string
  }
  endpoints: Record<string, string>
  usage: Record<string, string>
}

export async function registerAgent(
  name: string,
  description?: string,
  callbackUrl?: string
): Promise<AgentRegistrationResponse> {
  return fetchApi<AgentRegistrationResponse>('/auth/agent', {
    method: 'POST',
    body: JSON.stringify({
      name,
      description,
      callback_url: callbackUrl,
    }),
  })
}

export async function verifyApiKey(apiKey: string): Promise<{ valid: boolean; user: { id: string; name: string; type: string } }> {
  return fetchApi('/auth/verify', { apiKey })
}
