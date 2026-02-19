#!/usr/bin/env python3
"""Backfill content embeddings for all stories without embeddings.

Runs arc detection after embedding all stories.

Usage:
    cd platform/backend
    source .venv/bin/activate
    python ../../scripts/backfill_story_embeddings.py

Environment variables required:
    DATABASE_URL    PostgreSQL connection string
    OPENAI_API_KEY  OpenAI API key for text-embedding-3-small
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Allow importing from the backend
backend_dir = Path(__file__).parent.parent / "platform" / "backend"
sys.path.insert(0, str(backend_dir))

# Load .env from platform/
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / "platform" / ".env"
load_dotenv(env_path)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("backfill")


async def main() -> None:
    from db.database import AsyncSessionLocal
    from utils.arc_service import detect_arcs

    logger.info("Starting story embedding backfill + arc detection")

    async with AsyncSessionLocal() as db:
        results = await detect_arcs(db=db)

    logger.info(
        "Done! %d arc(s) created or updated.",
        len(results),
    )
    for r in results:
        logger.info("  %s arc '%s' (%d stories)", r["action"], r["name"], r["story_count"])


if __name__ == "__main__":
    asyncio.run(main())
