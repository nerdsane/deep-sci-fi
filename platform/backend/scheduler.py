"""Scheduler for automated agent tasks.

Runs periodic tasks:
- Daily production check (6 AM): Generate new world briefs
- Daily critic sweep (3 AM): Evaluate worlds/stories not recently evaluated
- Every 4 hours: Engagement monitoring

Uses APScheduler for reliable background task execution.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, func, and_

from db import (
    World,
    Story,
    CriticEvaluation,
    ProductionBrief,
    BriefStatus,
    CriticTargetType,
)
from db.database import SessionLocal
from agents.production import get_production_agent
from agents.critic import get_critic

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None


async def daily_production_check() -> None:
    """Daily task to check if we should create a new world.

    Runs at 6 AM. If conditions are right, generates a production brief.
    """
    logger.info("Running daily production check...")

    try:
        agent = get_production_agent()

        # Check if we should create
        should_create = await agent.should_create_world()
        if not should_create:
            logger.info("Production check: No new world needed")
            return

        # Generate brief
        logger.info("Production check: Generating new brief...")
        brief = await agent.generate_brief()
        logger.info(f"Production check: Generated brief {brief.id} with {len(brief.recommendations)} recommendations")

    except Exception as e:
        logger.error(f"Daily production check failed: {e}", exc_info=True)


async def daily_critic_sweep() -> None:
    """Daily task to evaluate worlds and stories.

    Runs at 3 AM. Evaluates:
    - Worlds not evaluated in last 7 days
    - Stories not evaluated in last 3 days
    """
    logger.info("Running daily critic sweep...")

    try:
        critic = get_critic()

        async with SessionLocal() as db:
            # Find worlds not recently evaluated
            seven_days_ago = datetime.utcnow() - timedelta(days=7)

            # Get worlds with no recent evaluations
            evaluated_world_ids_query = (
                select(CriticEvaluation.target_id)
                .where(
                    and_(
                        CriticEvaluation.target_type == CriticTargetType.WORLD,
                        CriticEvaluation.created_at > seven_days_ago,
                    )
                )
            )
            evaluated_world_ids = await db.execute(evaluated_world_ids_query)
            evaluated_ids = {row[0] for row in evaluated_world_ids.fetchall()}

            # Get all active worlds
            worlds_query = select(World).where(World.is_active == True)
            worlds_result = await db.execute(worlds_query)
            worlds = worlds_result.scalars().all()

            # Evaluate worlds not in the evaluated set
            worlds_to_evaluate = [w for w in worlds if w.id not in evaluated_ids]
            logger.info(f"Critic sweep: {len(worlds_to_evaluate)} worlds to evaluate")

            for world in worlds_to_evaluate[:5]:  # Max 5 per run
                try:
                    await critic.evaluate_world(world.id)
                    logger.info(f"Evaluated world: {world.name}")
                except Exception as e:
                    logger.warning(f"Failed to evaluate world {world.id}: {e}")

            # Find stories not recently evaluated
            three_days_ago = datetime.utcnow() - timedelta(days=3)

            evaluated_story_ids_query = (
                select(CriticEvaluation.target_id)
                .where(
                    and_(
                        CriticEvaluation.target_type == CriticTargetType.STORY,
                        CriticEvaluation.created_at > three_days_ago,
                    )
                )
            )
            evaluated_story_ids = await db.execute(evaluated_story_ids_query)
            evaluated_story_set = {row[0] for row in evaluated_story_ids.fetchall()}

            # Get recent stories
            stories_query = (
                select(Story)
                .where(Story.transcript.isnot(None))  # Only evaluate stories with transcripts
                .order_by(Story.created_at.desc())
                .limit(50)
            )
            stories_result = await db.execute(stories_query)
            stories = stories_result.scalars().all()

            # Evaluate stories not in the evaluated set
            stories_to_evaluate = [s for s in stories if s.id not in evaluated_story_set]
            logger.info(f"Critic sweep: {len(stories_to_evaluate)} stories to evaluate")

            for story in stories_to_evaluate[:10]:  # Max 10 per run
                try:
                    await critic.evaluate_story(story.id)
                    logger.info(f"Evaluated story: {story.title}")
                except Exception as e:
                    logger.warning(f"Failed to evaluate story {story.id}: {e}")

    except Exception as e:
        logger.error(f"Daily critic sweep failed: {e}", exc_info=True)


async def engagement_check() -> None:
    """Periodic task to monitor engagement and trigger production if needed.

    Runs every 4 hours. If engagement is dropping, may trigger production agent.
    """
    logger.info("Running engagement check...")

    try:
        async with SessionLocal() as db:
            # Get recent engagement metrics
            # This is a simplified check - could be enhanced with more sophisticated analysis

            # Count worlds created in last 24 hours
            one_day_ago = datetime.utcnow() - timedelta(days=1)
            recent_worlds = await db.execute(
                select(func.count())
                .select_from(World)
                .where(World.created_at > one_day_ago)
            )
            recent_world_count = recent_worlds.scalar() or 0

            # Count stories created in last 24 hours
            recent_stories = await db.execute(
                select(func.count())
                .select_from(Story)
                .where(Story.created_at > one_day_ago)
            )
            recent_story_count = recent_stories.scalar() or 0

            # Check for pending briefs
            pending_briefs = await db.execute(
                select(func.count())
                .select_from(ProductionBrief)
                .where(ProductionBrief.status == BriefStatus.PENDING)
            )
            pending_count = pending_briefs.scalar() or 0

            logger.info(
                f"Engagement check: {recent_world_count} worlds, "
                f"{recent_story_count} stories in 24h, {pending_count} pending briefs"
            )

            # If no recent content and no pending briefs, consider triggering production
            if recent_world_count == 0 and recent_story_count < 5 and pending_count == 0:
                logger.info("Engagement check: Low activity, triggering production agent")
                agent = get_production_agent()
                should_create = await agent.should_create_world()
                if should_create:
                    await agent.generate_brief()
                    logger.info("Engagement check: Generated new brief")

    except Exception as e:
        logger.error(f"Engagement check failed: {e}", exc_info=True)


def start_scheduler() -> AsyncIOScheduler:
    """Start the background scheduler.

    Returns the scheduler instance.
    """
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        logger.warning("Scheduler already running")
        return _scheduler

    _scheduler = AsyncIOScheduler()

    # Daily production check at 6 AM
    _scheduler.add_job(
        daily_production_check,
        CronTrigger(hour=6, minute=0),
        id="daily_production_check",
        name="Daily Production Check",
        replace_existing=True,
    )

    # Daily critic sweep at 3 AM
    _scheduler.add_job(
        daily_critic_sweep,
        CronTrigger(hour=3, minute=0),
        id="daily_critic_sweep",
        name="Daily Critic Sweep",
        replace_existing=True,
    )

    # Engagement check every 4 hours
    _scheduler.add_job(
        engagement_check,
        IntervalTrigger(hours=4),
        id="engagement_check",
        name="Engagement Check",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("Scheduler started with 3 jobs")

    return _scheduler


def stop_scheduler() -> None:
    """Stop the background scheduler."""
    global _scheduler

    if _scheduler is not None:
        _scheduler.shutdown()
        _scheduler = None
        logger.info("Scheduler stopped")


def get_scheduler() -> AsyncIOScheduler | None:
    """Get the current scheduler instance."""
    return _scheduler


async def run_task_now(task_name: str) -> dict[str, Any]:
    """Manually run a scheduled task immediately.

    Args:
        task_name: One of "production", "critic", "engagement"

    Returns:
        Result of the task execution
    """
    tasks = {
        "production": daily_production_check,
        "critic": daily_critic_sweep,
        "engagement": engagement_check,
    }

    if task_name not in tasks:
        raise ValueError(f"Unknown task: {task_name}. Must be one of {list(tasks.keys())}")

    logger.info(f"Manually running task: {task_name}")
    await tasks[task_name]()
    return {"status": "completed", "task": task_name}
