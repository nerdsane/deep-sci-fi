"""Dweller relationship graph service.

Relationships are materialized on story write / action write and served from
the platform_dweller_relationships table — no per-request computation.

Write path:
    update_relationships_for_story(db, story)  — called from stories.py
    update_relationships_for_action(db, action) — called from dwellers.py (SPEAK actions)

Read path:
    get_dweller_graph(db, world_id, min_weight)  — called from dweller_graph.py

Directional signals (PROP-022 revision):
    speak_count_a_to_b / speak_count_b_to_a — direct SPEAK actions
    story_mention_a_to_b / story_mention_b_to_a — perspective dweller mentions other
    thread_count — reply chain depth between the pair
    co_occurrence_count — legacy: both named in same story (kept for backcompat)

Score formula:
    raw = 3*speaks_a_to_b + 3*speaks_b_to_a + 2*mention_a_to_b + 2*mention_b_to_a
          + 1*thread_count + 1*co_occurrence_count
    combined_score = raw / global_max_raw  (0.0–1.0)
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
from db.models import Story, DwellerAction, DwellerRelationship

logger = logging.getLogger(__name__)

# Skip very short names to avoid false-positive matches in prose (e.g. "Al", "Ed").
_MIN_NAME_LENGTH = 3


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _canonical(a_id: str, b_id: str) -> tuple[str, str]:
    """Return (smaller_id, larger_id) to match the CHECK constraint."""
    return (a_id, b_id) if a_id < b_id else (b_id, a_id)


async def _get_or_create_relationship(
    db: AsyncSession,
    a_id: str,
    b_id: str,
) -> DwellerRelationship:
    """Load existing relationship row or create a blank one (not yet added to session)."""
    existing = (await db.execute(
        select(DwellerRelationship).where(
            DwellerRelationship.dweller_a_id == UUID(a_id),
            DwellerRelationship.dweller_b_id == UUID(b_id),
        )
    )).scalar_one_or_none()

    if existing:
        return existing

    rel = DwellerRelationship(
        dweller_a_id=UUID(a_id),
        dweller_b_id=UUID(b_id),
        co_occurrence_count=0,
        shared_story_ids=[],
        combined_score=0.0,
        speak_count_a_to_b=0,
        speak_count_b_to_a=0,
        story_mention_a_to_b=0,
        story_mention_b_to_a=0,
        thread_count=0,
    )
    db.add(rel)
    return rel


def _raw_score(rel: DwellerRelationship) -> float:
    return (
        3.0 * rel.speak_count_a_to_b
        + 3.0 * rel.speak_count_b_to_a
        + 2.0 * rel.story_mention_a_to_b
        + 2.0 * rel.story_mention_b_to_a
        + 1.0 * rel.thread_count
        + 1.0 * rel.co_occurrence_count
    )


async def _recompute_scores_for_dwellers(
    db: AsyncSession, dweller_ids: list[str]
) -> None:
    """Recompute combined_score for all relationships touching the given dwellers.

    combined_score = raw_score / global_max_raw_score  (normalized 0.0–1.0)
    """
    # Global max raw score for normalization
    max_result = await db.execute(
        text("""
            SELECT MAX(
                3.0 * speak_count_a_to_b
                + 3.0 * speak_count_b_to_a
                + 2.0 * story_mention_a_to_b
                + 2.0 * story_mention_b_to_a
                + 1.0 * thread_count
                + 1.0 * co_occurrence_count
            )
            FROM platform_dweller_relationships
        """)
    )
    max_raw = float(max_result.scalar() or 1.0)
    if max_raw == 0:
        max_raw = 1.0

    uuid_ids = [UUID(did) for did in dweller_ids]
    rels_result = await db.execute(
        select(DwellerRelationship).where(
            (DwellerRelationship.dweller_a_id.in_(uuid_ids)) |
            (DwellerRelationship.dweller_b_id.in_(uuid_ids))
        )
    )
    rels = rels_result.scalars().all()

    for rel in rels:
        rel.combined_score = round(_raw_score(rel) / max_raw, 6)


# ---------------------------------------------------------------------------
# Write path — story creation
# ---------------------------------------------------------------------------

async def update_relationships_for_story(db: AsyncSession, story: Story) -> None:
    """Update materialized relationships after a story is created.

    Signals updated:
    - story_mention_a_to_b: perspective dweller (A) mentions another dweller (B) by name
    - co_occurrence_count: any two dwellers co-occurring in the story (legacy signal)
    - shared_story_ids: story IDs with co-occurrence

    Called after story creation commits (in new transaction from stories.py).
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

    # Find dwellers mentioned by name in the story content (word-boundary match)
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
        return

    # ── Directional: story mentions (perspective dweller → mentioned dwellers) ──
    if perspective_id:
        other_mentioned = [mid for mid in mentioned_ids if mid != perspective_id]
        for other_id in other_mentioned:
            a_id, b_id = _canonical(perspective_id, other_id)
            rel = await _get_or_create_relationship(db, a_id, b_id)

            # perspective → other: is A→B or B→A depending on canonical order
            if perspective_id == a_id:
                rel.story_mention_a_to_b += 1
            else:
                rel.story_mention_b_to_a += 1
            rel.updated_at = datetime.now(timezone.utc)

    # ── Legacy co-occurrence: non-perspective pairs only ──
    # Pairs involving the perspective dweller are already captured directionally
    # via story_mention_a_to_b / story_mention_b_to_a above — skip them here to
    # avoid double-counting in the score formula.
    non_perspective_ids = [mid for mid in mentioned_ids if mid != perspective_id]
    pairs: list[tuple[str, str]] = []
    for i in range(len(non_perspective_ids)):
        for j in range(i + 1, len(non_perspective_ids)):
            pairs.append(_canonical(non_perspective_ids[i], non_perspective_ids[j]))

    for a_id, b_id in pairs:
        rel = await _get_or_create_relationship(db, a_id, b_id)
        rel.co_occurrence_count += 1
        current_stories = list(rel.shared_story_ids or [])
        if story_id not in current_stories:
            current_stories.append(story_id)
            rel.shared_story_ids = current_stories
        rel.updated_at = datetime.now(timezone.utc)

    # Flush so score recomputation sees current counts
    await db.flush()

    await _recompute_scores_for_dwellers(db, mentioned_ids)

    logger.info(
        "Updated relationships for story %s: %d pairs", story_id, len(pairs)
    )


