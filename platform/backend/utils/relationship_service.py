"""Dweller relationship graph service.

Relationships are materialized on story write and served from the
platform_dweller_relationships table — no per-request computation.

Write path (called from stories.py after story creation):
    update_relationships_for_story(db, story)

Read path (called from dweller_graph.py):
    get_dweller_graph(db, world_id, min_weight)
"""

import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from db import Dweller, World
from db.models import Story, DwellerRelationship

logger = logging.getLogger(__name__)

# Skip very short names to avoid false-positive matches in prose (e.g. "Al", "Ed").
_MIN_NAME_LENGTH = 3


# ---------------------------------------------------------------------------
# Write path
# ---------------------------------------------------------------------------

async def update_relationships_for_story(db: AsyncSession, story: Story) -> None:
    """Update materialized relationships after a story is created.

    1. Find all dwellers in the story's world whose names appear in content.
    2. Also include the perspective_dweller_id if set.
    3. For each pair, upsert the relationship row (increment count, append story).
    4. Recompute combined_score for affected rows.

    This is called after story creation commits, so it runs in a new transaction
    started by the caller (stories.py background task or inline).
    """
    if not story.content:
        return

    # Load all active dwellers in this world
    dweller_q = (
        select(Dweller)
        .where(Dweller.world_id == story.world_id, Dweller.is_active == True)  # noqa: E712
    )
    dweller_rows = (await db.execute(dweller_q)).scalars().all()

    if not dweller_rows:
        return

    content_lower = story.content.lower()
    story_id = str(story.id)
    perspective_id = str(story.perspective_dweller_id) if story.perspective_dweller_id else None

    # Find mentioned dwellers (word-boundary match, skip short names)
    mentioned_ids: list[str] = []
    for d in dweller_rows:
        name_lower = d.name.lower()
        if len(name_lower) < _MIN_NAME_LENGTH:
            continue
        if re.search(r'\b' + re.escape(name_lower) + r'\b', content_lower):
            mentioned_ids.append(str(d.id))

    # Include the perspective dweller even if not mentioned by name
    if perspective_id and perspective_id not in mentioned_ids:
        mentioned_ids.append(perspective_id)

    if len(mentioned_ids) < 2:
        return  # Need at least 2 dwellers to form a relationship

    # Build all unique canonical pairs (a < b)
    pairs: list[tuple[str, str]] = []
    for i in range(len(mentioned_ids)):
        for j in range(i + 1, len(mentioned_ids)):
            a = min(mentioned_ids[i], mentioned_ids[j])
            b = max(mentioned_ids[i], mentioned_ids[j])
            pairs.append((a, b))

    # Upsert each pair
    for a_id, b_id in pairs:
        existing = (await db.execute(
            select(DwellerRelationship).where(
                DwellerRelationship.dweller_a_id == UUID(a_id),
                DwellerRelationship.dweller_b_id == UUID(b_id),
            )
        )).scalar_one_or_none()

        if existing:
            existing.co_occurrence_count += 1
            current_stories = list(existing.shared_story_ids or [])
            if story_id not in current_stories:
                current_stories.append(story_id)
                existing.shared_story_ids = current_stories
            existing.updated_at = datetime.now(timezone.utc)
        else:
            existing = DwellerRelationship(
                dweller_a_id=UUID(a_id),
                dweller_b_id=UUID(b_id),
                co_occurrence_count=1,
                shared_story_ids=[story_id],
                combined_score=0.0,
            )
            db.add(existing)

    # Flush so we can read current counts for score normalization
    await db.flush()

    # Recompute combined_score for all affected dwellers
    # Normalize co_occurrence_count relative to max in the dataset
    await _recompute_scores_for_dwellers(db, mentioned_ids)

    logger.info(
        "Updated relationships for story %s: %d pairs", story_id, len(pairs)
    )


