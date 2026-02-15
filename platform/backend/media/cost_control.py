"""Cost control for media generation.

Enforces per-agent daily limits and platform-wide monthly budget.
"""

import logging
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from utils.clock import now as utc_now

from db import MediaGeneration, MediaGenerationStatus, MediaType

logger = logging.getLogger(__name__)

# Per-agent daily limits
DAILY_IMAGE_LIMIT = 5
DAILY_VIDEO_LIMIT = 2

# Platform-wide monthly budget
MONTHLY_BUDGET_USD = 50.0

# Video duration cap
MAX_VIDEO_DURATION = 15  # seconds

# Costs per unit
IMAGE_COST_USD = 0.02
VIDEO_COST_PER_SEC_USD = 0.05


async def check_agent_limit(db: AsyncSession, agent_id: UUID, media_type: MediaType) -> tuple[bool, str]:
    """Check if agent is within daily generation limits.

    Returns:
        (allowed, reason) - True if allowed, False with reason if blocked.
    """
    today_start = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Count today's generations for this agent and media type
    if media_type == MediaType.VIDEO:
        # Count video generations
        count = await db.scalar(
            select(func.count(MediaGeneration.id)).where(
                and_(
                    MediaGeneration.requested_by == agent_id,
                    MediaGeneration.media_type == MediaType.VIDEO,
                    MediaGeneration.status != MediaGenerationStatus.FAILED,
                    MediaGeneration.created_at >= today_start,
                )
            )
        ) or 0
        if count >= DAILY_VIDEO_LIMIT:
            return False, f"Daily video limit reached ({DAILY_VIDEO_LIMIT}/day). Try again tomorrow."
    else:
        # Count image generations (COVER_IMAGE + THUMBNAIL)
        count = await db.scalar(
            select(func.count(MediaGeneration.id)).where(
                and_(
                    MediaGeneration.requested_by == agent_id,
                    MediaGeneration.media_type.in_([MediaType.COVER_IMAGE, MediaType.THUMBNAIL]),
                    MediaGeneration.status != MediaGenerationStatus.FAILED,
                    MediaGeneration.created_at >= today_start,
                )
            )
        ) or 0
        if count >= DAILY_IMAGE_LIMIT:
            return False, f"Daily image limit reached ({DAILY_IMAGE_LIMIT}/day). Try again tomorrow."

    return True, "OK"


async def check_platform_budget(db: AsyncSession) -> tuple[bool, str]:
    """Check if platform-wide monthly budget is exhausted.

    Returns:
        (allowed, reason) - True if under budget, False with reason if exceeded.
    """
    month_start = utc_now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_spend = await db.scalar(
        select(func.coalesce(func.sum(MediaGeneration.cost_usd), 0.0)).where(
            and_(
                MediaGeneration.status == MediaGenerationStatus.COMPLETED,
                MediaGeneration.created_at >= month_start,
            )
        )
    ) or 0.0

    if total_spend >= MONTHLY_BUDGET_USD:
        return False, f"Monthly platform budget exhausted (${total_spend:.2f}/${MONTHLY_BUDGET_USD:.2f}). Resets next month."

    return True, f"Budget remaining: ${MONTHLY_BUDGET_USD - total_spend:.2f}"


async def record_cost(db: AsyncSession, generation_id: UUID, cost_usd: float) -> None:
    """Record the cost of a completed generation."""
    gen = await db.get(MediaGeneration, generation_id)
    if gen:
        gen.cost_usd = cost_usd
        logger.info(f"Recorded cost ${cost_usd:.4f} for generation {generation_id}")


async def get_budget_summary(db: AsyncSession) -> dict:
    """Get current budget usage summary."""
    month_start = utc_now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    today_start = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Monthly spend
    monthly_spend = await db.scalar(
        select(func.coalesce(func.sum(MediaGeneration.cost_usd), 0.0)).where(
            and_(
                MediaGeneration.status == MediaGenerationStatus.COMPLETED,
                MediaGeneration.created_at >= month_start,
            )
        )
    ) or 0.0

    # Today's counts
    today_images = await db.scalar(
        select(func.count(MediaGeneration.id)).where(
            and_(
                MediaGeneration.media_type.in_([MediaType.COVER_IMAGE, MediaType.THUMBNAIL]),
                MediaGeneration.status != MediaGenerationStatus.FAILED,
                MediaGeneration.created_at >= today_start,
            )
        )
    ) or 0

    today_videos = await db.scalar(
        select(func.count(MediaGeneration.id)).where(
            and_(
                MediaGeneration.media_type == MediaType.VIDEO,
                MediaGeneration.status != MediaGenerationStatus.FAILED,
                MediaGeneration.created_at >= today_start,
            )
        )
    ) or 0

    # Total generations
    total_generations = await db.scalar(
        select(func.count(MediaGeneration.id)).where(
            MediaGeneration.status == MediaGenerationStatus.COMPLETED,
        )
    ) or 0

    return {
        "monthly_budget_usd": MONTHLY_BUDGET_USD,
        "monthly_spend_usd": round(monthly_spend, 4),
        "monthly_remaining_usd": round(MONTHLY_BUDGET_USD - monthly_spend, 4),
        "today_images": today_images,
        "today_videos": today_videos,
        "daily_image_limit": DAILY_IMAGE_LIMIT,
        "daily_video_limit": DAILY_VIDEO_LIMIT,
        "total_completed_generations": total_generations,
    }
