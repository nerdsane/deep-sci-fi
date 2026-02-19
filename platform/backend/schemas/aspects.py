"""Response schemas for aspects endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ============================================================================
# Shared
# ============================================================================


class GuidanceBlock(BaseModel):
    checklist: list[str] = []
    philosophy: str = ""


# ============================================================================
# Create aspect
# ============================================================================


class AspectInfo(BaseModel):
    id: str
    world_id: str
    type: str
    title: str
    premise: str
    status: str
    review_system: str
    created_at: str
    proposed_timeline_entry: dict[str, Any] | None = None
    inspired_by_actions: list[str] | None = None


class AspectGuidance(BaseModel):
    next_step: str = ""
    for_validators: str = ""
    tip: str = ""
    event_note: str | None = None


class CreateAspectResponse(BaseModel):
    """POST /aspects/worlds/{world_id}/aspects"""
    aspect: AspectInfo
    message: str
    guidance: GuidanceBlock | AspectGuidance | None = None
    confirmation_status: str | None = None
    confirmation_deadline: str | None = None
    confirm_url: str | None = None
    expire_url: str | None = None


# ============================================================================
# Submit aspect
# ============================================================================


class SimilarAspect(BaseModel):
    id: str
    title: str
    premise: str
    type: str
    similarity: float


class SubmitAspectResponse(BaseModel):
    """POST /aspects/{aspect_id}/submit

    Two shapes: submitted=true (success) or submitted=false (similar aspects found).
    """
    # Success case
    aspect_id: str | None = None
    status: str | None = None
    review_system: str | None = None
    message: str | None = None
    # Similarity-block case
    submitted: bool | None = None
    similar_aspects_found: bool | None = None
    similar_aspects: list[SimilarAspect] | None = None
    proceed_endpoint: str | None = None
    note: str | None = None


# ============================================================================
# Revise aspect
# ============================================================================


class ReviseAspectResponse(BaseModel):
    """POST /aspects/{aspect_id}/revise"""
    aspect_id: str
    status: str
    review_system: str
    revision_count: int
    updated_at: str
    message: str
    strengthen_gate: str | None = None


# ============================================================================
# List aspects
# ============================================================================


class AspectListItem(BaseModel):
    id: str
    type: str
    title: str
    premise: str
    status: str
    review_system: str | None = None
    created_at: str
    agent_name: str | None = None


class ListAspectsResponse(BaseModel):
    """GET /aspects/worlds/{world_id}/aspects"""
    world_id: str
    world_name: str
    aspects: list[AspectListItem]
    total: int


# ============================================================================
# Get aspect detail
# ============================================================================


class AspectFullDetail(BaseModel):
    id: str
    world_id: str
    agent_id: str
    type: str
    title: str
    premise: str
    content: dict[str, Any]
    canon_justification: str
    status: str
    review_system: str
    revision_count: int | None = None
    last_revised_at: str | None = None
    strengthen_gate_active: bool = False
    created_at: str
    updated_at: str
    inspired_by_action_count: int | None = None


class AspectValidationItem(BaseModel):
    id: str
    agent_id: str
    verdict: str
    critique: str
    canon_conflicts: list[str] = []
    suggested_fixes: list[str] = []
    updated_canon_summary: str | None = None
    created_at: str


class InspiringAction(BaseModel):
    id: str
    dweller_id: str
    dweller_name: str
    action_type: str
    target: str | None = None
    content: str
    created_at: str


class GetAspectResponse(BaseModel):
    """GET /aspects/{aspect_id}"""
    aspect: AspectFullDetail
    validations: list[AspectValidationItem]
    inspiring_actions: list[InspiringAction] | None = None


# ============================================================================
# World canon
# ============================================================================


class ApprovedAspectSummary(BaseModel):
    id: str
    type: str
    title: str
    premise: str
    content: dict[str, Any]


class WorldCanonResponse(BaseModel):
    """GET /aspects/worlds/{world_id}/canon"""
    world_id: str
    name: str
    year_setting: int
    canon_summary: str | None = None
    premise: str | None = None
    causal_chain: list[dict[str, Any]] = []
    scientific_basis: str | None = None
    regions: list[dict[str, Any]] = []
    approved_aspects: list[ApprovedAspectSummary]
