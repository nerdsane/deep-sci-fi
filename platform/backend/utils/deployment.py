"""Deployment state helpers used by health and resilience endpoints."""

import os
from typing import Literal

DeploymentStatus = Literal["stable", "deploying", "degraded"]

DEFAULT_RETRY_AFTER_SECONDS = 30
_VALID_STATUSES: set[str] = {"stable", "deploying", "degraded"}


def get_retry_after_seconds() -> int:
    """Return the recommended retry delay during deployment."""
    raw = os.getenv("DEPLOYMENT_RETRY_AFTER_SECONDS", str(DEFAULT_RETRY_AFTER_SECONDS))
    try:
        parsed = int(raw)
    except ValueError:
        parsed = DEFAULT_RETRY_AFTER_SECONDS
    return max(1, parsed)


def get_forced_deployment_status() -> DeploymentStatus | None:
    """Read explicit deployment status override from environment."""
    raw = os.getenv("DSF_DEPLOYMENT_STATUS")
    if not raw:
        return None
    normalized = raw.strip().lower()
    if normalized not in _VALID_STATUSES:
        return None
    return normalized  # type: ignore[return-value]


def resolve_deployment_status(schema_is_current: bool) -> DeploymentStatus:
    """Resolve deployment status from override and runtime state."""
    forced = get_forced_deployment_status()
    if forced is not None:
        return forced
    if not schema_is_current:
        return "degraded"
    return "stable"
