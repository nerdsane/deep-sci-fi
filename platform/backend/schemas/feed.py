"""Pydantic response schemas for feed endpoints."""

from typing import Any

from pydantic import BaseModel, Field


class FeedResponse(BaseModel):
    """Top-level response for GET /feed. Feed items stay as dicts (17 polymorphic types)."""

    items: list[dict[str, Any]] = Field(description="List of feed items (polymorphic types)")
    next_cursor: str | None = Field(None, description="Cursor for next page (ISO timestamp)")
