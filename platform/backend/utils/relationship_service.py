"""Dweller relationship graph service.

Computes relationships between dwellers by analyzing co-occurrence
in stories (perspective_dweller_id + name mentions) and shared world membership.

No new tables — all data derived from existing stories, dwellers, and worlds.
"""

import re
from collections import defaultdict
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import Dweller, World
from db.models import Story

# Prevent full-table scans: cap story analysis to most recent N per world group.
# This bounds memory use while still surfacing recent relationships.
_STORY_LIMIT = 500

# Skip very short names to avoid false-positive matches in prose (e.g. "Al", "Ed").
_MIN_NAME_LENGTH = 3


async def get_dweller_graph(
    db: AsyncSession,
    world_id: Optional[UUID] = None,
    min_weight: int = 1,
) -> dict:
    """
    Return nodes (dwellers) and edges (relationships) for D3 visualization.

    Algorithm:
    1. Load all active dwellers (filtered by world_id if given).
    2. Load all stories for those worlds.
    3. For each story with a perspective_dweller_id, find other dwellers
       whose names appear in the story content (case-insensitive substring match).
       Each mention → edge weight +1.
    4. Same-world dwellers share a baseline connection (weight 0 on its own,
       only surfaces if combined with story mentions OR if there are ≥2 dwellers
       with zero story connections, we don't force edges between them).
    5. Filter edges by min_weight.
    6. Build cluster list: one cluster per world.

    Returns:
        {
            "nodes": [{"id", "name", "portrait_url", "world", "world_id"}],
            "edges": [{"source", "target", "weight", "stories"}],
            "clusters": [{"id", "label", "dweller_ids"}],
        }
    """

    # ── Load dwellers ──────────────────────────────────────────────────────────
    dweller_q = select(Dweller, World.name.label("world_name")).join(
        World, Dweller.world_id == World.id
    ).where(Dweller.is_active == True)  # noqa: E712

    if world_id:
        dweller_q = dweller_q.where(Dweller.world_id == world_id)

    dweller_rows = (await db.execute(dweller_q)).all()

    if not dweller_rows:
        return {"nodes": [], "edges": [], "clusters": []}

    # Build lookup structures
    dwellers_by_id: dict[str, dict] = {}
    world_dwellers: dict[str, list[str]] = defaultdict(list)  # world_id → [dweller_ids]
    name_to_ids: dict[str, list[str]] = defaultdict(list)     # lower name → [dweller_ids]

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
        name_to_ids[d.name.lower()].append(did)

    # ── Load stories ───────────────────────────────────────────────────────────
    world_ids = list(world_dwellers.keys())

    story_q = (
        select(Story)
        .where(
            Story.world_id.in_([UUID(wid) for wid in world_ids]),
            Story.perspective_dweller_id.isnot(None),
        )
        .order_by(Story.created_at.desc())
        .limit(_STORY_LIMIT)
    )
    stories = (await db.execute(story_q)).scalars().all()

    # ── Build edge weights from story co-occurrence ────────────────────────────
    # edge_weights[(a_id, b_id)] = weight  (a_id < b_id for canonical ordering)
    edge_weights: dict[tuple[str, str], int] = defaultdict(int)
    edge_stories: dict[tuple[str, str], list[str]] = defaultdict(list)

    for story in stories:
        perspective_id = str(story.perspective_dweller_id)
        if perspective_id not in dwellers_by_id:
            continue

        if not story.content:
            continue
        content_lower = story.content.lower()
        story_id = str(story.id)
        story_world_id = str(story.world_id)

        # Find other dwellers in the same world whose names appear in content
        for other_id in world_dwellers.get(story_world_id, []):
            if other_id == perspective_id:
                continue
            other_name = dwellers_by_id[other_id]["name"].lower()
            # Skip very short names to avoid spurious matches in prose
            if len(other_name) < _MIN_NAME_LENGTH:
                continue
            # Word-boundary match: name must appear as a standalone token
            if re.search(r'\b' + re.escape(other_name) + r'\b', content_lower):
                key = (min(perspective_id, other_id), max(perspective_id, other_id))
                edge_weights[key] += 1
                if story_id not in edge_stories[key]:
                    edge_stories[key].append(story_id)

    # ── Build output ───────────────────────────────────────────────────────────
    nodes = list(dwellers_by_id.values())

    edges = []
    for (src, tgt), weight in edge_weights.items():
        if weight >= min_weight:
            edges.append({
                "source": src,
                "target": tgt,
                "weight": weight,
                "stories": edge_stories[(src, tgt)],
            })

    # Clusters = one per world
    clusters = []
    for i, (wid, dids) in enumerate(world_dwellers.items()):
        # Find world name from any dweller in it
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
