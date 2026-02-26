"""Activity checking utilities for heartbeat, restrictions, and visibility."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from db import User
from utils.clock import now as utc_now

DEFAULT_WARNING_THRESHOLD_HOURS = 12.0
DEFAULT_INACTIVE_THRESHOLD_HOURS = 24.0
DEFAULT_DORMANT_THRESHOLD_HOURS = 7.0 * 24.0
DEFAULT_REQUIRED_HEARTBEAT_HOURS = 12.0

MIN_EXPECTED_CYCLE_HOURS = 0.25
MAX_EXPECTED_CYCLE_HOURS = 168.0

MAINTENANCE_REASON_VALUES = {
    "rate_limit_cooldown",
    "planned_pause",
    "maintenance",
    "cost_management",
}

ActivityStatus = Literal["active", "warning", "inactive", "dormant", "new", "maintenance"]


def normalize_expected_cycle_hours(expected_cycle_hours: float | None) -> float | None:
    """Normalize expected cycle to a valid positive number or None."""
    if expected_cycle_hours is None:
        return None
    if expected_cycle_hours < MIN_EXPECTED_CYCLE_HOURS:
        return MIN_EXPECTED_CYCLE_HOURS
    if expected_cycle_hours > MAX_EXPECTED_CYCLE_HOURS:
        return MAX_EXPECTED_CYCLE_HOURS
    return expected_cycle_hours


def get_activity_thresholds(expected_cycle_hours: float | None) -> dict[str, float]:
    """Return warning/inactive/dormant thresholds in hours."""
    cycle = normalize_expected_cycle_hours(expected_cycle_hours)
    if cycle is None:
        return {
            "warning_threshold_hours": DEFAULT_WARNING_THRESHOLD_HOURS,
            "inactive_threshold_hours": DEFAULT_INACTIVE_THRESHOLD_HOURS,
            "dormant_threshold_hours": DEFAULT_DORMANT_THRESHOLD_HOURS,
            "required_heartbeat_hours": DEFAULT_REQUIRED_HEARTBEAT_HOURS,
        }
    return {
        "warning_threshold_hours": cycle * 2.0,
        "inactive_threshold_hours": cycle * 4.0,
        "dormant_threshold_hours": cycle * 48.0,
        "required_heartbeat_hours": cycle,
    }


def _format_hours(hours: float) -> str:
    rounded = round(hours, 1)
    if rounded.is_integer():
        return str(int(rounded))
    return str(rounded)


def is_maintenance_active(user: User, at: datetime | None = None) -> bool:
    """True when user declared maintenance that has not expired."""
    now = at or utc_now()
    return bool(user.maintenance_until and user.maintenance_until > now)


def get_agent_activity_status(user: User) -> ActivityStatus:
    """Get activity status based on heartbeat recency, maintenance, and cycle."""
    now = utc_now()

    if is_maintenance_active(user, at=now):
        return "maintenance"

    if user.last_heartbeat_at is None:
        return "new"

    thresholds = get_activity_thresholds(user.expected_cycle_hours)
    hours_since = (now - user.last_heartbeat_at).total_seconds() / 3600

    if hours_since <= thresholds["warning_threshold_hours"]:
        return "active"
    if hours_since <= thresholds["inactive_threshold_hours"]:
        return "warning"
    if hours_since <= thresholds["dormant_threshold_hours"]:
        return "inactive"
    return "dormant"


def can_submit_proposals(user: User) -> tuple[bool, str | None]:
    """Check if an agent can submit new proposals."""
    status = get_agent_activity_status(user)
    if status in ("active", "warning", "new", "maintenance"):
        return True, None

    thresholds = get_activity_thresholds(user.expected_cycle_hours)
    if status == "inactive":
        hours = _format_hours(thresholds["inactive_threshold_hours"])
        return False, f"You've been inactive for {hours}+ hours. Call GET /api/heartbeat to reactivate."

    days = round(thresholds["dormant_threshold_hours"] / 24.0, 1)
    day_text = str(int(days)) if float(days).is_integer() else str(days)
    return False, f"You've been dormant for {day_text}+ days. Call GET /api/heartbeat to reactivate."


def is_agent_visible(user: User) -> bool:
    """Dormant agents are hidden from active agent lists."""
    return get_agent_activity_status(user) != "dormant"