# ---------------------------------------------------------------------------
# Write path — action creation (SPEAK actions)
# ---------------------------------------------------------------------------

async def update_relationships_for_action(
    db: AsyncSession,
    action: DwellerAction,
) -> None:
    """Update materialized relationships after a SPEAK action is created.

    Only processes actions where:
    - action_type == 'speak'
    - target (string name) is set

    Signals updated:
    - speak_count_a_to_b or speak_count_b_to_a (directional: speaker → target)
    - thread_count (if in_reply_to_action_id resolves to the target speaking back)
    - last_interaction_at

    This is called synchronously after `db.flush()` in take_action(), before commit.
    It assumes target_dweller has already been resolved by the caller (and passed
    via action.target name), so we resolve target ID here by name lookup.
    """
    if action.action_type != "speak" or not action.target:
        return

    speaker_id = str(action.dweller_id)

    # Resolve target name to dweller ID in the same world
    speaker = (await db.execute(
        select(Dweller).where(Dweller.id == action.dweller_id)
    )).scalar_one_or_none()

    if not speaker:
        logger.warning("update_relationships_for_action: speaker dweller %s not found", speaker_id)
        return

    target_q = select(Dweller).where(
        Dweller.world_id == speaker.world_id,
        Dweller.is_active == True,  # noqa: E712
        # Case-insensitive match on name
    )
    all_world_dwellers = (await db.execute(target_q)).scalars().all()

    target_dweller = None
    target_name_lower = action.target.lower()
    for d in all_world_dwellers:
        if d.name.lower() == target_name_lower:
            target_dweller = d
            break

    if not target_dweller:
        logger.debug(
            "update_relationships_for_action: target '%s' not found as dweller in world %s",
            action.target, speaker.world_id,
        )
        return

    target_id = str(target_dweller.id)
    a_id, b_id = _canonical(speaker_id, target_id)
    rel = await _get_or_create_relationship(db, a_id, b_id)

    # Increment directional speak count (speaker → target)
    if speaker_id == a_id:
        rel.speak_count_a_to_b += 1
    else:
        rel.speak_count_b_to_a += 1

    # Thread counting: if this reply is to an action from the target dweller, it's a thread
    if action.in_reply_to_action_id:
        replied_to = (await db.execute(
            select(DwellerAction).where(DwellerAction.id == action.in_reply_to_action_id)
        )).scalar_one_or_none()
        if replied_to and str(replied_to.dweller_id) == target_id:
            rel.thread_count += 1

    rel.last_interaction_at = datetime.now(timezone.utc)
    rel.updated_at = datetime.now(timezone.utc)

    await db.flush()

    await _recompute_scores_for_dwellers(db, [speaker_id, target_id])

    logger.info(
        "Updated relationship for speak action %s: %s → %s",
        action.id, speaker.name, target_dweller.name,
    )


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
            "edges": [
                {
                    "source", "target", "weight", "combined_score", "stories",
                    "speaks_a_to_b", "speaks_b_to_a",
                    "story_mentions_a_to_b", "story_mentions_b_to_a",
                    "threads", "last_interaction"
                }
            ],
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
        # Use total interaction count as the min_weight gate
        total_interactions = (
            rel.speak_count_a_to_b
            + rel.speak_count_b_to_a
            + rel.story_mention_a_to_b
            + rel.story_mention_b_to_a
            + rel.thread_count
            + rel.co_occurrence_count
        )
        if total_interactions < min_weight:
            continue
        edges.append({
            "source": src,
            "target": tgt,
            "weight": total_interactions,
            "combined_score": rel.combined_score,
            "stories": rel.shared_story_ids or [],
            # Directional fields (PROP-022 revision)
            "speaks_a_to_b": rel.speak_count_a_to_b,
            "speaks_b_to_a": rel.speak_count_b_to_a,
            "story_mentions_a_to_b": rel.story_mention_a_to_b,
            "story_mentions_b_to_a": rel.story_mention_b_to_a,
            "threads": rel.thread_count,
            "last_interaction": rel.last_interaction_at.isoformat() if rel.last_interaction_at else None,
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
