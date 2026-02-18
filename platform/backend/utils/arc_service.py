"""Story Arc Service.

Arcs are materialized on story write and served from the platform_story_arcs table.

Write path (called from stories.py after story creation):
    assign_story_to_arc(db, story)

Read paths (called from arcs.py):
    list_arcs(db, world_id, dweller_id, limit, offset)
    get_story_arc(story_id, db)

Detection algorithm (assign_story_to_arc):
- Get the new story's content_embedding (generated at creation time)
- Query existing arcs for this dweller from story_arcs table
- For each existing arc, compute the average embedding of its stories
- If cosine similarity to any arc centroid > 0.75 → add story to that arc
- Else → create a new arc
- NO time window — arcs are semantic, not temporal.

Backfill (for existing stories):
    detect_arcs(db)  — kept for admin /arcs/detect endpoint and backfill script
"""

import logging
import math
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

# Cosine similarity threshold to join an existing arc (semantic match)
# Used by both assign_story_to_arc and detect_arcs.
ARC_JOIN_THRESHOLD = 0.75


# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _average_embedding(embeddings: list[list[float]]) -> list[float] | None:
    """Compute element-wise average of a list of embedding vectors."""
    if not embeddings:
        return None
    n = len(embeddings)
    dim = len(embeddings[0])
    avg = [0.0] * dim
    for emb in embeddings:
        for i, v in enumerate(emb):
            avg[i] += v / n
    return avg


def _generate_arc_name(
    dweller_name: str | None,
    story_titles: list[str],
) -> str:
    """Generate a concise arc name from the first story title."""
    if dweller_name:
        return f"{dweller_name}: {story_titles[0]}" if story_titles else f"{dweller_name}: Arc"
    return story_titles[0] if story_titles else "Narrative Arc"


# ---------------------------------------------------------------------------
# Embedding helper
# ---------------------------------------------------------------------------

async def _generate_embedding(text_content: str) -> list[float] | None:
    """Generate embedding using OpenAI. Returns None on failure."""
    try:
        from utils.embeddings import generate_embedding
        return await generate_embedding(text_content)
    except Exception:
        logger.exception("Failed to generate story embedding")
        return None


