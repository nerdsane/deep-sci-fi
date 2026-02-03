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
    **context: Any,
) -> dict[str, Any]:
    """
    Create a structured error response for agents.

    Args:
        error: Brief description of what went wrong
        how_to_fix: Actionable guidance for fixing the issue
        error_code: Optional machine-readable error code
        **context: Additional context (IDs, current values, etc.)

    Returns:
        Structured error dict for HTTPException detail

    Example:
        raise HTTPException(
            status_code=404,
            detail=agent_error(
                error="Dweller not found",
                how_to_fix="Check the dweller_id. Use GET /api/dwellers/worlds/{world_id}/dwellers to list dwellers.",
                dweller_id=str(dweller_id),
            )
        )
    """
    result: dict[str, Any] = {"error": error}

    if error_code:
        result["error_code"] = error_code

    if context:
        result["context"] = context

    result["how_to_fix"] = how_to_fix

    return result
