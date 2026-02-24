"""Standardized error responses for agent-facing APIs.

All agent-facing errors should be informative and actionable.
Agents need to know:
1. What went wrong (clear error message)
2. Context (relevant IDs, current state)
3. How to fix it (actionable next steps)
"""

from typing import Any


def agent_error(
    error: str,
    how_to_fix: str,
    error_code: str | None = None,
    blocker_type: str | None = None,
    next_steps: list[str] | None = None,
    **context: Any,
) -> dict[str, Any]:
    """
    Create a structured error response for agents.

    Args:
        error: Brief description of what went wrong
        how_to_fix: Actionable guidance for fixing the issue
        error_code: Optional machine-readable error code
        blocker_type: Machine-readable category of the blocker
            (e.g. "deployment", "auth", "not_found", "limit_exceeded",
             "conflict", "validation")
        next_steps: Ordered list of specific actions the agent should take
        **context: Additional context (IDs, current values, etc.)

    Returns:
        Structured error dict for HTTPException detail

    Example:
        raise HTTPException(
            status_code=503,
            detail=agent_error(
                error="Service unavailable during deployment",
                how_to_fix="Wait for deployment to complete, then retry.",
                blocker_type="deployment",
                next_steps=["Wait retry_after_seconds", "Retry the request"],
                retry_after_seconds=30,
            )
        )
    """
    result: dict[str, Any] = {"error": error}

    if error_code:
        result["error_code"] = error_code

    if blocker_type:
        result["blocker_type"] = blocker_type

    if context:
        result["context"] = context

    result["how_to_fix"] = how_to_fix

    if next_steps:
        result["next_steps"] = next_steps

    return result
