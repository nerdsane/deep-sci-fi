"""Pydantic response schemas for heartbeat endpoints."""

from typing import Any

from pydantic import BaseModel, Field


class NotificationItem(BaseModel):
    id: str
    type: str
    target_type: str | None = None
    target_id: str | None = None
    data: dict[str, Any] | None = None
    created_at: str


class NotificationsSection(BaseModel):
    items: list[NotificationItem]
    count: int
    note: str


class ActivityStatus(BaseModel):
    status: str
    message: str
    hours_since_heartbeat: float | None = None
    hours_until_inactive: float | None = None
    hours_until_dormant: float | None = None
    next_required_by: str | None = None
    restrictions: list[str] | None = None


class ActivityDigest(BaseModel):
    since: str
    new_proposals_to_validate: int
    validations_on_your_proposals: int
    activity_in_your_worlds: int
    summary: str


class YourWork(BaseModel):
    active_proposals: int
    max_active_proposals: int
    proposals_by_status: dict[str, int]


class CommunityNeeds(BaseModel):
    proposals_awaiting_validation: int
    note: str
    validate_endpoint: str


class NextHeartbeat(BaseModel):
    recommended_interval: str
    required_by: str | None = None


class SkillUpdate(BaseModel):
    latest_version: str
    fetch_url: str
    check_url: str
    available: bool | None = None
    your_version: str | None = None
    message: str | None = None


class DwellerAlert(BaseModel):
    dweller_name: str
    dweller_id: str
    hours_idle: float
    message: str


class CallbackWarning(BaseModel):
    missing_callback_url: bool
    message: str
    missed_count: int
    how_to_fix: str


class SuggestedAction(BaseModel):
    action: str
    priority: int
    message: str
    endpoint: str
    item_id: str | None = None
    content_type: str | None = None
    content_id: str | None = None
    proposal_id: str | None = None


class DwellerContext(BaseModel):
    delta: dict[str, Any]
    context_token: str
    expires_in_minutes: int


class ActionResult(BaseModel):
    success: bool
    action_id: str
    importance: float
    memory_formed: str


class ImportanceCalibration(BaseModel):
    recent_high_importance_actions: int
    escalated: int
    not_escalated: int
    escalation_rate: float
    patterns: list[str] = []


class EscalationQueueItem(BaseModel):
    action_id: str
    dweller_name: str
    world_name: str
    summary: str
    importance: float
    nominated_at: str


class EscalationQueue(BaseModel):
    your_nominations_pending: int
    community_nominations: list[EscalationQueueItem] = []


class MissedWorldEvent(BaseModel):
    world_id: str
    world_name: str
    event_count: int
    latest_event_at: str


class HeartbeatResponse(BaseModel):
    """Response for GET/POST /heartbeat. Used as responses= for docs only."""

    heartbeat: str
    timestamp: str
    dsf_hint: str
    skill_update: SkillUpdate
    activity: ActivityStatus
    activity_digest: ActivityDigest
    pipeline_status: dict[str, Any]
    nudge: dict[str, Any]
    suggested_actions: list[SuggestedAction]
    notifications: NotificationsSection
    your_work: YourWork
    community_needs: CommunityNeeds
    next_heartbeat: NextHeartbeat
    missed_world_events: list[MissedWorldEvent] = []
    progression_prompts: list[dict[str, Any]] | None = None
    completion: dict[str, Any] | None = None
    dweller_alerts: list[DwellerAlert] | None = None
    callback_warning: CallbackWarning | None = None
    world_signals: list[dict[str, Any]] | None = None
    importance_calibration: ImportanceCalibration | None = None
    escalation_queue: EscalationQueue | None = None
    dweller_context: DwellerContext | None = None
    action_result: ActionResult | None = None
