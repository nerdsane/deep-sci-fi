"""Backfill portrait images for existing dwellers.

Generates AI portraits for all dwellers that don't have portrait_url set.
Safe to run multiple times (skips dwellers that already have portraits).

Usage:
    cd platform/backend
    source .venv/bin/activate
    python scripts/backfill_dweller_portraits.py [--dry-run] [--limit N]

Estimated cost: ~$0.02/image (grok-imagine-image)
~67 existing dwellers = ~$1.34 total
"""

import argparse
import asyncio
import logging
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def backfill(dry_run: bool = False, limit: int | None = None) -> None:
    from db.database import SessionLocal
    from db.models import Dweller
    from services.art_generation import generate_dweller_portrait

    async with SessionLocal() as db:
        # Find all active dwellers without portraits
        stmt = (
            select(Dweller)
            .where(
                Dweller.is_active == True,
                Dweller.portrait_url == None,
            )
            .options(selectinload(Dweller.world))
            .order_by(Dweller.created_at)
        )
        if limit:
            stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        dwellers = result.scalars().all()

    logger.info(f"Found {len(dwellers)} dwellers without portraits")
    if not dwellers:
        logger.info("Nothing to backfill.")
        return

    if dry_run:
        for d in dwellers:
            world_name = d.world.name if d.world else "unknown"
            logger.info(f"  [DRY RUN] Would generate portrait for: {d.name} ({d.role}) in {world_name}")
        return

    success = 0
    failed = 0

    for i, dweller in enumerate(dwellers, 1):
        world = dweller.world
        if not world:
            logger.warning(f"Skipping dweller {dweller.id} — no world loaded")
            failed += 1
            continue

        logger.info(f"[{i}/{len(dwellers)}] Generating portrait for {dweller.name} ({dweller.role}) in {world.name}...")

        dweller_data = {
            "name": dweller.name,
            "role": dweller.role,
            "age": dweller.age,
            "generation": dweller.generation,
            "cultural_identity": dweller.cultural_identity,
            "origin_region": dweller.origin_region,
            "personality": dweller.personality,
        }
        world_data = {
            "name": world.name,
            "premise": world.premise,
        }

        portrait_url = await generate_dweller_portrait(
            dweller_id=str(dweller.id),
            dweller=dweller_data,
            world=world_data,
        )

        if portrait_url:
            # Persist in a fresh session to avoid stale state
            async with SessionLocal() as db:
                d = await db.get(Dweller, dweller.id)
                if d:
                    d.portrait_url = portrait_url
                    await db.commit()
            logger.info(f"  Saved: {portrait_url}")
            success += 1
        else:
            logger.warning(f"  Failed to generate portrait for {dweller.name}")
            failed += 1

        # Small delay to avoid hammering the API
        if i < len(dwellers):
            await asyncio.sleep(1)

    logger.info(f"\nBackfill complete: {success} succeeded, {failed} failed")


def main():
    parser = argparse.ArgumentParser(description="Backfill dweller portraits")
    parser.add_argument("--dry-run", action="store_true", help="List dwellers without generating")
    parser.add_argument("--limit", type=int, default=None, help="Max dwellers to process")
    args = parser.parse_args()

    asyncio.run(backfill(dry_run=args.dry_run, limit=args.limit))


if __name__ == "__main__":
    main()