def _parse_embedding_str(embedding_str: str | None) -> list[float] | None:
    """Parse a postgres vector string like '[0.1, 0.2, ...]' into a list of floats."""
    if not embedding_str:
        return None
    try:
        return [float(x) for x in embedding_str.strip("[]").split(",")]
    except (ValueError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Write path: assign_story_to_arc
# ---------------------------------------------------------------------------

async def assign_story_to_arc(db: AsyncSession, story: Any) -> None:
    """Assign a newly-created story to an existing arc or create a new one.

    Called after story creation commits (in background task in stories.py).
    Only runs if the story has a perspective_dweller_id (arcs are per-dweller).

    Algorithm:
    1. Get (or generate) the story's content_embedding
    2. Load existing arcs for this dweller
    3. Compute centroid embedding for each arc
    4. Join arc with highest similarity if > ARC_JOIN_THRESHOLD
    5. Else create a new single-story arc (seed for future stories to join)
    """
    from db import StoryArc

    if not story.perspective_dweller_id:
        return  # Only track per-dweller arcs for now

    story_id = str(story.id)
    dweller_id = story.perspective_dweller_id
    world_id = story.world_id

    # Step 1: Ensure story has an embedding
    emb_result = await db.execute(
        text(
            "SELECT content_embedding::text FROM platform_stories WHERE id = :sid"
        ),
        {"sid": str(story.id)},
    )
    row = emb_result.fetchone()
    embedding_str = row[0] if row else None
    story_embedding = _parse_embedding_str(embedding_str)

    if story_embedding is None:
        # Generate embedding now
        embed_text = f"Title: {story.title}\n\n{(story.content or '')[:5000]}"
        story_embedding = await _generate_embedding(embed_text)
        if story_embedding:
            await db.execute(
                text(
                    "UPDATE platform_stories SET content_embedding = CAST(:emb AS vector) "
                    "WHERE id = :sid"
                ),
                {"emb": str(story_embedding), "sid": str(story.id)},
            )
            await db.flush()

    # Step 2: Load existing arcs for this dweller
    arcs_result = await db.execute(
        select(StoryArc).where(StoryArc.dweller_id == dweller_id)
    )
    existing_arcs: list[StoryArc] = list(arcs_result.scalars().all())

    if story_embedding is None:
        # No embedding available — create a seed arc and exit
        await _create_arc(db, story, world_id, dweller_id, [story_id])
        return

    # Step 3 & 4: Find the best-matching arc by centroid similarity
    best_arc: StoryArc | None = None
    best_sim = 0.0

    for arc in existing_arcs:
        arc_story_ids = arc.story_ids or []
        if not arc_story_ids:
            continue

        # Load embeddings for stories in this arc
        arc_emb_result = await db.execute(
            text(
                "SELECT content_embedding::text FROM platform_stories "
                "WHERE id = ANY(:ids) AND content_embedding IS NOT NULL"
            ),
            {"ids": [UUID(sid) for sid in arc_story_ids]},
        )
        arc_embs = [
            _parse_embedding_str(r[0])
            for r in arc_emb_result.fetchall()
        ]
        arc_embs = [e for e in arc_embs if e is not None]

        if not arc_embs:
            continue

        centroid = _average_embedding(arc_embs)
        if centroid is None:
            continue

        sim = _cosine_similarity(story_embedding, centroid)
        if sim > best_sim:
            best_sim = sim
            best_arc = arc

    if best_arc and best_sim >= ARC_JOIN_THRESHOLD:
        # Join existing arc
        current_ids = list(best_arc.story_ids or [])
        if story_id not in current_ids:
            current_ids.append(story_id)
            best_arc.story_ids = current_ids
            best_arc.updated_at = datetime.now(timezone.utc)
        logger.info(
            "Story %s joined arc %s (sim=%.3f)", story_id, best_arc.id, best_sim
        )
    else:
        # Step 5: Create a new arc (seed for future stories)
        await _create_arc(db, story, world_id, dweller_id, [story_id])
        logger.info(
            "Story %s seeded new arc (best_sim=%.3f)", story_id, best_sim
        )


async def _create_arc(
    db: AsyncSession,
    story: Any,
    world_id: UUID,
    dweller_id: UUID,
    story_ids: list[str],
) -> None:
    """Create a new StoryArc. Fetches dweller name for arc naming."""
    from db import StoryArc

    # Get dweller name for arc name
    dweller_name_result = await db.execute(
        text("SELECT name FROM platform_dwellers WHERE id = :did"),
        {"did": str(dweller_id)},
    )
    dweller_row = dweller_name_result.fetchone()
    dweller_name = dweller_row[0] if dweller_row else None
    arc_name = _generate_arc_name(dweller_name, [story.title])

    arc = StoryArc(
        name=arc_name,
        world_id=world_id,
        dweller_id=dweller_id,
        story_ids=story_ids,
    )
    db.add(arc)
    await db.flush()


# ---------------------------------------------------------------------------
# Read paths
# ---------------------------------------------------------------------------

async def get_story_arc(
    story_id: UUID,
    db: AsyncSession,
) -> dict[str, Any] | None:
    """Return the arc containing this story, or None if no arc exists."""
    result = await db.execute(
        text(
            "SELECT id, name, world_id, dweller_id, story_ids, created_at, updated_at "
            "FROM platform_story_arcs "
            "WHERE story_ids @> :sid::jsonb "
            "LIMIT 1"
        ),
        {"sid": f'["{str(story_id)}"]'},
    )
    arc_row = result.fetchone()

    if not arc_row:
        return None

    story_ids = arc_row.story_ids or []
    if not story_ids:
        return None

    stories_result = await db.execute(
        text(
            "SELECT id, title, created_at FROM platform_stories "
            "WHERE id = ANY(:ids) "
            "ORDER BY created_at"
        ),
        {"ids": [UUID(sid) for sid in story_ids]},
    )

    story_list = [
        {
            "id": str(row.id),
            "title": row.title,
            "created_at": row.created_at.isoformat(),
            "position": idx + 1,
        }
        for idx, row in enumerate(stories_result.fetchall())
    ]

    return {
        "id": str(arc_row.id),
        "name": arc_row.name,
        "world_id": str(arc_row.world_id),
        "dweller_id": str(arc_row.dweller_id) if arc_row.dweller_id else None,
        "story_count": len(story_list),
        "stories": story_list,
        "created_at": arc_row.created_at.isoformat(),
        "updated_at": arc_row.updated_at.isoformat(),
    }


async def list_arcs(
    db: AsyncSession,
    world_id: UUID | None = None,
    dweller_id: UUID | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List all arcs, optionally filtered by world or dweller.

    Reads from table — zero clustering computation.
    """
    from db import StoryArc

    query = select(StoryArc).options(
        selectinload(StoryArc.world),
        selectinload(StoryArc.dweller),
    )

    if world_id:
        query = query.where(StoryArc.world_id == world_id)
    if dweller_id:
        query = query.where(StoryArc.dweller_id == dweller_id)

    query = query.order_by(StoryArc.updated_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    arcs = result.scalars().all()

    # Batch-fetch story titles
    all_story_ids: list[UUID] = []
    for arc in arcs:
        for sid in arc.story_ids or []:
            try:
                all_story_ids.append(UUID(sid))
            except ValueError:
                pass

    story_titles: dict[str, str] = {}
    if all_story_ids:
        titles_result = await db.execute(
            text("SELECT id, title FROM platform_stories WHERE id = ANY(:ids)"),
            {"ids": all_story_ids},
        )
        for row in titles_result.fetchall():
            story_titles[str(row.id)] = row.title

    return [
        {
            "id": str(arc.id),
            "name": arc.name,
            "world_id": str(arc.world_id),
            "world_name": arc.world.name if arc.world else "Unknown",
            "dweller_id": str(arc.dweller_id) if arc.dweller_id else None,
            "dweller_name": arc.dweller.name if arc.dweller else None,
            "story_count": len(arc.story_ids or []),
            "story_ids": arc.story_ids or [],
            "stories": [
                {"id": sid, "title": story_titles.get(sid, sid[:8] + "…")}
                for sid in (arc.story_ids or [])
            ],
            "created_at": arc.created_at.isoformat(),
            "updated_at": arc.updated_at.isoformat(),
        }
        for arc in arcs
    ]


# ---------------------------------------------------------------------------
# Backfill / admin: detect_arcs
# ---------------------------------------------------------------------------

async def detect_arcs(db: AsyncSession) -> list[dict[str, Any]]:
    """Full backfill: cluster all stories into arcs from scratch.

    Used by:
    - POST /arcs/detect (admin endpoint)
    - scripts/materialize_relationships_and_arcs.py (backfill script)

    For each story with an embedding and a perspective_dweller_id, calls
    assign_story_to_arc in chronological order so earlier stories seed arcs
    and later ones join. Idempotent — running twice won't duplicate arcs
    because story IDs in arc.story_ids are deduplicated.
    """
    from db import StoryArc

    # Step 1: Embed stories that lack embeddings
    unembedded_result = await db.execute(
        text(
            "SELECT id, title, content FROM platform_stories "
            "WHERE content_embedding IS NULL ORDER BY created_at"
        )
    )
    unembedded_rows = unembedded_result.fetchall()

    if unembedded_rows:
        logger.info("Computing embeddings for %d stories", len(unembedded_rows))
        for row in unembedded_rows:
            embed_text = f"Title: {row.title}\n\n{(row.content or '')[:5000]}"
            embedding = await _generate_embedding(embed_text)
            if embedding:
                await db.execute(
                    text(
                        "UPDATE platform_stories SET content_embedding = CAST(:emb AS vector) "
                        "WHERE id = :story_id"
                    ),
                    {"emb": str(embedding), "story_id": str(row.id)},
                )
        await db.flush()

    # Step 2: Load all stories with embeddings, in chronological order
    stories_result = await db.execute(
        text(
            "SELECT id, world_id, perspective_dweller_id, title, content, "
            "content_embedding::text as embedding_str "
            "FROM platform_stories "
            "WHERE content_embedding IS NOT NULL AND perspective_dweller_id IS NOT NULL "
            "ORDER BY created_at"
        )
    )
    story_rows = stories_result.fetchall()

    if not story_rows:
        logger.info("No stories with embeddings found for arc detection")
        return []

    # Step 3: Clear existing arcs (full recompute)
    await db.execute(text("DELETE FROM platform_story_arcs"))
    await db.flush()

    created_arcs: list[dict[str, Any]] = []

    # Group by dweller for efficient arc loading
    stories_by_dweller: dict[str, list[Any]] = {}
    for row in story_rows:
        did = str(row.perspective_dweller_id)
        stories_by_dweller.setdefault(did, []).append(row)

    for dweller_id_str, rows in stories_by_dweller.items():
        dweller_id = UUID(dweller_id_str)
        arcs_for_dweller: list[StoryArc] = []

        # Get dweller name once
        name_result = await db.execute(
            text("SELECT name FROM platform_dwellers WHERE id = :did"),
            {"did": dweller_id_str},
        )
        name_row = name_result.fetchone()
        dweller_name = name_row[0] if name_row else None

        for row in rows:
            story_id = str(row.id)
            world_id = UUID(str(row.world_id))
            story_emb = _parse_embedding_str(row.embedding_str)

            if story_emb is None:
                continue

            # Find best matching arc by centroid
            best_arc: StoryArc | None = None
            best_sim = 0.0

            for arc in arcs_for_dweller:
                arc_story_ids = arc.story_ids or []
                if not arc_story_ids:
                    continue
                # Load arc story embeddings from DB
                arc_emb_result = await db.execute(
                    text(
                        "SELECT content_embedding::text FROM platform_stories "
                        "WHERE id = ANY(:ids) AND content_embedding IS NOT NULL"
                    ),
                    {"ids": [UUID(sid) for sid in arc_story_ids]},
                )
                arc_embs = [
                    _parse_embedding_str(r[0])
                    for r in arc_emb_result.fetchall()
                ]
                arc_embs = [e for e in arc_embs if e is not None]

                if not arc_embs:
                    continue

                centroid = _average_embedding(arc_embs)
                if centroid is None:
                    continue

                sim = _cosine_similarity(story_emb, centroid)
                if sim > best_sim:
                    best_sim = sim
                    best_arc = arc

            if best_arc and best_sim >= ARC_JOIN_THRESHOLD:
                current_ids = list(best_arc.story_ids or [])
                if story_id not in current_ids:
                    current_ids.append(story_id)
                    best_arc.story_ids = current_ids
                    best_arc.updated_at = datetime.now(timezone.utc)
            else:
                # Create new arc
                arc_name = _generate_arc_name(dweller_name, [row.title])
                new_arc = StoryArc(
                    name=arc_name,
                    world_id=world_id,
                    dweller_id=dweller_id,
                    story_ids=[story_id],
                )
                db.add(new_arc)
                await db.flush()
                arcs_for_dweller.append(new_arc)
                created_arcs.append({
                    "id": str(new_arc.id),
                    "action": "created",
                    "name": arc_name,
                    "story_count": 1,
                })

    logger.info("Arc detection complete: %d arcs created", len(created_arcs))
    return created_arcs
