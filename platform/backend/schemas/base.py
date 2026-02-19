"""Base response models used across multiple API modules."""

from pydantic import BaseModel, Field


class PaginatedResponse(BaseModel):
    """Base for offset-paginated list responses."""

    total: int = Field(description="Total number of items matching the query")
    has_more: bool = Field(description="Whether more items exist beyond this page")


class CursorPaginatedResponse(BaseModel):
    """Base for cursor-paginated list responses (feed-style)."""

    next_cursor: str | None = Field(None, description="Cursor for fetching the next page")
    has_more: bool = Field(description="Whether more items exist beyond this page")


class StatusResponse(BaseModel):
    """Generic success/status response."""

    success: bool = True
    message: str | None = None
