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

import asyncio
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

# Cosine similarity threshold to join an existing arc (semantic match)
# Used by both assign_story_to_arc and detect_arcs.
ARC_JOIN_THRESHOLD = 0.75

SUMMARY_MODEL = "gpt-4o-mini"
SUMMARY_CACHE_LIMIT = 256
CONCLUSION_ACTION_TYPES = {
    "conclude",
    "conclusion",
    "arc_conclusion",
    "resolve_arc",
    "end_arc",
}
CONCLUSION_CONTENT_MARKERS = (
    "arc concluded",
    "conclusion:",
    "#conclusion",
    "thread resolved",
)
_summary_cache: dict[tuple[str, str, str | None, str | None], str | None] = {}
_CACHE_MISS = object()


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


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _days_since(dt: datetime | None, now: datetime) -> int:
    if not dt:
        return 0
    delta = now - dt
    if delta.total_seconds() <= 0:
        return 0
    return int(delta.total_seconds() // 86400)


def _normalize_action_token(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.lower().replace("-", " ").replace("_", " ").split())


def _is_explicit_conclusion_action(action_type: str | None, content: str | None) -> bool:
    normalized_type = _normalize_action_token(action_type)
    if normalized_type in CONCLUSION_ACTION_TYPES:
        return True
    if normalized_type and "conclud" in normalized_type:
        return True

    normalized_content = _normalize_action_token(content)
    if not normalized_content:
        return False
    return any(marker in normalized_content for marker in CONCLUSION_CONTENT_MARKERS)


def _classify_momentum(
    recent_48h_count: int,
    recent_7d_count: int,
    last_story_at: datetime | None,
    has_explicit_conclusion: bool,
    now: datetime,
) -> str:
    if has_explicit_conclusion:
        return "concluded"
    if recent_48h_count >= 2:
        return "heating_up"
    if recent_7d_count >= 1:
        return "active"
    if not last_story_at:
        return "concluded"

    age = now - last_story_at
    if age >= timedelta(days=30):
        return "concluded"
    if age >= timedelta(days=8):
        return "stalling"
    return "active"


def _compute_arc_health_score(
    *,
    story_count: int,
    recent_48h_count: int,
    recent_7d_count: int,
    days_since_last_story: int,
    dweller_consistency: float,
    momentum: str,
) -> float:
    if momentum == "heating_up":
        recency_score = 1.0
    elif momentum == "active":
        # Keep active arcs differentiated by how recently they updated.
        recency_score = 0.65 if recent_48h_count == 0 else 0.8
    elif momentum == "stalling":
        recency_score = max(0.2, 0.55 - min(days_since_last_story, 30) / 60)
    else:  # concluded
        recency_score = 0.15

    story_count_score = min(1.0, story_count / 6)
    consistency_score = _clamp01(dweller_consistency)

    score = (
        0.5 * recency_score
        + 0.3 * story_count_score
        + 0.2 * consistency_score
    )
    return round(_clamp01(score), 3)


def _get_cached_summary(cache_key: tuple[str, str, str | None, str | None]) -> str | None | object:
    return _summary_cache.get(cache_key, _CACHE_MISS)


def _store_summary(cache_key: tuple[str, str, str | None, str | None], summary: str | None) -> None:
    if len(_summary_cache) >= SUMMARY_CACHE_LIMIT:
        # dict preserves insertion order in py3.7+; evict oldest entry
        oldest_key = next(iter(_summary_cache))
        _summary_cache.pop(oldest_key, None)
    _summary_cache[cache_key] = summary


async def _generate_arc_summary(
    *,
    first_title: str,
    latest_title: str,
    dweller_name: str | None,
    world_name: str | None,
) -> str | None:
    cache_key = (first_title, latest_title, dweller_name, world_name)
    cached = _get_cached_summary(cache_key)
    if cached is not _CACHE_MISS:
        return cached  # type: ignore[return-value]

    try:
        from utils.embeddings import get_openai_client

        client = get_openai_client()
    except Exception:
        _store_summary(cache_key, None)
        return None

    try:
        response = await client.chat.completions.create(
            model=SUMMARY_MODEL,
            temperature=0.3,
            max_tokens=80,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You summarize narrative arcs in one sentence. "
                        "Keep it concrete, in present tense, and under 24 words."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"World: {world_name or 'Unknown'}\n"
                        f"Perspective dweller: {dweller_name or 'Unknown'}\n"
                        f"First story title: {first_title}\n"
                        f"Latest story title: {latest_title}\n\n"
                        "Write one sentence describing the arc's throughline."
                    ),
                },
            ],
        )
        summary = (response.choices[0].message.content or "").strip().replace("\n", " ")
        summary = summary.strip('"').strip()
        if summary and len(summary) > 220:
            summary = summary[:217].rstrip() + "..."
        _store_summary(cache_key, summary or None)
        return summary or None
    except Exception:
        logger.exception("Arc summary generation failed")
        _store_summary(cache_key, None)
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
            "WHERE story_ids @> CAST(:sid AS jsonb) "
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
    """List all arcs with intelligence signals, optionally filtered by world/dweller."""
    from db import StoryArc

    query = (
        select(StoryArc)
        .options(selectinload(StoryArc.world), selectinload(StoryArc.dweller))
        .order_by(StoryArc.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if world_id:
        query = query.where(StoryArc.world_id == world_id)
    if dweller_id:
        query = query.where(StoryArc.dweller_id == dweller_id)

    result = await db.execute(query)
    arcs = list(result.scalars().all())
    return await _build_arc_list_payloads(db, arcs)


async def get_arc_by_id(db: AsyncSession, arc_id: UUID) -> dict[str, Any] | None:
    """Return one arc with full story details for the arc detail page."""
    from db import StoryArc

    result = await db.execute(
        select(StoryArc)
        .options(selectinload(StoryArc.world), selectinload(StoryArc.dweller))
        .where(StoryArc.id == arc_id)
    )
    arc = result.scalar_one_or_none()
    if arc is None:
        return None

    arc_payloads = await _build_arc_list_payloads(db, [arc])
    if not arc_payloads:
        return None
    arc_payload = arc_payloads[0]

    ordered_story_ids = [story["id"] for story in arc_payload["stories"]]
    story_uuid_ids: list[UUID] = []
    for sid in ordered_story_ids:
        try:
            story_uuid_ids.append(UUID(sid))
        except ValueError:
            continue

    story_details_by_id: dict[str, dict[str, Any]] = {}
    if story_uuid_ids:
        details_result = await db.execute(
            text(
                "SELECT id, title, summary, created_at, cover_image_url, thumbnail_url "
                "FROM platform_stories "
                "WHERE id = ANY(:ids)"
            ),
            {"ids": story_uuid_ids},
        )
        for row in details_result.fetchall():
            story_details_by_id[str(row.id)] = {
                "id": str(row.id),
                "title": row.title,
                "summary": row.summary,
                "created_at": row.created_at.isoformat(),
                "cover_image_url": row.cover_image_url,
                "thumbnail_url": row.thumbnail_url,
            }

    arc_payload["stories"] = [
        story_details_by_id.get(
            sid,
            {
                "id": sid,
                "title": sid[:8] + "…",
                "summary": None,
                "created_at": arc.created_at.isoformat(),
                "cover_image_url": None,
                "thumbnail_url": None,
            },
        )
        for sid in ordered_story_ids
    ]
    return arc_payload


async def _build_arc_list_payloads(db: AsyncSession, arcs: list[Any]) -> list[dict[str, Any]]:
    if not arcs:
        return []

    now = datetime.now(timezone.utc)

    # Batch-load story metadata for all arcs.
    all_story_ids: list[UUID] = []
    for arc in arcs:
        for sid in arc.story_ids or []:
            try:
                all_story_ids.append(UUID(sid))
            except ValueError:
                continue

    story_meta_by_id: dict[str, dict[str, Any]] = {}
    if all_story_ids:
        stories_result = await db.execute(
            text(
                "SELECT id, title, created_at, perspective_dweller_id, source_action_ids "
                "FROM platform_stories "
                "WHERE id = ANY(:ids)"
            ),
            {"ids": all_story_ids},
        )
        for row in stories_result.fetchall():
            story_meta_by_id[str(row.id)] = {
                "id": str(row.id),
                "title": row.title,
                "created_at": row.created_at,
                "perspective_dweller_id": str(row.perspective_dweller_id) if row.perspective_dweller_id else None,
                "source_action_ids": row.source_action_ids or [],
            }

    # Batch-load source actions so we can detect explicit arc-conclusion actions.
    all_source_action_ids: list[UUID] = []
    for story_meta in story_meta_by_id.values():
        for action_id in story_meta["source_action_ids"]:
            try:
                all_source_action_ids.append(UUID(str(action_id)))
            except ValueError:
                continue

    action_meta_by_id: dict[str, dict[str, str | None]] = {}
    if all_source_action_ids:
        action_result = await db.execute(
            text(
                "SELECT id, action_type, content "
                "FROM platform_dweller_actions "
                "WHERE id = ANY(:ids)"
            ),
            {"ids": all_source_action_ids},
        )
        for row in action_result.fetchall():
            action_meta_by_id[str(row.id)] = {
                "action_type": row.action_type,
                "content": row.content,
            }

    payloads: list[dict[str, Any]] = []
    summary_specs: list[tuple[int, str, str, str | None, str | None]] = []

    for arc in arcs:
        arc_story_ids = list(arc.story_ids or [])
        story_meta = [
            story_meta_by_id.get(
                sid,
                {
                    "id": sid,
                    "title": sid[:8] + "…",
                    "created_at": None,
                    "perspective_dweller_id": None,
                    "source_action_ids": [],
                },
            )
            for sid in arc_story_ids
        ]

        dated_stories = [item for item in story_meta if item["created_at"] is not None]
        dated_stories.sort(key=lambda item: item["created_at"])
        undated_stories = [item for item in story_meta if item["created_at"] is None]
        ordered_stories = dated_stories + undated_stories

        last_story_at = dated_stories[-1]["created_at"] if dated_stories else arc.updated_at
        recent_48h_count = sum(
            1 for story in dated_stories
            if now - story["created_at"] <= timedelta(hours=48)
        )
        recent_7d_count = sum(
            1 for story in dated_stories
            if now - story["created_at"] <= timedelta(days=7)
        )
        days_since_last_story = _days_since(last_story_at, now)

        has_explicit_conclusion = False
        for story in ordered_stories:
            for source_action_id in story["source_action_ids"]:
                action_meta = action_meta_by_id.get(str(source_action_id))
                if not action_meta:
                    continue
                if _is_explicit_conclusion_action(
                    action_meta.get("action_type"),
                    action_meta.get("content"),
                ):
                    has_explicit_conclusion = True
                    break
            if has_explicit_conclusion:
                break

        momentum = _classify_momentum(
            recent_48h_count=recent_48h_count,
            recent_7d_count=recent_7d_count,
            last_story_at=last_story_at,
            has_explicit_conclusion=has_explicit_conclusion,
            now=now,
        )

        expected_dweller_id = str(arc.dweller_id) if arc.dweller_id else None
        if expected_dweller_id and story_meta:
            matching_dweller_count = sum(
                1 for story in story_meta
                if story["perspective_dweller_id"] == expected_dweller_id
            )
            dweller_consistency = matching_dweller_count / max(1, len(story_meta))
        else:
            # Arcs are defined by dweller perspective; missing dweller metadata lowers confidence.
            dweller_consistency = 0.5 if story_meta else 0.0

        arc_health_score = _compute_arc_health_score(
            story_count=len(arc_story_ids),
            recent_48h_count=recent_48h_count,
            recent_7d_count=recent_7d_count,
            days_since_last_story=days_since_last_story,
            dweller_consistency=dweller_consistency,
            momentum=momentum,
        )

        payload = {
            "id": str(arc.id),
            "name": arc.name,
            "world_id": str(arc.world_id),
            "world_name": arc.world.name if arc.world else "Unknown",
            "dweller_id": str(arc.dweller_id) if arc.dweller_id else None,
            "dweller_name": arc.dweller.name if arc.dweller else None,
            "story_count": len(arc_story_ids),
            "story_ids": arc_story_ids,
            "stories": [
                {"id": story["id"], "title": story["title"]}
                for story in ordered_stories
            ],
            "created_at": arc.created_at.isoformat(),
            "updated_at": arc.updated_at.isoformat(),
            "momentum": momentum,
            "days_since_last_story": days_since_last_story,
            "arc_health_score": arc_health_score,
            "summary": None,
        }

        if len(ordered_stories) >= 2:
            summary_specs.append(
                (
                    len(payloads),
                    ordered_stories[0]["title"],
                    ordered_stories[-1]["title"],
                    payload["dweller_name"],
                    payload["world_name"],
                )
            )

        payloads.append(payload)

    if summary_specs:
        semaphore = asyncio.Semaphore(4)

        async def _summarize(
            first_title: str,
            latest_title: str,
            dweller_name: str | None,
            world_name: str | None,
        ) -> str | None:
            async with semaphore:
                return await _generate_arc_summary(
                    first_title=first_title,
                    latest_title=latest_title,
                    dweller_name=dweller_name,
                    world_name=world_name,
                )

        summary_results = await asyncio.gather(
            *[
                _summarize(first_title, latest_title, dweller_name, world_name)
                for _, first_title, latest_title, dweller_name, world_name in summary_specs
            ]
        )

        for (payload_index, *_), summary in zip(summary_specs, summary_results):
            payloads[payload_index]["summary"] = summary

    return payloads


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
