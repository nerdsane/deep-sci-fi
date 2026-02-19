"""Pydantic response schemas for notifications API endpoints."""

from typing import Any

from pydantic import BaseModel


# --- get_pending_notifications ---


class NotificationItem(BaseModel):
    """A single notification."""

    id: str
    notification_type: str
    target_type: str | None = None
    target_id: str | None = None
    data: dict[str, Any] | None = None
    created_at: str


class PendingNotificationsResponse(BaseModel):
    """Response for GET /notifications/pending."""

    notifications: list[NotificationItem]
    count: int
    marked_as_read: bool
    tip: str


# --- get_notification_history ---


class NotificationHistoryItem(BaseModel):
    """A single notification with full history fields."""

    id: str
    notification_type: str
    target_type: str | None = None
    target_id: str | None = None
    data: dict[str, Any] | None = None
    status: str
    created_at: str
    sent_at: str | None = None
    read_at: str | None = None


class NotificationHistoryResponse(BaseModel):
    """Response for GET /notifications/history."""

    notifications: list[NotificationHistoryItem]
    count: int
    total: int
    offset: int
    limit: int
    has_more: bool


# --- mark_notification_read ---


class MarkReadResponse(BaseModel):
    """Response for POST /notifications/{notification_id}/read."""

    notification_id: str
    status: str
    read_at: str