async def _recompute_scores_for_dwellers(
    db: AsyncSession, dweller_ids: list[str]
) -> None:
    """Recompute combined_score for all relationships touching the given dwellers.

    combined_score = 0.6 * normalized_co_occurrence + 0.4 * (semantic_similarity or 0)

    Normalization is relative to the max co_occurrence_count across ALL rows
    so scores are consistent globally.
    """
    # Get global max count for normalization
    max_result = await db.execute(
        text("SELECT MAX(co_occurrence_count) FROM platform_dweller_relationships")
    )
    max_count = max_result.scalar() or 1

    # Load all relationships touching our dwellers
    uuid_ids = [UUID(did) for did in dweller_ids]
    rels_result = await db.execute(
        select(DwellerRelationship).where(
            (DwellerRelationship.dweller_a_id.in_(uuid_ids)) |
            (DwellerRelationship.dweller_b_id.in_(uuid_ids))
        )
    )
    rels = rels_result.scalars().all()

    for rel in rels:
        normalized_co = rel.co_occurrence_count / max_count
        sem_sim = rel.semantic_similarity or 0.0
        rel.combined_score = round(0.6 * normalized_co + 0.4 * sem_sim, 6)


# ---------------------------------------------------------------------------
# Read path
# ---------------------------------------------------------------------------

async def get_dweller_graph(
    db: AsyncSession,
    world_id: Optional[UUID] = None,
    min_weight: int = 1,
) -> dict:
    """Return nodes (dwellers) and edges (relationships) for D3 visualization.

    Reads from platform_dweller_relationships — zero computation.

    Returns:
        {
            "nodes": [{"id", "name", "portrait_url", "world", "world_id"}],
            "edges": [{"source", "target", "weight", "stories"}],
            "clusters": [{"id", "label", "dweller_ids", "world_id"}],
        }
    """
    # ── Load dwellers ──────────────────────────────────────────────────────────
    dweller_q = (
        select(Dweller, World.name.label("world_name"))
        .join(World, Dweller.world_id == World.id)
        .where(Dweller.is_active == True)  # noqa: E712
    )
    if world_id:
        dweller_q = dweller_q.where(Dweller.world_id == world_id)

    dweller_rows = (await db.execute(dweller_q)).all()

    if not dweller_rows:
        return {"nodes": [], "edges": [], "clusters": []}

    dwellers_by_id: dict[str, dict] = {}
    world_dwellers: dict[str, list[str]] = defaultdict(list)

    for row in dweller_rows:
        d = row[0]
        world_name = row[1]
        did = str(d.id)
        dwellers_by_id[did] = {
            "id": did,
            "name": d.name,
            "portrait_url": d.portrait_url,
            "world": world_name,
            "world_id": str(d.world_id),
        }
        world_dwellers[str(d.world_id)].append(did)

    # ── Load pre-computed relationships ────────────────────────────────────────
    dweller_uuids = [UUID(did) for did in dwellers_by_id]

    rel_q = select(DwellerRelationship).where(
        DwellerRelationship.combined_score > 0,
        (DwellerRelationship.dweller_a_id.in_(dweller_uuids)) |
        (DwellerRelationship.dweller_b_id.in_(dweller_uuids)),
    )
    rels = (await db.execute(rel_q)).scalars().all()

    # ── Build output ───────────────────────────────────────────────────────────
    nodes = list(dwellers_by_id.values())

    edges = []
    for rel in rels:
        src = str(rel.dweller_a_id)
        tgt = str(rel.dweller_b_id)
        # Filter to dwellers in scope (respects world_id filter)
        if src not in dwellers_by_id or tgt not in dwellers_by_id:
            continue
        if rel.co_occurrence_count < min_weight:
            continue
        edges.append({
            "source": src,
            "target": tgt,
            "weight": rel.co_occurrence_count,
            "combined_score": rel.combined_score,
            "stories": rel.shared_story_ids or [],
        })

    clusters = []
    for i, (wid, dids) in enumerate(world_dwellers.items()):
        world_name = dwellers_by_id[dids[0]]["world"] if dids else wid
        clusters.append({
            "id": i,
            "label": world_name,
            "dweller_ids": dids,
            "world_id": wid,
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "clusters": clusters,
    }
