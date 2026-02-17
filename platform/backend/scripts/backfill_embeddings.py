#!/usr/bin/env python3
"""Backfill embeddings for all worlds that don't have one yet.

Usage:
    cd platform/backend
    source .venv/bin/activate
    python scripts/backfill_embeddings.py

Requires:
    OPENAI_API_KEY  — for generating embeddings
    DATABASE_URL    — PostgreSQL connection string

The script:
1. Fetches all active worlds without a premise_embedding
2. Generates text-embedding-3-small embeddings for each world
3. Stores the embedding vector back to the database
4. Prints a summary when done
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add backend root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load .env from platform/
load_dotenv(Path(__file__).parent.parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def backfill() -> None:
    from sqlalchemy import text
    from db.database import AsyncSessionLocal
    from utils.embeddings import generate_embedding, create_proposal_text_for_embedding

    async with AsyncSessionLocal() as db:
        # Find worlds without embeddings
        rows = (
            await db.execute(
                text("""
                    SELECT id, name, premise, scientific_basis, year_setting, causal_chain, regions
                    FROM platform_worlds
                    WHERE is_active = TRUE
                      AND (premise_embedding IS NULL)
                    ORDER BY created_at ASC
                """)
            )
        ).fetchall()

        if not rows:
            logger.info("All worlds already have embeddings — nothing to do.")
            return

        logger.info(f"Found {len(rows)} worlds without embeddings.")

        success = 0
        failed = 0

        for row in rows:
            world_id = str(row.id)
            name = row.name or "(unnamed)"
            try:
                # Build rich text for embedding
                causal_chain = row.causal_chain or []
                regions = row.regions or []

                region_text = ""
                if regions:
                    region_text = "Regions: " + "; ".join(
                        r.get("name", "") for r in regions if r.get("name")
                    )

                text_for_emb = create_proposal_text_for_embedding(
                    premise=row.premise,
                    scientific_basis=row.scientific_basis or "",
                    year_setting=row.year_setting,
                    causal_chain=causal_chain,
                )
                if region_text:
                    text_for_emb += f"\n\n{region_text}"

                embedding = await generate_embedding(text_for_emb)

                # Store back — use raw SQL for vector literal
                emb_str = "[" + ",".join(str(v) for v in embedding) + "]"
                await db.execute(
                    text(
                        "UPDATE platform_worlds "
                        "SET premise_embedding = CAST(:emb AS vector) "
                        "WHERE id = :id"
                    ),
                    {"emb": emb_str, "id": world_id},
                )
                await db.commit()

                logger.info(f"  ✓ {name} ({world_id})")
                success += 1

            except Exception as e:
                logger.error(f"  ✗ {name} ({world_id}): {e}")
                await db.rollback()
                failed += 1

        logger.info(
            f"\nDone: {success} succeeded, {failed} failed out of {len(rows)} worlds."
        )


if __name__ == "__main__":
    asyncio.run(backfill())
