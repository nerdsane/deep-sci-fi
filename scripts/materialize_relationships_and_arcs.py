#!/usr/bin/env python3
"""Backfill script: materialize all dweller relationships and story arcs.

Idempotent — safe to re-run. Processes all existing stories in chronological
order, calling the same write-path functions used during normal story creation.

Usage:
    cd platform/backend
    source .venv/bin/activate
    python3 ../../scripts/materialize_relationships_and_arcs.py

Or with a custom DATABASE_URL:
    DATABASE_URL=postgresql+asyncpg://... python3 ../../scripts/materialize_relationships_and_arcs.py
"""

import asyncio
import logging
import os
import sys

# Add backend to path
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "platform", "backend")
sys.path.insert(0, os.path.abspath(BACKEND_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("backfill")


async def run_backfill():
    from sqlalchemy import select, text
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from db.models import Base, Story

    database_url = os.environ.get(
        "DATABASE_URL",
        os.environ.get("TEST_DATABASE_URL", ""),
    )
    if not database_url:
        logger.error(
            "DATABASE_URL environment variable is required. "
            "Set it to your PostgreSQL connection string."
        )
        sys.exit(1)

    engine = create_async_engine(database_url, echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # ── Relationships ────────────────────────────────────────────────────────

    logger.info("=== Backfilling dweller relationships ===")

    async with SessionLocal() as db:
        # Clear existing relationships for a clean recompute
        await db.execute(text("DELETE FROM platform_dweller_relationships"))
        await db.commit()
        logger.info("Cleared existing relationships")

    # Load all stories with a perspective_dweller_id, in chronological order
    async with SessionLocal() as db:
        result = await db.execute(
            select(Story)
            .where(Story.perspective_dweller_id.isnot(None))
            .order_by(Story.created_at.asc())
        )
        stories = result.scalars().all()

    logger.info("Processing %d stories for relationships", len(stories))

    from utils.relationship_service import update_relationships_for_story

    for i, story in enumerate(stories):
        async with SessionLocal() as db:
            try:
                # Re-load story in this session
                result = await db.execute(select(Story).where(Story.id == story.id))
                s = result.scalar_one_or_none()
                if s:
                    await update_relationships_for_story(db, s)
                    await db.commit()
                    if (i + 1) % 50 == 0:
                        logger.info("Relationships: processed %d / %d stories", i + 1, len(stories))
            except Exception:
                logger.exception("Failed to update relationships for story %s", story.id)

    logger.info("Relationships backfill complete.")

    # ── Arcs ─────────────────────────────────────────────────────────────────

    logger.info("=== Backfilling story arcs ===")

    from utils.arc_service import detect_arcs

    async with SessionLocal() as db:
        try:
            arcs = await detect_arcs(db)
            await db.commit()
            logger.info("Arc backfill complete: %d arcs created", len(arcs))
        except Exception:
            logger.exception("Arc backfill failed")

    await engine.dispose()
    logger.info("=== Backfill done ===")


if __name__ == "__main__":
    asyncio.run(run_backfill())
