"""Pydantic response schemas for media generation endpoints."""

from typing import Any

from pydantic import BaseModel, Field


# --- Generate cover image / video ---


class GenerateMediaResponse(BaseModel):
    generation_id: str
    status: str
    poll_url: str
    estimated_seconds: int
    estimated_cost_usd: float | None = None
    message: str


# --- Generation status ---


class GenerationStatusResponse(BaseModel):
    generation_id: str
    status: str
    target_type: str
    target_id: str
    media_type: str
    created_at: str
    media_url: str | None = None
    cost_usd: float | None = None
    completed_at: str | None = None
    file_size_bytes: int | None = None
    duration_seconds: float | None = None
    error_message: str | None = None
    retry_count: int | None = None
    started_at: str | None = None
    message: str | None = None


# --- Budget ---
# Budget response is dynamic (comes from cost_control.get_budget_summary).
# We type it as dict[str, Any] via response_model usage.
