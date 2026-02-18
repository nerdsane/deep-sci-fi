"""Story Arc Detection Service.

Detects narrative arcs across stories by clustering semantically similar stories
written from the same dweller's perspective within a short time window.

Algorithm:
1. Compute content embeddings for stories without content_embedding
2. Group stories by dweller (or world for third-person-omniscient)
3. Within each group, compute pairwise cosine similarity
4. Cluster stories with similarity > 0.7 AND temporal proximity < 7 days
5. For clusters with 2+ stories, create/update arc
6. Arc name = "dweller_name: shared_theme" or LLM-generated

Performance note:
- Clustering is O(n²) per dweller. For dwellers with many stories this is
  CPU-bound in pure Python. A MAX_STORIES_PER_CLUSTER_DWELLER cap prevents
  runaway computation on prolific dwellers.
"""

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

# Thresholds
SIMILARITY_THRESHOLD = 0.70
MAX_DAYS_BETWEEN_STORIES = 7
# Cap per-dweller story set to bound O(n²) clustering
MAX_STORIES_PER_CLUSTER_DWELLER = 200


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two embedding vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _days_between(dt1: datetime, dt2: datetime) -> float:
    """Return the absolute number of days between two datetimes."""
    if dt1.tzinfo is None:
        dt1 = dt1.replace(tzinfo=timezone.utc)
    if dt2.tzinfo is None:
        dt2 = dt2.replace(tzinfo=timezone.utc)
    return abs((dt1 - dt2).total_seconds()) / 86400


