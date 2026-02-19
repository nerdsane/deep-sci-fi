"""Pydantic response schemas for story arcs endpoints."""

from typing import Any

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


class ListArcsResponse(BaseModel):
    arcs: list[dict[str, Any]]
    count: int
    filters: ArcFilters
    pagination: ArcPagination


# --- Detect arcs (admin) ---


class DetectArcsResponse(BaseModel):
    message: str
    arcs: list[dict[str, Any]]
