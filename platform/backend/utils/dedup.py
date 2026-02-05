"""Dedup utility for creation endpoints.

Prevents duplicate records from rapid re-submissions (e.g., network retries,
double-clicks). Each endpoint specifies its own filter criteria and time window.
"""

import os
from datetime import timedelta

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from utils.clock import now as utc_now


async def check_recent_duplicate(
    db: AsyncSession,
    model,
    filters: list,
    window_seconds: int = 60,
):
    """Check if a matching record was created within the time window.

    Args:
        db: Database session.
        model: SQLAlchemy model class (must have created_at column).
        filters: List of SQLAlchemy filter expressions (e.g., [Story.author_id == uid]).
        window_seconds: How far back to look (default 60s).

    Returns:
        The existing record if found, else None.
    """
    # Allow override via env var (e.g., DEDUP_WINDOW_OVERRIDE_SECONDS=0 to disable)
    override = os.getenv("DEDUP_WINDOW_OVERRIDE_SECONDS")
    if override is not None:
        window_seconds = int(override)
        if window_seconds <= 0:
            return None  # Explicit disable

    cutoff = utc_now() - timedelta(seconds=window_seconds)
    query = (
        select(model)
        .where(and_(*filters, model.created_at >= cutoff))
        .order_by(model.created_at.desc())
    )
    result = await db.execute(query)
    return result.scalars().first()
