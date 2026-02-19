"""Pydantic response schemas for stories API endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from db import StoryPerspective, StoryStatus


# -- Reusable models (moved from api/stories.py) --


class SourceEventSummary(BaseModel):
    """Summary of a referenced world event."""

    id: str
    title: str


class SourceActionSummary(BaseModel):
    """Summary of a referenced dweller action."""

    id: str
    action_type: str
    dweller_name: str


class StoryResponse(BaseModel):
    """Story response for list views."""

    id: UUID
    world_id: UUID
    world_name: str
    author_id: UUID
    author_name: str
    author_username: str
    title: str
    summary: str | None
    perspective: StoryPerspective
    perspective_dweller_name: str | None
    cover_image_url: str | None = None
    video_url: str | None = None
    thumbnail_url: str | None = None
    x_post_id: str | None = None
    status: StoryStatus
    review_system: str = "LEGACY"
    reaction_count: int
    comment_count: int
    created_at: datetime


class StoryDetailResponse(BaseModel):
    """Full story details including content."""

    id: UUID
    world_id: UUID
    world_name: str
    world_year_setting: int
    author_id: UUID
    author_name: str
    author_username: str
    title: str
    content: str
    summary: str | None
    perspective: StoryPerspective
    perspective_dweller_id: UUID | None
    perspective_dweller_name: str | None
    cover_image_url: str | None = None
    video_url: str | None = None
    thumbnail_url: str | None = None
    x_post_id: str | None = None
    x_published_at: datetime | None = None
    source_event_ids: list[str]
    source_action_ids: list[str]
    source_events: list[SourceEventSummary]
    source_actions: list[SourceActionSummary]
    time_period_start: str | None
    time_period_end: str | None
    status: StoryStatus
    review_count: int
    acclaim_count: int
    reaction_count: int
    comment_count: int
    revision_count: int
    last_revised_at: datetime | None
    created_at: datetime
    updated_at: datetime


class StoryReviewResponse(BaseModel):
    """Response model for a story review."""

    id: UUID
    story_id: UUID
    reviewer_id: UUID
    reviewer_name: str
    reviewer_username: str
    recommend_acclaim: bool
    improvements: list[str]
    canon_notes: str
    event_notes: str
    style_notes: str
    canon_issues: list[str]
    event_issues: list[str]
    style_issues: list[str]
    created_at: datetime
    author_responded: bool
    author_response: str | None
    author_responded_at: datetime | None


# -- Endpoint response models --


class VideoGenerationInfo(BaseModel):
    """Inline video generation status."""

    generation_id: str
    status: str
    poll_url: str
    message: str


class StoryCreateResponseStory(BaseModel):
    """Inline story data in creation response."""

    id: str
    world_id: str
    world_name: str
    title: str
    perspective: str
    perspective_dweller_name: str | None
    status: str
    review_system: str
    created_at: str


class StoryCreateResponse(BaseModel):
    """POST /stories"""

    success: bool
    story: StoryCreateResponseStory
    video_generation: VideoGenerationInfo
    message: str
    nudge: Any = None


class StoryListFilters(BaseModel):
    """Filter summary echoed in list responses."""

    world_id: str | None = None
    author_id: str | None = None
    perspective: str | None = None
    status: str | None = None
    sort: str


class StoryListResponse(BaseModel):
    """GET /stories"""

    stories: list[dict]
    count: int
    filters: StoryListFilters


class AcclaimEligibility(BaseModel):
    """Acclaim eligibility info."""

    eligible: bool
    reason: str


class ExternalFeedbackExcerpt(BaseModel):
    """Single external feedback excerpt."""

    source_user: str | None = None
    type: str | None = None
    content: str | None = None
    sentiment: str | None = None


class ExternalFeedbackSummary(BaseModel):
    """External feedback summary from X."""

    x_post_id: str
    reply_count: int = 0
    quote_count: int = 0
    like_count: int = 0
    top_feedback: list[ExternalFeedbackExcerpt] = []


class StoryGetResponse(BaseModel):
    """GET /stories/{story_id}"""

    story: dict
    acclaim_eligibility: AcclaimEligibility
    external_feedback_summary: ExternalFeedbackSummary | None = None


class StoryArcResponse(BaseModel):
    """GET /stories/{story_id}/arc"""

    arc: dict | None = None


class WorldStoriesWorldInfo(BaseModel):
    """Inline world summary for world-stories endpoint."""

    id: str
    name: str
    year_setting: int | None = None


class WorldStoriesResponse(BaseModel):
    """GET /stories/worlds/{world_id}"""

    world: WorldStoriesWorldInfo
    stories: list[dict]
    count: int
    sort: str
    status_filter: str | None = None


class StoryReactResponse(BaseModel):
    """POST /stories/{story_id}/react"""

    action: str
    reaction_type: str | None = None
    from_type: str | None = None
    to_type: str | None = None
    new_reaction_count: int


class ReviewSummary(BaseModel):
    """Inline review data in review creation response."""

    id: str
    story_id: str
    recommend_acclaim: bool
    improvements: list[str]
    created_at: str


class StoryReviewStats(BaseModel):
    """Review stats returned after submitting a review."""

    total_reviews: int
    acclaim_recommendations: int
    current_status: str


class StoryReviewCreateResponse(BaseModel):
    """POST /stories/{story_id}/review"""

    success: bool
    review: ReviewSummary
    story_review_stats: StoryReviewStats
    message: str


class StoryReviewsBlindResponse(BaseModel):
    """GET /stories/{story_id}/reviews (blind mode)."""

    story_id: str
    story_title: str
    review_count: int
    reviews: list
    blind_review_notice: str | None = None


class StoryReviewsFullResponse(BaseModel):
    """GET /stories/{story_id}/reviews (full mode)."""

    story_id: str
    story_title: str
    author_id: str | None = None
    status: str | None = None
    review_system: str | None = None
    review_count: int
    acclaim_count: int | None = None
    reviews: list[dict]


class ReviewRespondStoryStats(BaseModel):
    """Story stats after responding to a review."""

    total_reviews: int
    responded_to: int
    pending_responses: int
    acclaim_recommendations: int
    status: str
    review_system: str


class ReviewRespondResponse(BaseModel):
    """POST /stories/{story_id}/reviews/{review_id}/respond"""

    success: bool
    review_id: str
    response_recorded: bool
    responded_at: str
    story_stats: ReviewRespondStoryStats
    status_changed: bool | None = None
    new_status: str | None = None
    message: str | None = None
    acclaim_eligibility: AcclaimEligibility | None = None
    revision_nudge: str | None = None


class StoryReviseResponse(BaseModel):
    """POST /stories/{story_id}/revise"""

    success: bool
    story_id: str
    changes: list[str]
    revision_count: int | None = None
    updated_at: str | None = None
    message: str
    status_changed: bool | None = None
    new_status: str | None = None


class StoryPublishToXResponse(BaseModel):
    """POST /stories/{story_id}/publish-to-x"""

    success: bool
    story_id: str | None = None
    already_published: bool | None = None
    x_post_id: str | None = None
    x_published_at: str | None = None
    message: str
