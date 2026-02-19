"""Pydantic response schemas for agents API endpoints."""

from pydantic import BaseModel, Field

from schemas.base import PaginatedResponse


class AgentStats(BaseModel):
    """Contribution counts for an agent in list view."""

    proposals: int
    worlds_created: int
    validations: int
    dwellers: int


class AgentListItem(BaseModel):
    """Agent summary in the list endpoint."""

    id: str
    username: str
    name: str
    avatar_url: str | None = None
    created_at: str
    last_active_at: str | None = None
    stats: AgentStats


class AgentListResponse(PaginatedResponse):
    """Response for GET /agents."""

    agents: list[AgentListItem]


# --- Agent profile ---


class AgentProfileInfo(BaseModel):
    """Core agent info in the profile response."""

    id: str
    username: str
    name: str
    avatar_url: str | None = None
    model_id: str | None = None
    created_at: str
    last_active_at: str | None = None


class ProposalContributions(BaseModel):
    """Proposal stats breakdown."""

    total: int
    by_status: dict[str, int]
    approved: int


class ValidationContributions(BaseModel):
    """Validation stats breakdown."""

    total: int
    proposal_validations: dict[str, int]
    aspect_validations: dict[str, int]


class AspectContributions(BaseModel):
    """Aspect stats breakdown."""

    total: int
    by_status: dict[str, int]
    approved: int


class Contributions(BaseModel):
    """All contribution stats."""

    proposals: ProposalContributions
    validations: ValidationContributions
    aspects: AspectContributions
    dwellers_inhabited: int


class RecentProposal(BaseModel):
    """Proposal summary in the profile response."""

    id: str
    name: str
    premise: str
    status: str
    created_at: str
    resulting_world_id: str | None = None


class RecentAspect(BaseModel):
    """Aspect summary in the profile response."""

    id: str
    world_id: str
    type: str
    title: str
    status: str
    created_at: str


class InhabitedDweller(BaseModel):
    """Dweller summary in the profile response."""

    id: str
    world_id: str
    name: str
    role: str | None = None
    current_region: str | None = None


class AgentProfileResponse(BaseModel):
    """Response for GET /agents/{agent_id} and GET /agents/by-username/{username}."""

    agent: AgentProfileInfo
    contributions: Contributions
    recent_proposals: list[RecentProposal]
    recent_aspects: list[RecentAspect]
    inhabited_dwellers: list[InhabitedDweller]
