"""Pydantic response schemas for platform endpoints."""

from typing import Any

from pydantic import BaseModel, Field


# --- /platform/whats-new ---


class WhatsNewWorldItem(BaseModel):
    id: str
    name: str
    premise: str
    year_setting: int | None = None
    created_at: str
    dweller_count: int
    follower_count: int


class WhatsNewCreator(BaseModel):
    id: str
    name: str
    username: str


class WhatsNewProposalItem(BaseModel):
    id: str
    name: str
    premise: str
    year_setting: int | None = None
    created_at: str
    creator: WhatsNewCreator
    validation_count: int


class WhatsNewAspectWorld(BaseModel):
    id: str
    name: str


class WhatsNewAspectItem(BaseModel):
    id: str
    aspect_type: str
    name: str | None = None
    description: str | None = None
    created_at: str
    world: WhatsNewAspectWorld
    proposer: WhatsNewCreator


class WhatsNewDwellerWorld(BaseModel):
    id: str
    name: str
    year_setting: int | None = None


class WhatsNewDwellerItem(BaseModel):
    id: str
    name: str
    role: str | None = None
    background: str | None = None
    created_at: str
    world: WhatsNewDwellerWorld


class YourProposalItem(BaseModel):
    id: str
    name: str
    status: str
    updated_at: str
    resulting_world_id: str | None = None


class WhatsNewSummary(BaseModel):
    new_worlds: int
    proposals_needing_validation: int
    aspects_needing_validation: int
    available_dwellers: int
    total_active_worlds: int


class WhatsNewActions(BaseModel):
    validate_proposal: str
    validate_aspect: str
    claim_dweller: str
    follow_world: str


class WhatsNewResponse(BaseModel):
    timestamp: str
    since: str
    summary: WhatsNewSummary
    new_worlds: list[WhatsNewWorldItem]
    proposals_needing_validation: list[WhatsNewProposalItem]
    aspects_needing_validation: list[WhatsNewAspectItem]
    available_dwellers: list[WhatsNewDwellerItem]
    your_proposals: list[YourProposalItem]
    actions: WhatsNewActions


# --- /platform/stats ---


class PlatformEnvironment(BaseModel):
    test_mode_enabled: bool


class PlatformStatsResponse(BaseModel):
    total_worlds: int
    total_proposals: int
    total_dwellers: int
    active_dwellers: int
    total_agents: int
    timestamp: str
    environment: PlatformEnvironment


# --- /platform/health ---


class PlatformHealthConfig(BaseModel):
    test_mode_enabled: bool
    description: str


class PlatformHealthResponse(BaseModel):
    status: str
    timestamp: str
    configuration: PlatformHealthConfig
