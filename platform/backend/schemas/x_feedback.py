"""Pydantic response schemas for X feedback endpoints."""

from typing import Any

from pydantic import BaseModel, Field


# --- Query model for GET /x-feedback/stories/{story_id} ---


class ExternalFeedbackQuery(BaseModel):
    """Query parameters for external feedback listing."""

    source: str | None = None
    feedback_type: str | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


# --- External feedback item ---


class ExternalFeedbackItem(BaseModel):
    id: str
    source: str
    source_post_id: str | None = None
    source_user: str | None = None
    feedback_type: str
    content: str | None = None
    sentiment: str | None = None
    weight: float | None = None
    is_human: bool | None = None
    created_at: str


class StoryExternalFeedbackResponse(BaseModel):
    story_id: str
    x_post_id: str | None = None
    feedback: list[ExternalFeedbackItem]
    count: int


# --- Feedback summary ---


class FeedbackTypeCounts(BaseModel):
    reply: int = 0
    quote: int = 0
    like: int = 0
    bookmark: int = 0


class SentimentBreakdown(BaseModel):
    positive: int = 0
    negative: int = 0
    neutral: int = 0
    constructive: int = 0


class TopFeedbackExcerpt(BaseModel):
    source_user: str | None = None
    feedback_type: str
    content: str | None = None
    sentiment: str | None = None


class StoryFeedbackSummaryResponse(BaseModel):
    story_id: str
    x_post_id: str | None = None
    x_published_at: str | None = None
    type_counts: FeedbackTypeCounts
    sentiment_breakdown: SentimentBreakdown
    total_engagement_weight: float
    top_feedback: list[TopFeedbackExcerpt]
