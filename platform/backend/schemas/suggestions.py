"""Pydantic response schemas for revision suggestions endpoints."""

from typing import Any

from pydantic import BaseModel, Field


# --- Suggest revision ---


class SuggestionSummary(BaseModel):
    id: str
    target_type: str
    target_id: str
    field: str
    status: str
    owner_response_deadline: str
    created_at: str


class SuggestRevisionResponse(BaseModel):
    suggestion: SuggestionSummary
    message: str


# --- List suggestions ---


class SuggestionListItem(BaseModel):
    id: str
    field: str
    suggested_value: Any
    rationale: str
    status: str
    suggested_by: str
    upvotes_count: int
    owner_response_deadline: str
    created_at: str
    response_reason: str | None = None


class ListSuggestionsResponse(BaseModel):
    proposal_id: str | None = None
    aspect_id: str | None = None
    suggestions: list[SuggestionListItem]
    total: int
    pending_count: int


# --- Accept/reject suggestion ---


class AcceptSuggestionResponse(BaseModel):
    suggestion_id: str
    status: str
    accepted_by: str
    field: str
    message: str


class RejectSuggestionResponse(BaseModel):
    suggestion_id: str
    status: str
    reason: str
    message: str


# --- Upvote ---


class UpvoteSuggestionResponse(BaseModel):
    suggestion_id: str
    upvotes_count: int
    upvotes_needed_for_override: int
    can_override: bool
    message: str


# --- Withdraw ---


class WithdrawSuggestionResponse(BaseModel):
    suggestion_id: str
    status: str
    message: str


# --- Get suggestion ---


class SuggesterInfo(BaseModel):
    id: str
    name: str


class SuggestionDetail(BaseModel):
    id: str
    target_type: str
    target_id: str
    field: str
    current_value: Any
    suggested_value: Any
    rationale: str
    status: str
    suggested_by: SuggesterInfo | None = None
    upvotes_count: int
    owner_response_deadline: str
    created_at: str
    resolved_at: str | None = None
    response_reason: str | None = None


class GetSuggestionResponse(BaseModel):
    suggestion: SuggestionDetail
