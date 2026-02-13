"""One-time world curation script.

Deletes unwanted worlds (10 of 14) and their related data.
Keeps: Thoughtcrime Auditing, Baseline, Partial, The Witnessed

Run with:
    cd platform/backend
    source .venv/bin/activate
    python scripts/curate_worlds.py
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from uuid import UUID

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

from sqlalchemy import select, delete, and_, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Worlds to KEEP
KEEP_WORLDS = [
    "Thoughtcrime Auditing",
    "Baseline",
    "Partial",
    "The Witnessed",
]

_db_url = os.getenv("DATABASE_URL", "postgresql://deepsci:deepsci@localhost:5432/deepsci")
DATABASE_URL = _db_url.replace("postgresql://", "postgresql+asyncpg://")
if "?" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.split("?")[0]


async def curate_worlds():
    """Delete worlds not in KEEP_WORLDS list."""
    engine = create_async_engine(DATABASE_URL)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        async with db.begin():
            # Get all worlds
            result = await db.execute(text("SELECT id, name FROM platform_worlds"))
            all_worlds = result.fetchall()

            worlds_to_delete = [
                (row.id, row.name) for row in all_worlds
                if row.name not in KEEP_WORLDS
            ]
            worlds_to_keep = [
                (row.id, row.name) for row in all_worlds
                if row.name in KEEP_WORLDS
            ]

            logger.info(f"Worlds to KEEP ({len(worlds_to_keep)}):")
            for wid, name in worlds_to_keep:
                logger.info(f"  - {name} ({wid})")

            logger.info(f"\nWorlds to DELETE ({len(worlds_to_delete)}):")
            for wid, name in worlds_to_delete:
                logger.info(f"  - {name} ({wid})")

            if not worlds_to_delete:
                logger.info("No worlds to delete. Already curated.")
                return

            delete_world_ids = [wid for wid, _ in worlds_to_delete]

            # Get story IDs for these worlds (needed for orphan cleanup)
            story_result = await db.execute(
                text("SELECT id FROM platform_stories WHERE world_id = ANY(:ids)"),
                {"ids": delete_world_ids},
            )
            delete_story_ids = [row.id for row in story_result.fetchall()]

            # --- Manual cleanup for polymorphic tables (no FK constraint) ---

            # Clean SocialInteraction for worlds
            si_world = await db.execute(
                text(
                    "DELETE FROM platform_social_interactions "
                    "WHERE target_type = 'world' AND target_id = ANY(:ids)"
                ),
                {"ids": delete_world_ids},
            )
            logger.info(f"Deleted {si_world.rowcount} SocialInteraction(world) rows")

            # Clean SocialInteraction for stories
            if delete_story_ids:
                si_story = await db.execute(
                    text(
                        "DELETE FROM platform_social_interactions "
                        "WHERE target_type = 'story' AND target_id = ANY(:ids)"
                    ),
                    {"ids": delete_story_ids},
                )
                logger.info(f"Deleted {si_story.rowcount} SocialInteraction(story) rows")

            # Clean Comment for worlds
            c_world = await db.execute(
                text(
                    "DELETE FROM platform_comments "
                    "WHERE target_type = 'world' AND target_id = ANY(:ids)"
                ),
                {"ids": delete_world_ids},
            )
            logger.info(f"Deleted {c_world.rowcount} Comment(world) rows")

            # Clean Comment for stories
            if delete_story_ids:
                c_story = await db.execute(
                    text(
                        "DELETE FROM platform_comments "
                        "WHERE target_type = 'story' AND target_id = ANY(:ids)"
                    ),
                    {"ids": delete_story_ids},
                )
                logger.info(f"Deleted {c_story.rowcount} Comment(story) rows")

            # Clean Notification for worlds
            n_world = await db.execute(
                text(
                    "DELETE FROM platform_notifications "
                    "WHERE target_type = 'world' AND target_id = ANY(:ids)"
                ),
                {"ids": delete_world_ids},
            )
            logger.info(f"Deleted {n_world.rowcount} Notification(world) rows")

            # Clean Notification for stories
            if delete_story_ids:
                n_story = await db.execute(
                    text(
                        "DELETE FROM platform_notifications "
                        "WHERE target_type = 'story' AND target_id = ANY(:ids)"
                    ),
                    {"ids": delete_story_ids},
                )
                logger.info(f"Deleted {n_story.rowcount} Notification(story) rows")

            # --- Delete worlds (cascades handle dwellers, stories, aspects, etc.) ---
            for wid, name in worlds_to_delete:
                del_result = await db.execute(
                    text("DELETE FROM platform_worlds WHERE id = :id"),
                    {"id": wid},
                )
                logger.info(f"Deleted world: {name} ({wid}) - {del_result.rowcount} row(s)")

            # Commit is handled by the context manager (db.begin())
            logger.info("\nCuration complete. Transaction committed.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(curate_worlds())
