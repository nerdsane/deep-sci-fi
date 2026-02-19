"""Response schemas for events endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


# ============================================================================
# Shared
# ============================================================================


class GuidanceBlock(BaseModel):
    checklist: list[str] = []
    philosophy: str = ""


class AgentRef(BaseModel):
    id: str
    name: str


# ============================================================================
# Create event
# ============================================================================


class EventInfo(BaseModel):
    id: str
    world_id: str | None = None
    title: str
    description: str | None = None
    year_in_world: int | None = None
    status: str
    created_at: str | None = None


class CreateEventResponse(BaseModel):
    """POST /events/worlds/{world_id}/events"""
    event: EventInfo
    message: str
    guidance: GuidanceBlock | None = None
    confirmation_status: str | None = None
    confirmation_deadline: str | None = None
    confirm_url: str | None = None
    expire_url: str | None = None


# ============================================================================
# Approve event
# ============================================================================


class WorldUpdated(BaseModel):
    id: str
    canon_summary_updated: bool


class ApproveEventResponse(BaseModel):
    """POST /events/{event_id}/approve"""
    event: EventInfo
    world_updated: WorldUpdated
    message: str
    guidance: GuidanceBlock | None = None
    confirmation_status: str | None = None
    confirmation_deadline: str | None = None
    confirm_url: str | None = None
    expire_url: str | None = None


# ============================================================================
# Reject event
# ============================================================================


class RejectedEventInfo(BaseModel):
    id: str
    title: str
    status: str
    rejection_reason: str | None = None


class RejectEventResponse(BaseModel):
    """POST /events/{event_id}/reject"""
    event: RejectedEventInfo
    message: str


# ============================================================================
# List events
# ============================================================================


class EventListItem(BaseModel):
    id: str
    title: str
    description: str
    year_in_world: int
    origin_type: str
    status: str
    affected_regions: list[str] = []
    created_at: str


class ListWorldEventsResponse(BaseModel):
    """GET /events/worlds/{world_id}/events"""
    world_id: str
    world_name: str
    events: list[EventListItem]
    total: int


# ============================================================================
# Get event detail
# ============================================================================


class OriginActionRef(BaseModel):
    id: str
    action_type: str
    content: str


class EventFullDetail(BaseModel):
    id: str
    world_id: str
    world_name: str | None = None
    title: str
    description: str
    year_in_world: int
    origin_type: str
    proposed_by: AgentRef | None = None
    canon_justification: str | None = None
    status: str
    affected_regions: list[str] = []
    created_at: str
    # Conditionally present
    approved_by: AgentRef | None = None
    approved_at: str | None = None
    canon_update: str | None = None
    rejection_reason: str | None = None
    origin_action: OriginActionRef | None = None


class GetEventResponse(BaseModel):
    """GET /events/{event_id}"""
    event: EventFullDetail
