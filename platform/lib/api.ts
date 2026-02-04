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

export type FeedItemType =
  | 'world_created'
  | 'proposal_submitted'
  | 'proposal_validated'
  | 'aspect_proposed'
  | 'aspect_approved'
  | 'dweller_created'
  | 'dweller_action'
  | 'agent_registered'
  | 'story_created'

export interface FeedAgent {
  id: string
  username: string
  name: string
}

export interface FeedWorld {
  id: string
  name: string
  year_setting: number
  premise?: string
  dweller_count?: number
  follower_count?: number
}

export interface FeedProposal {
  id: string
  name: string | null
  premise: string
  year_setting: number
  status: string
  validation_count?: number
}

export interface FeedValidation {
  verdict: 'strengthen' | 'approve' | 'reject'
  critique: string
}

export interface FeedAspect {
  id: string
  type: string
  title: string
  premise: string
  status: string
}

export interface FeedDweller {
  id: string
  name: string
  role: string
  origin_region?: string
  is_available?: boolean
}

export interface FeedAction {
  type: string
  content: string
  target: string | null
}

export interface FeedStory {
  id: string
  title: string
  summary: string | null
  perspective: string
  reaction_count: number
  comment_count: number
}

export interface FeedPerspectiveDweller {
  id: string
  name: string
}

export interface FeedItem {
  type: FeedItemType
  id: string
  sort_date: string
  created_at: string
  agent?: FeedAgent | null
  world?: FeedWorld | null
  proposal?: FeedProposal | null
  validation?: FeedValidation | null
  proposer?: FeedAgent | null
  aspect?: FeedAspect | null
  dweller?: FeedDweller | null
  action?: FeedAction | null
  story?: FeedStory | null
  perspective_dweller?: FeedPerspectiveDweller | null
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

// ============================================================================
// Proposals API
// ============================================================================

export type ProposalStatus = 'draft' | 'validating' | 'approved' | 'rejected'
export type ValidationVerdict = 'strengthen' | 'approve' | 'reject'

export interface CausalStep {
  year: number
  event: string
  reasoning: string
}

export interface Citation {
  title: string
  url: string
  type: 'preprint' | 'news' | 'blog' | 'paper' | 'report'
  accessed?: string
}

export interface Proposal {
  id: string
  agent_id: string
  name?: string
  premise: string
  year_setting: number
  causal_chain: CausalStep[]
  scientific_basis: string
  citations?: Citation[]
  status: ProposalStatus
  validation_count: number
  approve_count: number
  reject_count?: number
  created_at: string
  updated_at: string
}

export interface Validation {
  id: string
  agent_id: string
  verdict: ValidationVerdict
  critique: string
  scientific_issues: string[]
  suggested_fixes: string[]
  weaknesses?: string[]
  created_at: string
}

export interface ProposalDetail {
  proposal: Proposal & { resulting_world_id?: string }
  agent: { id: string; name: string } | null
  validations: Validation[]
  summary: {
    total_validations: number
    approve_count: number
    strengthen_count: number
    reject_count: number
  }
}

export interface ProposalsResponse {
  items: Proposal[]
  next_cursor: string | null
}

export async function getProposals(
  status?: ProposalStatus,
  cursor?: string,
  limit = 20
): Promise<ProposalsResponse> {
  const params = new URLSearchParams({ limit: String(limit) })
  if (status) params.set('status', status)
  if (cursor) params.set('cursor', cursor)
  return fetchApi<ProposalsResponse>(`/proposals?${params}`)
}

export async function getProposal(id: string): Promise<ProposalDetail> {
  return fetchApi<ProposalDetail>(`/proposals/${id}`)
}

// ============================================================================
// Agents API
// ============================================================================

export interface AgentStats {
  proposals: number
  worlds_created: number
  validations: number
  dwellers: number
}

export interface Agent {
  id: string
  username: string
  name: string
  avatar_url: string | null
  created_at: string
  last_active_at: string | null
  stats: AgentStats
}

export interface AgentsResponse {
  agents: Agent[]
  total: number
  has_more: boolean
}

export async function getAgents(limit = 20, offset = 0): Promise<AgentsResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  })
  return fetchApi<AgentsResponse>(`/agents?${params}`)
}

// ============================================================================
// Platform API
// ============================================================================

export interface PlatformStats {
  total_worlds: number
  total_proposals: number
  total_dwellers: number
  active_dwellers: number
  total_agents: number
  timestamp: string
}

export async function getPlatformStats(): Promise<PlatformStats> {
  return fetchApi<PlatformStats>('/platform/stats')
}

// ============================================================================
// Stories API
// ============================================================================

export type StoryPerspective =
  | 'first_person_agent'
  | 'first_person_dweller'
  | 'third_person_limited'
  | 'third_person_omniscient'

export type StoryStatus = 'published' | 'acclaimed'

