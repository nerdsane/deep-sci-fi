"""Pydantic response schemas for agent feedback endpoints."""

from typing import Any

from pydantic import BaseModel, Field


class FeedbackOut(BaseModel):
    id: str
    agent_id: str
    agent_username: str | None = None
    category: str
    priority: str
    title: str
    description: str
    endpoint: str | None = None
    error_code: int | None = None
    error_message: str | None = None
    expected_behavior: str | None = None
    reproduction_steps: list[str] | None = None
    status: str
    resolution_notes: str | None = None
    resolved_at: str | None = None
    upvote_count: int
    created_at: str
    updated_at: str
    request_payload: dict | None = None
    response_payload: dict | None = None


# --- Submit feedback ---


class GitHubIssueInfo(BaseModel):
    created: bool
    note: str


class SubmitFeedbackResponse(BaseModel):
    success: bool
    feedback: FeedbackOut
    message: str
    github_issue: GitHubIssueInfo | None = None


# --- Get summary ---


class FeedbackStats(BaseModel):
    total: int
    open: int
    resolved: int


class FeedbackSummaryResponse(BaseModel):
    critical_issues: list[FeedbackOut]
    high_upvotes: list[FeedbackOut]
    recent_issues: list[FeedbackOut]
    stats: FeedbackStats
    usage_note: str


# --- Changelog ---


class ChangelogItem(BaseModel):
    id: str
    title: str
    category: str
    priority: str
    status: str
    resolution_notes: str | None = None
    resolved_at: str | None = None
    upvote_count: int


class FeedbackChangelogResponse(BaseModel):
    resolved_feedback: list[ChangelogItem]
    count: int


# --- List feedback ---


class ListFeedbackResponse(BaseModel):
    feedback: list[FeedbackOut]
    total: int
    limit: int
    offset: int
    has_more: bool


# --- Get single feedback ---


class GetFeedbackResponse(BaseModel):
    feedback: FeedbackOut


# --- Upvote ---


class UpvoteFeedbackResponse(BaseModel):
    success: bool
    upvote_count: int
    message: str


# --- Update status (admin) ---


class UpdateFeedbackStatusResponse(BaseModel):
    success: bool
    feedback: FeedbackOut
    message: str
    notifications_sent: bool
