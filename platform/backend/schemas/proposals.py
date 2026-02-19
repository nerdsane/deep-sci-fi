"""Pydantic response schemas for proposals API endpoints."""

from typing import Any

from pydantic import BaseModel, Field



# -- Shared nested models --


class ProposalListItem(BaseModel):
    """Single proposal in list view."""

    id: str
    agent_id: str
    name: str | None = None
    premise: str
    year_setting: int
    causal_chain: list[dict] | None = None
    scientific_basis: str | None = None
    citations: list[dict] | None = None
    status: str
    review_system: str = "LEGACY"
    validation_count: int = 0
    approve_count: int = 0
    reject_count: int = 0
    created_at: str
    updated_at: str


class ProposalDetail(BaseModel):
    """Full proposal detail nested in get_proposal response."""

    id: str
    name: str | None = None
    premise: str
    year_setting: int
    causal_chain: list[dict] | None = None
    scientific_basis: str | None = None
    citations: list[dict] | None = None
    status: str
    review_system: str
    revision_count: int = 0
    last_revised_at: str | None = None
    strengthen_gate_active: bool = False
    created_at: str
    updated_at: str
    resulting_world_id: str | None = None


class ValidationDetail(BaseModel):
    """Single validation in proposal detail."""

    id: str
    agent_id: str
    validator: dict | None = None
    verdict: str
    critique: str
    research_conducted: str
    scientific_issues: list[str] = []
    suggested_fixes: list[str] = []
    weaknesses: list[str] | None = None
    created_at: str


class ValidationSummary(BaseModel):
    """Validation summary counts (may be hidden in blind mode)."""

    total_validations: int | str
    approve_count: int | str
    strengthen_count: int | str
    reject_count: int | str


class ValidationProgress(BaseModel):
    """Progress toward approval threshold."""

    approvals_received: int
    approvals_needed: int
    remaining: int
    queue_position: int


class ProposalAgent(BaseModel):
    """Proposer agent info."""

    id: str
    name: str


# -- Endpoint response models --


class ProposalSearchResponse(BaseModel):
    """GET /proposals/search"""

    query: str
    status_filter: str | None = None
    results: list[dict]
    count: int


class GuidanceBlock(BaseModel):
    """Guidance block appended by make_guidance_response."""

    checklist: list[str]
    philosophy: str


class ProposalCreateResponse(BaseModel):
    """POST /proposals — wrapped by make_guidance_response."""

    id: str
    status: str
    review_system: str
    created_at: str
    message: str
    guidance: GuidanceBlock | None = None
    confirmation_status: str | None = None
    confirmation_deadline: str | None = None


class ProposalListResponse(BaseModel):
    """GET /proposals"""

    items: list[ProposalListItem]
    next_cursor: str | None = None


class ProposalGetResponse(BaseModel):
    """GET /proposals/{proposal_id}"""

    proposal: ProposalDetail
    agent: ProposalAgent | None = None
    validations: list[ValidationDetail | dict]
    summary: ValidationSummary
    blind_mode: bool = False
    blind_mode_reason: str | None = None
    validation_progress: ValidationProgress | None = None


class SimilarContentResponse(BaseModel):
    """Returned by submit when similar content found (submitted=false)."""

    submitted: bool = False
    similar_content_found: bool = True
    message: str
    similar_proposals: list[dict] = []
    similar_worlds: list[dict] = []
    proceed_endpoint: str
    note: str


class ProposalSubmitResponse(BaseModel):
    """POST /proposals/{proposal_id}/submit — wrapped by make_guidance_response."""

    id: str
    status: str
    review_system: str
    message: str
    guidance: GuidanceBlock | None = None
    confirmation_status: str | None = None
    confirmation_deadline: str | None = None


class ProposalReviseResponse(BaseModel):
    """POST /proposals/{proposal_id}/revise — wrapped by make_guidance_response."""

    id: str
    status: str
    review_system: str
    revision_count: int
    updated_at: str
    message: str
    strengthen_gate: str | None = None
    guidance: GuidanceBlock | None = None
    confirmation_status: str | None = None
    confirmation_deadline: str | None = None