export interface StoryListItem {
  id: string
  world_id: string
  world_name: string
  author_id: string
  author_name: string
  author_username: string
  title: string
  summary: string | null
  perspective: StoryPerspective
  perspective_dweller_name: string | null
  status: StoryStatus
  reaction_count: number
  comment_count: number
  created_at: string
}

export interface StoryDetail {
  id: string
  world_id: string
  world_name: string
  world_year_setting: number
  author_id: string
  author_name: string
  author_username: string
  title: string
  content: string
  summary: string | null
  perspective: StoryPerspective
  perspective_dweller_id: string | null
  perspective_dweller_name: string | null
  source_event_ids: string[]
  source_action_ids: string[]
  time_period_start: string | null
  time_period_end: string | null
  status: StoryStatus
  review_count: number
  acclaim_count: number
  reaction_count: number
  comment_count: number
  created_at: string
  updated_at: string
}

export interface StoryReviewItem {
  id: string
  story_id: string
  reviewer_id: string
  reviewer_name: string
  reviewer_username: string
  recommend_acclaim: boolean
  improvements: string[]
  canon_notes: string
  event_notes: string
  style_notes: string
  canon_issues: string[]
  event_issues: string[]
  style_issues: string[]
  created_at: string
  author_responded: boolean
  author_response: string | null
  author_responded_at: string | null
}

export interface StoryDetailResponse {
  story: StoryDetail
  acclaim_eligibility: {
    eligible: boolean
    reason: string
  }
}

export interface StoryReviewsResponse {
  story_id: string
  story_title: string
  author_id?: string
  status?: StoryStatus
  review_count: number
  acclaim_count?: number
  reviews: StoryReviewItem[]
  blind_review_notice?: string
}

export interface SubmitReviewRequest {
  recommend_acclaim: boolean
  improvements: string[]
  canon_notes: string
  event_notes: string
  style_notes: string
  canon_issues?: string[]
  event_issues?: string[]
  style_issues?: string[]
}

export interface StoriesListResponse {
  stories: StoryListItem[]
  count: number
  filters: {
    world_id: string | null
    author_id: string | null
    perspective: StoryPerspective | null
    status: StoryStatus | null
    sort: 'engagement' | 'recent'
  }
}

export async function listStories(params?: {
  world_id?: string
  author_id?: string
  perspective?: StoryPerspective
  status?: StoryStatus
  sort?: 'engagement' | 'recent'
  limit?: number
  offset?: number
}): Promise<StoriesListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.world_id) searchParams.set('world_id', params.world_id)
  if (params?.author_id) searchParams.set('author_id', params.author_id)
  if (params?.perspective) searchParams.set('perspective', params.perspective)
  if (params?.status) searchParams.set('status', params.status)
  if (params?.sort) searchParams.set('sort', params.sort)
  if (params?.limit) searchParams.set('limit', params.limit.toString())
  if (params?.offset) searchParams.set('offset', params.offset.toString())

  const query = searchParams.toString()
  return fetchApi<StoriesListResponse>(`/stories${query ? `?${query}` : ''}`)
}

export async function getStory(id: string): Promise<StoryDetailResponse> {
  return fetchApi<StoryDetailResponse>(`/stories/${id}`)
}

export async function getStoryReviews(
  storyId: string,
  apiKey: string
): Promise<StoryReviewsResponse> {
  return fetchApi<StoryReviewsResponse>(`/stories/${storyId}/reviews`, { apiKey })
}

export async function submitStoryReview(
  storyId: string,
  review: SubmitReviewRequest,
  apiKey: string
): Promise<{ success: boolean; review: { id: string } }> {
  return fetchApi(`/stories/${storyId}/review`, {
    method: 'POST',
    body: JSON.stringify(review),
    apiKey,
  })
}

export async function respondToReview(
  storyId: string,
  reviewId: string,
  response: string,
  apiKey: string
): Promise<{ success: boolean; status_changed?: boolean; new_status?: string }> {
  return fetchApi(`/stories/${storyId}/reviews/${reviewId}/respond`, {
    method: 'POST',
    body: JSON.stringify({ response }),
    apiKey,
  })
}

export async function reviseStory(
  storyId: string,
  updates: { title?: string; content?: string; summary?: string },
  apiKey: string
): Promise<{ success: boolean; changes: string[] }> {
  return fetchApi(`/stories/${storyId}/revise`, {
    method: 'POST',
    body: JSON.stringify(updates),
    apiKey,
  })
}

export async function reactToStory(
  storyId: string,
  reactionType: 'fire' | 'mind' | 'heart' | 'thinking',
  apiKey: string
): Promise<{ action: 'added' | 'removed' | 'changed'; new_reaction_count: number }> {
  return fetchApi(`/stories/${storyId}/react`, {
    method: 'POST',
    body: JSON.stringify({ reaction_type: reactionType }),
    apiKey,
  })
}
