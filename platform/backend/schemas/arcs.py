"""Pydantic response schemas for story arcs endpoints."""

from typing import Literal

from pydantic import BaseModel, Field


# --- Query model for GET /arcs ---


class ArcListQuery(BaseModel):
    """Query parameters for arc listing."""

    world_id: str | None = None
    dweller_id: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


# --- List arcs ---


class ArcFilters(BaseModel):
    world_id: str | None = None
    dweller_id: str | None = None


class ArcPagination(BaseModel):
    limit: int
    offset: int


ArcMomentum = Literal["heating_up", "active", "stalling", "concluded"]


class ArcStoryRef(BaseModel):
    id: str
    title: str


class ArcListItem(BaseModel):
    id: str
    name: str
    world_id: str
    world_name: str
    dweller_id: str | None
    dweller_name: str | None
    story_count: int
    story_ids: list[str]
    stories: list[ArcStoryRef]
    created_at: str
    updated_at: str
    momentum: ArcMomentum
    days_since_last_story: int = Field(ge=0)
    arc_health_score: float = Field(ge=0.0, le=1.0)
    summary: str | None = None


class ListArcsResponse(BaseModel):
    arcs: list[ArcListItem]
    count: int
    filters: ArcFilters
    pagination: ArcPagination


# --- Arc detail ---


class ArcDetailStory(BaseModel):
    id: str
    title: str
    summary: str | None = None
    created_at: str
    cover_image_url: str | None = None
    thumbnail_url: str | None = None


class ArcDetailItem(BaseModel):
    id: str
    name: str
    world_id: str
    world_name: str
    dweller_id: str | None
    dweller_name: str | None
    story_count: int
    story_ids: list[str]
    stories: list[ArcDetailStory]
    created_at: str
    updated_at: str
    momentum: ArcMomentum
    days_since_last_story: int = Field(ge=0)
    arc_health_score: float = Field(ge=0.0, le=1.0)
    summary: str | None = None


class ArcDetailResponse(BaseModel):
    arc: ArcDetailItem


# --- Detect arcs (admin) ---


class DetectArcsResponse(BaseModel):
    message: str
    arcs: list[dict[str, str | int]]
