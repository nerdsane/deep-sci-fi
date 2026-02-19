"""Pydantic response schemas for critical review system endpoints."""

from typing import Any

from pydantic import BaseModel, Field


# --- Submit review ---


class ReviewFeedbackItemOut(BaseModel):
    id: str
    category: str
    severity: str
    description: str
    status: str


class SubmitReviewResponse(BaseModel):
    review_id: str
    message: str
    feedback_items: list[ReviewFeedbackItemOut]


# --- Get reviews ---


class FeedbackResponseOut(BaseModel):
    id: str
    responder_id: str
    response_text: str
    created_at: str


class ReviewFeedbackItemDetail(BaseModel):
    id: str
    category: str
    severity: str
    description: str
    status: str
    created_at: str
    resolution_note: str | None = None
    resolved_at: str | None = None
    responses: list[FeedbackResponseOut] | None = None


class ReviewOut(BaseModel):
    review_id: str
    reviewer_id: str
    created_at: str
    feedback_items: list[ReviewFeedbackItemDetail]


class GetReviewsResponse(BaseModel):
    blind_mode: bool
    reviews: list[ReviewOut]
    total_reviewers: int | None = None
    message: str | None = None


# --- Respond to feedback ---


class RespondToFeedbackResponse(BaseModel):
    response_id: str
    item_id: str
    new_status: str
    message: str


# --- Resolve feedback ---


class GraduationInfo(BaseModel):
    graduated: bool
    world_id: str
    world_name: str


class ResolveFeedbackResponse(BaseModel):
    item_id: str
    status: str
    resolved_at: str
    message: str
    graduation: GraduationInfo | None = None


# --- Reopen feedback ---


class ReopenFeedbackResponse(BaseModel):
    item_id: str
    status: str
    message: str


# --- Add feedback ---


class AddFeedbackResponse(BaseModel):
    review_id: str
    message: str
    new_items: list[ReviewFeedbackItemOut]


# --- Graduation status ---


class FeedbackItemCounts(BaseModel):
    total: int
    by_status: dict[str, int]


class GraduationStatusResponse(BaseModel):
    content_type: str
    content_id: str
    reviewer_count: int
    min_reviewers: int
    feedback_items: FeedbackItemCounts
    can_graduate: bool
    graduation_status: str
