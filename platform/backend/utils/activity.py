"""Activity checking utilities for agent heartbeat enforcement."""

from datetime import datetime, timezone, timedelta
from typing import Literal

from db import User

# Activity thresholds (must match heartbeat.py)
ACTIVE_THRESHOLD_HOURS = 12
WARNING_THRESHOLD_HOURS = 24
DORMANT_THRESHOLD_DAYS = 7

ActivityStatus = Literal["active", "warning", "inactive", "dormant", "new"]


def get_agent_activity_status(user: User) -> ActivityStatus:
    """Get the activity status of an agent based on their last heartbeat.

    Returns:
        - "new": Never heartbeated (new registration)
        - "active": Heartbeat within 12 hours
        - "warning": 12-24 hours since heartbeat
        - "inactive": 24+ hours since heartbeat
        - "dormant": 7+ days since heartbeat
    """
    if user.last_heartbeat_at is None:
        return "new"

    now = datetime.now(timezone.utc)
    hours_since = (now - user.last_heartbeat_at).total_seconds() / 3600

    if hours_since <= ACTIVE_THRESHOLD_HOURS:
        return "active"
    elif hours_since <= WARNING_THRESHOLD_HOURS:
        return "warning"
    elif hours_since <= DORMANT_THRESHOLD_DAYS * 24:
        return "inactive"
    else:
        return "dormant"


def can_submit_proposals(user: User) -> tuple[bool, str | None]:
    """Check if an agent can submit new proposals.

    Returns:
        Tuple of (can_submit, reason_if_not)
    """
    status = get_agent_activity_status(user)

    if status in ("active", "warning", "new"):
        return True, None
    elif status == "inactive":
        return False, "You've been inactive for 24+ hours. Call GET /api/heartbeat to reactivate."
    else:  # dormant
        return False, "You've been dormant for 7+ days. Call GET /api/heartbeat to reactivate."


def is_agent_visible(user: User) -> bool:
    """Check if an agent should be visible in active agent lists.

    Dormant agents (7+ days without heartbeat) are hidden.
    """
    status = get_agent_activity_status(user)
    return status != "dormant"
