"""Response schemas for actions endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


# ============================================================================
# Shared
# ============================================================================


class AgentRef(BaseModel):
    id: str
    name: str


# ============================================================================
# Get action
# ============================================================================


class ImportanceConfirmation(BaseModel):
    confirmed_by: AgentRef | None = None
    confirmed_at: str | None = None
    rationale: str | None = None


class EscalatedEventRef(BaseModel):
    id: str
    title: str


class ActionDetail(BaseModel):
    id: str
    dweller_id: str
    dweller_name: str | None = None
    actor: AgentRef | None = None
    action_type: str
    target: str | None = None
    content: str
    importance: float
    escalation_eligible: bool
    escalation_status: str
    nominated_at: str | None = None
    nomination_count: int = 0
    created_at: str
    importance_confirmed: ImportanceConfirmation | None = None
    escalated_to_event: EscalatedEventRef | None = None


class GetActionResponse(BaseModel):
    """GET /actions/{action_id}"""
    action: ActionDetail


# ============================================================================
# Confirm importance
# ============================================================================


class ConfirmedActionInfo(BaseModel):
    id: str
    importance: float
    escalation_eligible: bool
    escalation_status: str
    importance_confirmed: bool


class ConfirmImportanceResponse(BaseModel):
    """POST /actions/{action_id}/confirm-importance"""
    action: ConfirmedActionInfo
    confirmed_by: str
    message: str
    escalate_url: str


# ============================================================================
# Escalate to event
# ============================================================================


class EscalatedEventInfo(BaseModel):
    id: str
    world_id: str
    title: str
    description: str
    year_in_world: int
    origin_type: str
    status: str
    created_at: str


class OriginActionSummary(BaseModel):
    id: str
    dweller_name: str
    content: str


class EscalateToEventResponse(BaseModel):
    """POST /actions/{action_id}/escalate"""
    event: EscalatedEventInfo
    origin_action: OriginActionSummary
    message: str


# ============================================================================
# List escalation-eligible
# ============================================================================


class EscalationEligibleAction(BaseModel):
    id: str
    dweller_name: str | None = None
    actor_name: str | None = None
    action_type: str
    content: str
    importance: float
    importance_confirmed: bool
    escalation_status: str
    nominated_at: str | None = None
    nomination_count: int = 0
    confirmed_by: str | None = None
    created_at: str
    confirm_url: str | None = None
    escalate_url: str | None = None


class EscalationPagination(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool


class ListEscalationEligibleResponse(BaseModel):
    """GET /actions/worlds/{world_id}/escalation-eligible"""
    world_id: str
    world_name: str
    actions: list[EscalationEligibleAction]
    pagination: EscalationPagination


# ============================================================================
# Nominate action
# ============================================================================


class NominateActionResponse(BaseModel):
    """POST /actions/{action_id}/nominate"""

    success: bool
    action_id: str
    escalation_status: str
    nomination_count: int
    nominated_at: str
    message: str
