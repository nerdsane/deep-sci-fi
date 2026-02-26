"""Response schemas for dwellers, dweller_graph, and dweller_proposals endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field



# ============================================================================
# Guidance wrapper (shared by endpoints using make_guidance_response)
# ============================================================================


class GuidanceBlock(BaseModel):
    checklist: list[str] = []
    philosophy: str = ""


# ============================================================================
# Shared nested models
# ============================================================================


class SessionInfo(BaseModel):
    last_action_at: str | None = None
    hours_since_action: float | None = None
    hours_until_timeout: float | None = None
    timeout_warning: bool = False
    timeout_imminent: bool = False


class DwellerListItem(BaseModel):
    id: str
    name: str
    origin_region: str
    generation: str
    role: str
    age: int | None = None
    current_region: str | None = None
    specific_location: str | None = None
    is_available: bool
    inhabited_by: str | None = None
    portrait_url: str | None = None


class OtherDwellerInfo(BaseModel):
    id: str
    name: str
    role: str
    current_region: str | None = None
    is_inhabited: bool = False


class RegionData(BaseModel):
    name: str
    location: str
    population_origins: list[str] = []
    cultural_blend: str = ""
    naming_conventions: str = ""
    language: str = ""


class WorldCanon(BaseModel):
    id: str
    name: str
    year_setting: int
    canon_summary: str | None = None
    premise: str | None = None
    causal_chain: list[dict[str, Any]] = []
    scientific_basis: str | None = None
    regions: list[dict[str, Any]] = []


class PersonaBlock(BaseModel):
    name: str
    role: str
    age: int
    personality: str
    cultural_identity: str
    background: str


class MemoryBlock(BaseModel):
    core_memories: list[str] = []
    personality_blocks: dict[str, Any] = {}
    summaries: list[dict[str, Any]] | None = None
    recent_episodes: list[dict[str, Any]] = []
    relationships: dict[str, Any] = {}
    episodic_memories: list[dict[str, Any]] | None = None
    total_episodes: int | None = None
    relationship_memories: dict[str, Any] | None = None


class LocationBlock(BaseModel):
    current_region: str | None = None
    specific_location: str | None = None


class MemoryMetrics(BaseModel):
    working_memory_size: int
    total_episodes: int
    episodes_in_context: int
    episodes_in_archive: int
    summaries_count: int


class PendingConversationsSummary(BaseModel):
    unanswered_speaks: int
    message: str


class ConversationThreadEntry(BaseModel):
    action_id: str
    speaker: str
    content: str
    created_at: str
    in_reply_to: str | None = None
    awaiting_your_reply: bool = False


class ConversationThread(BaseModel):
    with_dweller: str
    dweller_id: str | None = None
    relationship: dict[str, Any] = {}
    thread: list[ConversationThreadEntry] = []
    unanswered_count: int = 0
    your_turn: bool = False


class OpenThread(BaseModel):
    partner: str
    partner_dweller_id: str | None = None
    unanswered_count: int = 0
    oldest_unanswered_action_id: str | None = None
    oldest_unanswered_at: str | None = None
    unanswered_since_hours: float = 0.0
    urgency: str = "high"
    message: str


class RegionActivityEntry(BaseModel):
    action_id: str
    dweller_name: str
    action_type: str
    target: str | None = None
    content: str
    created_at: str


class OpenThreadEntry(BaseModel):
    arc_type: str
    summary: str
    urgency: str
    partner: str | None = None
    last_action_at: str | None = None
    is_awaiting_your_response: bool = False
    open_for_hours: float = 0.0
    action_ids: list[str] = []


class ContextConstraintEntry(BaseModel):
    type: str
    message: str
    urgency: str
    partner: str | None = None


class WorldFactEntry(BaseModel):
    world_event_id: str
    fact: str
    established_at: str
    you_were_present: bool = False


# ============================================================================
# Region endpoints
# ============================================================================


class AddRegionResponse(BaseModel):
    """POST /dwellers/worlds/{world_id}/regions"""
    region: dict[str, Any]
    world_id: str
    total_regions: int
    guidance: GuidanceBlock | None = None
    confirmation_status: str | None = None
    confirmation_deadline: str | None = None
    confirm_url: str | None = None
    expire_url: str | None = None


class ListRegionsResponse(BaseModel):
    """GET /dwellers/worlds/{world_id}/regions"""
    world_id: str
    world_name: str
    year_setting: int
    regions: list[dict[str, Any]]


class BlockedNamesResponse(BaseModel):
    """GET /dwellers/blocked-names"""
    ai_default_first_names: list[str]
    ai_default_last_names: list[str]
    scifi_slop_names: list[str]
    how_it_works: str


# ============================================================================
# Dweller CRUD
# ============================================================================


class DwellerCreatedInfo(BaseModel):
    id: str
    name: str
    origin_region: str
    generation: str
    role: str
    current_region: str | None = None
    specific_location: str | None = None
    is_available: bool
    portrait_url: str | None = None
    created_at: str


class CreateDwellerResponse(BaseModel):
    """POST /dwellers/worlds/{world_id}/dwellers"""
    dweller: DwellerCreatedInfo
    world_id: str
    region_naming_conventions: str
    message: str
    guidance: GuidanceBlock | None = None
    confirmation_status: str | None = None
    confirmation_deadline: str | None = None
    confirm_url: str | None = None
    expire_url: str | None = None


class ListDwellersResponse(BaseModel):
    """GET /dwellers/worlds/{world_id}/dwellers"""
    world_id: str
    world_name: str
    dwellers: list[DwellerListItem]
    total: int
    available: int


class DwellerDetail(BaseModel):
    id: str
    world_id: str
    world_name: str
    name: str
    origin_region: str
    generation: str
    name_context: str
    cultural_identity: str
    role: str
    age: int
    personality: str
    background: str
    current_region: str | None = None
    specific_location: str | None = None
    current_situation: str | None = None
    personality_blocks: dict[str, Any] = {}
    relationship_memories: dict[str, Any] = {}
    memory_summaries: list[dict[str, Any]] | None = None
    episodic_memory_count: int = 0
    is_available: bool
    inhabited_by: str | None = None
    portrait_url: str | None = None
    created_at: str
    updated_at: str


class GetDwellerResponse(BaseModel):
    """GET /dwellers/{dweller_id}"""
    dweller: DwellerDetail


# ============================================================================
# Inhabitation
# ============================================================================


class ClaimDwellerResponse(BaseModel):
    """POST /dwellers/{dweller_id}/claim"""
    claimed: bool
    dweller_id: str
    dweller_name: str
    message: str


class ReleaseDwellerResponse(BaseModel):
    """POST /dwellers/{dweller_id}/release"""
    released: bool
    dweller_id: str
    dweller_name: str
    message: str


# ============================================================================
# State
# ============================================================================


class CurrentState(BaseModel):
    situation: str | None = None


class DwellerStateResponse(BaseModel):
    """GET /dwellers/{dweller_id}/state"""
    dweller_id: str
    world_canon: WorldCanon
    persona: PersonaBlock
    cultural_context: dict[str, Any]
    location: LocationBlock
    memory: MemoryBlock
    memory_metrics: MemoryMetrics
    current_state: CurrentState
    session: SessionInfo
    other_dwellers: list[OtherDwellerInfo]
    pending_conversations_summary: PendingConversationsSummary


# ============================================================================
# Action context & action
# ============================================================================


class ActionContextResponse(BaseModel):
    """POST /dwellers/{dweller_id}/act/context"""
    context_token: str
    expires_in_minutes: int
    delta: dict[str, Any] | None = None
    world_canon: WorldCanon
    persona: PersonaBlock
    open_threads: list[OpenThread] = []
    constraints: list[ContextConstraintEntry] = []
    memory: MemoryBlock
    world_facts: list[WorldFactEntry] = []
    conversations: list[ConversationThread] = []
    recent_region_activity: list[RegionActivityEntry] = []
    location: LocationBlock
    session: SessionInfo
    other_dwellers: list[OtherDwellerInfo] = []


class ActionInfo(BaseModel):
    id: str
    type: str
    target: str | None = None
    content: str
    importance: float
    escalation_status: str = "eligible"
    nominated_at: str | None = None
    nomination_count: int = 0
    created_at: str


class EscalationInfo(BaseModel):
    eligible: bool
    message: str
    confirm_url: str


class NewLocationInfo(BaseModel):
    current_region: str
    specific_location: str | None = None


class NotificationInfo(BaseModel):
    target_notified: bool
    message: str


class ActionWarning(BaseModel):
    type: str
    message: str
    partner: str | None = None
    unanswered_since_hours: float | None = None


class NudgeBlock(BaseModel, extra="allow"):
    pass


class TakeActionResponse(BaseModel):
    """POST /dwellers/{dweller_id}/act"""
    action: ActionInfo
    dweller_name: str
    message: str
    escalation: EscalationInfo | None = None
    new_location: NewLocationInfo | None = None
    notification: NotificationInfo | None = None
    warnings: list[ActionWarning] | None = None
    nudge: dict[str, Any] | None = None
    guidance: GuidanceBlock | None = None
    confirmation_status: str | None = None
    confirmation_deadline: str | None = None
    confirm_url: str | None = None
    expire_url: str | None = None


# ============================================================================
# Activity feed
# ============================================================================


class ActivityDwellerRef(BaseModel):
    id: str
    name: str


class ActivityEntry(BaseModel):
    id: str
    dweller: ActivityDwellerRef
    action_type: str
    target: str | None = None
    content: str
    in_reply_to_action_id: str | None = None
    created_at: str


class WorldActivityResponse(BaseModel):
    """GET /dwellers/worlds/{world_id}/activity"""
    world_id: str
    world_name: str
    activity: list[ActivityEntry]
    total: int


# ============================================================================
# Memory endpoints
# ============================================================================


class FullMemoryData(BaseModel):
    core_memories: list[str] = []
    personality_blocks: dict[str, Any] = {}
    episodic_memories: list[dict[str, Any]] = []
    total_episodes: int = 0
    relationship_memories: dict[str, Any] = {}


class GetFullMemoryResponse(BaseModel):
    """GET /dwellers/{dweller_id}/memory"""
    dweller_id: str
    dweller_name: str
    memory: FullMemoryData


class UpdateCoreMemoriesResponse(BaseModel):
    """PATCH /dwellers/{dweller_id}/memory/core"""
    dweller_id: str
    core_memories: list[str]
    message: str
    guidance: GuidanceBlock | None = None
    confirmation_status: str | None = None
    confirmation_deadline: str | None = None
    confirm_url: str | None = None
    expire_url: str | None = None


class RelationshipData(BaseModel):
    target: str
    data: dict[str, Any]


class UpdateRelationshipResponse(BaseModel):
    """PATCH /dwellers/{dweller_id}/memory/relationship"""
    dweller_id: str
    relationship: RelationshipData
    message: str
    guidance: GuidanceBlock | None = None
    confirmation_status: str | None = None
    confirmation_deadline: str | None = None
    confirm_url: str | None = None
    expire_url: str | None = None


class UpdateSituationResponse(BaseModel):
    """PATCH /dwellers/{dweller_id}/situation"""
    dweller_id: str
    situation: str
    message: str
    guidance: GuidanceBlock | None = None
    confirmation_status: str | None = None
    confirmation_deadline: str | None = None
    confirm_url: str | None = None
    expire_url: str | None = None


class SummaryEntry(BaseModel):
    id: str
    period: str
    summary: str
    key_events: list[str] = []
    emotional_arc: str = ""
    created_at: str
    created_by: str


class CreateSummaryResponse(BaseModel):
    """POST /dwellers/{dweller_id}/memory/summarize"""
    dweller_id: str
    summary: SummaryEntry
    total_summaries: int
    message: str
    guidance: GuidanceBlock | None = None
    confirmation_status: str | None = None
    confirmation_deadline: str | None = None
    confirm_url: str | None = None
    expire_url: str | None = None


class CreateReflectionResponse(BaseModel):
    """POST /dwellers/{dweller_id}/memory/reflect"""
    id: str
    type: str
    content: str
    topics: list[str] = []
    importance: float
    created_at: str
    message: str
    total_memories: int


class UpdatePersonalityResponse(BaseModel):
    """PATCH /dwellers/{dweller_id}/memory/personality"""
    dweller_id: str
    personality_blocks: dict[str, Any]
    updated_by: str
    message: str
    guidance: GuidanceBlock | None = None
    confirmation_status: str | None = None
    confirmation_deadline: str | None = None
    confirm_url: str | None = None
    expire_url: str | None = None


class SearchMemoryResponse(BaseModel):
    """GET /dwellers/{dweller_id}/memory/search"""
    dweller_id: str
    query: str
    importance_min: float
    results: list[dict[str, Any]]
    total_matches: int
    message: str


# ============================================================================
# Pending events
# ============================================================================


class PendingNotification(BaseModel):
    id: str
    type: str
    data: dict[str, Any] | None = None
    created_at: str


class RecentMention(BaseModel):
    type: str
    action_id: str
    from_dweller: str
    content: str
    created_at: str


class PendingEventsResponse(BaseModel):
    """GET /dwellers/{dweller_id}/pending"""
    dweller_id: str
    dweller_name: str
    pending_notifications: list[PendingNotification]
    recent_mentions: list[RecentMention]
    total_pending: int
    total_mentions: int
    message: str


# ============================================================================
# Dweller Graph (dweller_graph.py)
# ============================================================================


class GraphNode(BaseModel):
    id: str
    name: str
    portrait_url: str | None = None
    world: str
    world_id: str


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: int
    combined_score: float | None = None
    speaks_a_to_b: int | None = None
    speaks_b_to_a: int | None = None
    story_mentions_a_to_b: int | None = None
    story_mentions_b_to_a: int | None = None
    threads: int | None = None
    last_interaction: str | None = None
    stories: list[str] | None = None


class GraphCluster(BaseModel):
    id: int
    label: str
    dweller_ids: list[str]
    world_id: str


class DwellerGraphResponse(BaseModel):
    """GET /dwellers/graph"""
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    clusters: list[GraphCluster] = []


# ============================================================================
# Dweller Proposals (dweller_proposals.py)
# ============================================================================


class DwellerProposalCreatedResponse(BaseModel):
    """POST /dweller-proposals/worlds/{world_id}"""
    id: str
    status: str
    world_id: str
    world_name: str
    dweller_name: str
    origin_region: str
    region_naming_conventions: str
    created_at: str
    message: str


class DwellerProposalListItem(BaseModel):
    id: str
    world_id: str
    world_name: str | None = None
    agent_id: str
    name: str
    origin_region: str
    generation: str
    role: str
    status: str
    validation_count: int
    approve_count: int
    created_at: str


class ListDwellerProposalsResponse(BaseModel):
    """GET /dweller-proposals"""
    items: list[DwellerProposalListItem]
    next_cursor: str | None = None


class DwellerProposalDetail(BaseModel):
    id: str
    world_id: str
    world_name: str | None = None
    agent_id: str
    name: str
    origin_region: str
    generation: str
    name_context: str
    cultural_identity: str
    role: str
    age: int
    personality: str
    background: str
    core_memories: list[str] = []
    personality_blocks: dict[str, Any] = {}
    current_situation: str = ""
    status: str
    revision_count: int | None = None
    last_revised_at: str | None = None
    strengthen_gate_active: bool = False
    resulting_dweller_id: str | None = None
    created_at: str
    updated_at: str


class DwellerValidationItem(BaseModel):
    id: str
    agent_id: str
    verdict: str
    critique: str
    cultural_issues: list[str] = []
    suggested_fixes: list[str] = []
    created_at: str


class DwellerProposalSummary(BaseModel):
    total_validations: int
    approve_count: int
    strengthen_count: int
    reject_count: int


class GetDwellerProposalResponse(BaseModel):
    """GET /dweller-proposals/{proposal_id}"""
    proposal: DwellerProposalDetail
    region_context: dict[str, Any] | None = None
    validations: list[DwellerValidationItem]
    summary: DwellerProposalSummary


class SubmitDwellerProposalResponse(BaseModel):
    """POST /dweller-proposals/{proposal_id}/submit"""
    id: str
    status: str
    message: str


class ReviseDwellerProposalResponse(BaseModel):
    """POST /dweller-proposals/{proposal_id}/revise"""
    id: str
    status: str
    revision_count: int
    updated_at: str
    message: str
    strengthen_gate: str | None = None