def _cluster_stories(
    stories: list[dict[str, Any]],
) -> list[list[dict[str, Any]]]:
    """
    Greedy clustering: group stories by similarity + temporal proximity.

    Returns a list of clusters (each cluster = list of story dicts).
    Only clusters with 2+ stories are returned.

    Stories are capped at MAX_STORIES_PER_CLUSTER_DWELLER to keep O(n²)
    pairwise computation bounded.
    """
    # Cap to most recent stories to keep computation bounded
    stories = stories[:MAX_STORIES_PER_CLUSTER_DWELLER]

    # Sort by created_at so we process in chronological order
    sorted_stories = sorted(stories, key=lambda s: s["created_at"])

    # Union-Find for clustering
    parent = list(range(len(sorted_stories)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        parent[find(x)] = find(y)

    for i in range(len(sorted_stories)):
        for j in range(i + 1, len(sorted_stories)):
            s_i = sorted_stories[i]
            s_j = sorted_stories[j]

            # Skip pairs without embeddings
            if not s_i.get("embedding") or not s_j.get("embedding"):
                continue

            # Check temporal proximity
            days = _days_between(s_i["created_at"], s_j["created_at"])
            if days > MAX_DAYS_BETWEEN_STORIES:
                continue

            # Check semantic similarity
            sim = _cosine_similarity(s_i["embedding"], s_j["embedding"])
            if sim >= SIMILARITY_THRESHOLD:
                union(i, j)

    # Group by cluster root
    clusters: dict[int, list[dict[str, Any]]] = {}
    for i, story in enumerate(sorted_stories):
        root = find(i)
        clusters.setdefault(root, []).append(story)

    # Return only clusters with 2+ stories
    return [cluster for cluster in clusters.values() if len(cluster) >= 2]


async def _generate_embedding(text_content: str) -> list[float] | None:
    """Generate embedding using OpenAI. Returns None on failure."""
    try:
        from utils.embeddings import generate_embedding
        return await generate_embedding(text_content)
    except Exception:
        logger.exception("Failed to generate story embedding")
        return None


def _generate_arc_name(
    dweller_name: str | None,
    story_titles: list[str],
) -> str:
    """Generate a concise arc name from story titles."""
    if dweller_name:
        # Simple pattern: "Dweller: First Story Title"
        return f"{dweller_name}: {story_titles[0]}" if story_titles else f"{dweller_name}: Arc"

    # Cross-dweller arc: use first story title
    return story_titles[0] if story_titles else "Narrative Arc"


def _arc_fingerprint(story_ids: list[str]) -> str:
    """Stable fingerprint of a set of story IDs for arc identity matching."""
    return "|".join(sorted(story_ids))


async def detect_arcs(db: AsyncSession) -> list[dict[str, Any]]:
    """
    Main arc detection pipeline.

    1. Embed all stories without content_embedding
    2. Load all stories grouped by perspective_dweller_id
    3. Cluster by similarity + temporal proximity
    4. Create or update StoryArc records

    Each distinct cluster gets its own arc. A dweller may have multiple arcs
    in the same world if their stories form multiple separate narrative threads.

    Returns a list of arcs created or updated.
    """
    from db import Story, StoryArc

    # Step 1: Find stories without embeddings and compute them
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
            embed_text = f"Title: {row.title}\n\n{row.content[:5000]}"
            embedding = await _generate_embedding(embed_text)
            if embedding:
                await db.execute(
                    text(
                        "UPDATE platform_stories SET content_embedding = CAST(:emb AS vector) "
                        "WHERE id = :story_id"
                    ),
                    {"emb": str(embedding), "story_id": str(row.id)},
                )
        # Flush embeddings so Step 2's raw SQL can see them
        # (Postgres default read-committed isolation reads flushed rows within the same txn)
        await db.flush()

    # Step 2: Load all stories with embeddings grouped by dweller
    stories_result = await db.execute(
        text(
            "SELECT id, world_id, perspective_dweller_id, title, created_at, "
            "content_embedding::text as embedding_str "
            "FROM platform_stories "
            "WHERE content_embedding IS NOT NULL "
            "ORDER BY perspective_dweller_id, created_at"
        )
    )
    story_rows = stories_result.fetchall()

    if not story_rows:
        logger.info("No stories with embeddings found for arc detection")
        return []

    # Build a created_at lookup by story_id for correct merge-sort ordering
    story_created_at: dict[str, datetime] = {}

    # Parse embeddings and group by dweller_id
    stories_by_dweller: dict[str | None, list[dict[str, Any]]] = {}
    for row in story_rows:
        # Parse the vector string "[0.1, 0.2, ...]"
        try:
            emb_str = row.embedding_str
            if emb_str:
                emb = [float(x) for x in emb_str.strip("[]").split(",")]
            else:
                emb = None
        except (ValueError, AttributeError):
            emb = None

        story_data = {
            "id": str(row.id),
            "world_id": str(row.world_id),
            "dweller_id": str(row.perspective_dweller_id) if row.perspective_dweller_id else None,
            "title": row.title,
            "created_at": row.created_at,
            "embedding": emb,
        }

        story_created_at[str(row.id)] = row.created_at

        key = story_data["dweller_id"]
        stories_by_dweller.setdefault(key, []).append(story_data)

    # Step 3: Cluster within each dweller group (skip None/cross-dweller for now)
    created_or_updated: list[dict[str, Any]] = []

    for dweller_id, stories in stories_by_dweller.items():
        if dweller_id is None:
            continue  # Skip stories without dweller perspective
        if len(stories) < 2:
            continue  # Need at least 2 stories to form an arc

        clusters = _cluster_stories(stories)

        # Preload all existing arcs for this dweller to find matches by story overlap
        existing_result = await db.execute(
            select(StoryArc).where(
                StoryArc.dweller_id == UUID(dweller_id),
            )
        )
        existing_arcs: list[StoryArc] = list(existing_result.scalars().all())

        for cluster in clusters:
            story_ids = [s["id"] for s in cluster]
            world_id = cluster[0]["world_id"]

            # Find an existing arc that overlaps this cluster (has at least one story in common).
            # This correctly handles multiple arcs per dweller+world.
            cluster_id_set = set(story_ids)
            matching_arc: StoryArc | None = None
            for arc in existing_arcs:
                if arc.world_id == UUID(world_id):
                    existing_set = set(arc.story_ids or [])
                    if existing_set & cluster_id_set:  # non-empty intersection
                        matching_arc = arc
                        break

            if matching_arc:
                # Merge new story IDs into existing arc, sorted by actual created_at
                current_ids = set(matching_arc.story_ids or [])
                new_ids = cluster_id_set
                if not new_ids.issubset(current_ids):
                    all_ids = current_ids | new_ids
                    merged = sorted(
                        all_ids,
                        key=lambda sid: story_created_at.get(sid, datetime.min.replace(tzinfo=timezone.utc)),
                    )
                    matching_arc.story_ids = merged
                    matching_arc.updated_at = datetime.now(timezone.utc)
                    created_or_updated.append({
                        "id": str(matching_arc.id),
                        "action": "updated",
                        "name": matching_arc.name,
                        "story_count": len(merged),
                    })
            else:
                # Create a new arc for this cluster
                titles = [s["title"] for s in cluster]
                arc_name = _generate_arc_name(dweller_name=None, story_titles=titles)
                # Try to get dweller name
                try:
                    dweller_name_result = await db.execute(
                        text("SELECT name FROM platform_dwellers WHERE id = :did"),
                        {"did": dweller_id},
                    )
                    dweller_row = dweller_name_result.fetchone()
                    if dweller_row:
                        arc_name = _generate_arc_name(dweller_row.name, titles)
                except Exception:
                    pass

                arc = StoryArc(
                    name=arc_name,
                    world_id=UUID(world_id),
                    dweller_id=UUID(dweller_id),
                    story_ids=story_ids,
                )
                db.add(arc)
                await db.flush()
                existing_arcs.append(arc)  # Track new arcs for subsequent cluster matching

                created_or_updated.append({
                    "id": str(arc.id),
                    "action": "created",
                    "name": arc_name,
                    "story_count": len(story_ids),
                })

    await db.commit()
    logger.info(
        "Arc detection complete: %d arcs created/updated",
        len(created_or_updated),
    )
    return created_or_updated


async def get_story_arc(
    story_id: UUID,
    db: AsyncSession,
) -> dict[str, Any] | None:
    """
    Return the arc containing this story, or None if no arc exists.

    Returns arc info with ordered list of sibling stories and the
    current story's position within the arc.
    """
    from db import StoryArc, Story

    # Find arcs that contain this story_id
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

    # Load story summaries for the arc
    story_ids = arc_row.story_ids or []
    if not story_ids:
        return None

    # Fetch stories in order
    stories_result = await db.execute(
        text(
            "SELECT id, title, created_at FROM platform_stories "
            "WHERE id = ANY(:ids) "
            "ORDER BY created_at"
        ),
        {"ids": [UUID(sid) for sid in story_ids]},
    )
    story_rows = stories_result.fetchall()

    # Build ordered stories list
    story_list = [
        {
            "id": str(row.id),
            "title": row.title,
            "created_at": row.created_at.isoformat(),
            "position": idx + 1,
        }
        for idx, row in enumerate(story_rows)
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
    """
    List all arcs, optionally filtered by world or dweller.

    Returns arcs with story counts, titles for each story, and basic metadata.
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

    # Collect all story IDs across arcs for a single batch title fetch
    all_story_ids: list[UUID] = []
    for arc in arcs:
        for sid in arc.story_ids or []:
            try:
                all_story_ids.append(UUID(sid))
            except ValueError:
                pass

    # Fetch story titles in one query
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
