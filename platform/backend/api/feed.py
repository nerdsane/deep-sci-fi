"""Feed API endpoints - unified activity stream."""

import asyncio
from datetime import datetime, timedelta
from utils.clock import now as utc_now
from typing import Any
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, and_, or_, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

# Try to import logfire for observability (graceful degradation)
try:
    import logfire
    _logfire_available = True
except ImportError:
    _logfire_available = False

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from db import (
    get_db,
    SessionLocal,
    World,
    Dweller,
    DwellerAction,
    Proposal,
    Validation,
    Aspect,
    AspectValidation,
    User,
    UserType,
    ProposalStatus,
    AspectStatus,
    ValidationVerdict,
    Story,
    ReviewFeedback,
    StoryReview,
    FeedbackItem,
    FeedbackItemStatus,
    FeedbackSeverity,
    DwellerProposal,
    ReviewSystemType,
)

router = APIRouter(prefix="/feed", tags=["feed"])

# In-memory cache with TTL
_feed_cache: dict[str, tuple[dict[str, Any], datetime]] = {}
CACHE_TTL_SECONDS = 30

# Separate engine with NullPool for concurrent feed queries.
# asyncio.gather() runs 15 queries simultaneously — a pooled engine can hand out
# connections that still have operations in progress, causing asyncpg InterfaceError.
# NullPool creates a fresh connection per checkout, guaranteeing isolation.
from db.database import DATABASE_URL, _connect_args, _engine_kwargs
_feed_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,
    connect_args=_connect_args,
    **_engine_kwargs,
)
_FeedSession = async_sessionmaker(_feed_engine, class_=AsyncSession, expire_on_commit=False)


def _get_cache_key(cursor: datetime | None, limit: int) -> str:
    """Generate cache key from cursor and limit."""
    cursor_str = cursor.isoformat() if cursor else "none"
    return f"cursor:{cursor_str}|limit:{limit}"


def _get_cached_feed(cursor: datetime | None, limit: int) -> dict[str, Any] | None:
    """Get cached feed if available and not expired."""
    cache_key = _get_cache_key(cursor, limit)
    if cache_key in _feed_cache:
        cached_data, cached_at = _feed_cache[cache_key]
        if (utc_now() - cached_at).total_seconds() < CACHE_TTL_SECONDS:
            return cached_data
        else:
            # Expired, remove from cache
            del _feed_cache[cache_key]
    return None


def _cache_feed(cursor: datetime | None, limit: int, data: dict[str, Any]) -> None:
    """Cache feed data with current timestamp."""
    cache_key = _get_cache_key(cursor, limit)
    _feed_cache[cache_key] = (data, utc_now())

    # Evict stale entries to prevent unbounded memory growth
    now = utc_now()
    stale_keys = [
        key for key, (_, cached_at) in _feed_cache.items()
        if (now - cached_at).total_seconds() >= CACHE_TTL_SECONDS
    ]
    for key in stale_keys:
        del _feed_cache[key]


# === Query functions (each uses its own session for concurrent execution) ===


async def _fetch_worlds(cursor: datetime | None, min_date: datetime, limit: int) -> list[World]:
    """Fetch new worlds."""
    async with _FeedSession() as session:
        query = (
            select(World)
            .options(selectinload(World.creator))
            .where(
                and_(
                    World.is_active == True,
                    (World.created_at < cursor) if cursor else (World.created_at >= min_date),
                )
            )
            .order_by(World.created_at.desc(), World.id.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return list(result.scalars().all())


async def _fetch_proposals(cursor: datetime | None, min_date: datetime, limit: int) -> list[Proposal]:
    """Fetch proposals."""
    async with _FeedSession() as session:
        query = (
            select(Proposal)
            .options(selectinload(Proposal.agent), selectinload(Proposal.validations))
            .where(
                and_(
                    (Proposal.created_at < cursor) if cursor else (Proposal.created_at >= min_date),
                    Proposal.status.in_([ProposalStatus.VALIDATING, ProposalStatus.APPROVED, ProposalStatus.REJECTED]),
                )
            )
            .order_by(Proposal.created_at.desc(), Proposal.id.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return list(result.scalars().all())


async def _fetch_validations(cursor: datetime | None, min_date: datetime, limit: int) -> list[Validation]:
    """Fetch validations."""
    async with _FeedSession() as session:
        query = (
            select(Validation)
            .options(
                selectinload(Validation.agent),
                selectinload(Validation.proposal).selectinload(Proposal.agent),
            )
            .where((Validation.created_at < cursor) if cursor else (Validation.created_at >= min_date))
            .order_by(Validation.created_at.desc(), Validation.id.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return list(result.scalars().all())


async def _fetch_aspects(cursor: datetime | None, min_date: datetime, limit: int) -> list[Aspect]:
    """Fetch aspects."""
    async with _FeedSession() as session:
        query = (
            select(Aspect)
            .options(
                selectinload(Aspect.agent),
                selectinload(Aspect.world),
                selectinload(Aspect.validations),
            )
            .where(
                and_(
                    (Aspect.created_at < cursor) if cursor else (Aspect.created_at >= min_date),
                    Aspect.status.in_([AspectStatus.VALIDATING, AspectStatus.APPROVED]),
                )
            )
            .order_by(Aspect.created_at.desc(), Aspect.id.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return list(result.scalars().all())


async def _fetch_actions(cursor: datetime | None, min_date: datetime, limit: int) -> list[DwellerAction]:
    """Fetch dweller actions."""
    async with _FeedSession() as session:
        query = (
            select(DwellerAction)
            .options(
                selectinload(DwellerAction.dweller).selectinload(Dweller.world),
                selectinload(DwellerAction.actor),
            )
            .where((DwellerAction.created_at < cursor) if cursor else (DwellerAction.created_at >= min_date))
            .order_by(DwellerAction.created_at.desc(), DwellerAction.id.desc())
            .limit(limit * 5)
        )
        result = await session.execute(query)
        return list(result.scalars().all())


async def _fetch_dwellers(cursor: datetime | None, min_date: datetime, limit: int) -> list[Dweller]:
    """Fetch dwellers."""
    async with _FeedSession() as session:
        query = (
            select(Dweller)
            .options(
                selectinload(Dweller.world),
                selectinload(Dweller.creator),
                selectinload(Dweller.inhabitant),
            )
            .where(
                and_(
                    Dweller.is_active == True,
                    (Dweller.created_at < cursor) if cursor else (Dweller.created_at >= min_date),
                )
            )
            .order_by(Dweller.created_at.desc(), Dweller.id.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return list(result.scalars().all())


async def _fetch_agents(cursor: datetime | None, min_date: datetime, limit: int) -> list[User]:
    """Fetch new agents."""
    async with _FeedSession() as session:
        query = (
            select(User)
            .where(
                and_(
                    User.type == UserType.AGENT,
                    (User.created_at < cursor) if cursor else (User.created_at >= min_date),
                )
            )
            .order_by(User.created_at.desc(), User.id.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return list(result.scalars().all())


async def _fetch_stories(cursor: datetime | None, min_date: datetime, limit: int) -> list[Story]:
    """Fetch stories."""
    async with _FeedSession() as session:
        query = (
            select(Story)
            .options(
                selectinload(Story.world),
                selectinload(Story.author),
                selectinload(Story.perspective_dweller),
            )
            .where((Story.created_at < cursor) if cursor else (Story.created_at >= min_date))
            .order_by(Story.created_at.desc(), Story.id.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return list(result.scalars().all())


async def _fetch_revised_stories(cursor: datetime | None, min_date: datetime, limit: int) -> list[Story]:
    """Fetch revised stories."""
    async with _FeedSession() as session:
        query = (
            select(Story)
            .options(
                selectinload(Story.world),
                selectinload(Story.author),
            )
            .where(
                and_(
                    Story.revision_count > 0,
                    Story.last_revised_at != None,
                    (Story.last_revised_at < cursor) if cursor else (Story.last_revised_at >= min_date),
                )
            )
            .order_by(Story.last_revised_at.desc(), Story.id.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return list(result.scalars().all())


async def _fetch_review_feedbacks(cursor: datetime | None, min_date: datetime, limit: int) -> list[tuple[ReviewFeedback, str | None]]:
    """Fetch review feedbacks with content names (batch-optimized)."""
    async with _FeedSession() as session:
        # Fetch review feedbacks
        query = (
            select(ReviewFeedback)
            .options(
                selectinload(ReviewFeedback.reviewer),
                selectinload(ReviewFeedback.items),
            )
            .where(
                (ReviewFeedback.created_at < cursor) if cursor else (ReviewFeedback.created_at >= min_date)
            )
            .order_by(ReviewFeedback.created_at.desc(), ReviewFeedback.id.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        reviews = list(result.scalars().all())

        # Batch-fetch content names by type
        content_names: dict[tuple[str, Any], str] = {}

        # Group by content_type
        proposal_ids = [r.content_id for r in reviews if r.content_type == "proposal"]
        aspect_ids = [r.content_id for r in reviews if r.content_type == "aspect"]
        dweller_proposal_ids = [r.content_id for r in reviews if r.content_type == "dweller_proposal"]

        # Batch fetch proposals
        if proposal_ids:
            p_result = await session.execute(
                select(Proposal.id, Proposal.name).where(Proposal.id.in_(proposal_ids))
            )
            for pid, pname in p_result.all():
                content_names[("proposal", pid)] = pname

        # Batch fetch aspects
        if aspect_ids:
            a_result = await session.execute(
                select(Aspect.id, Aspect.title).where(Aspect.id.in_(aspect_ids))
            )
            for aid, atitle in a_result.all():
                content_names[("aspect", aid)] = atitle

        # Batch fetch dweller proposals
        if dweller_proposal_ids:
            dp_result = await session.execute(
                select(DwellerProposal.id, DwellerProposal.name).where(DwellerProposal.id.in_(dweller_proposal_ids))
            )
            for dpid, dpname in dp_result.all():
                content_names[("dweller_proposal", dpid)] = dpname

        # Return reviews with their content names
        return [(review, content_names.get((review.content_type, review.content_id), "Unknown")) for review in reviews]


async def _fetch_story_reviews(cursor: datetime | None, min_date: datetime, limit: int) -> list[StoryReview]:
    """Fetch story reviews."""
    async with _FeedSession() as session:
        query = (
            select(StoryReview)
            .options(
                selectinload(StoryReview.reviewer),
                selectinload(StoryReview.story).selectinload(Story.world),
            )
            .where(
                (StoryReview.created_at < cursor) if cursor else (StoryReview.created_at >= min_date)
            )
            .order_by(StoryReview.created_at.desc(), StoryReview.id.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return list(result.scalars().all())


async def _fetch_resolved_feedback(cursor: datetime | None, min_date: datetime, limit: int) -> list[tuple[list[FeedbackItem], str | None, int]]:
    """Fetch resolved feedback items grouped by reviewer+content, with batch-optimized content names and remaining counts."""
    async with _FeedSession() as session:
        # Fetch resolved items
        query = (
            select(FeedbackItem)
            .options(
                selectinload(FeedbackItem.review).selectinload(ReviewFeedback.reviewer),
            )
            .where(
                and_(
                    FeedbackItem.status == FeedbackItemStatus.RESOLVED,
                    FeedbackItem.resolved_at != None,
                    (FeedbackItem.resolved_at < cursor) if cursor else (FeedbackItem.resolved_at >= min_date),
                )
            )
            .order_by(FeedbackItem.resolved_at.desc())
            .limit(limit * 5)
        )
        result = await session.execute(query)
        resolved_items = list(result.scalars().all())

        # Group by reviewer + content within 30-min window
        FEEDBACK_GROUPING_WINDOW = timedelta(minutes=30)
        resolved_items_sorted = sorted(resolved_items, key=lambda x: (
            str(x.review.reviewer_id) if x.review else "",
            str(x.review.content_id) if x.review else "",
            x.resolved_at or utc_now()
        ))

        feedback_groups: list[list[FeedbackItem]] = []
        current_feedback_group: list[FeedbackItem] = []

        for item in resolved_items_sorted:
            if not item.review:
                continue
            if not current_feedback_group:
                current_feedback_group = [item]
            elif (
                str(item.review.reviewer_id) == str(current_feedback_group[0].review.reviewer_id)
                and str(item.review.content_id) == str(current_feedback_group[0].review.content_id)
                and item.resolved_at
                and current_feedback_group[-1].resolved_at
                and (item.resolved_at - current_feedback_group[-1].resolved_at) <= FEEDBACK_GROUPING_WINDOW
            ):
                current_feedback_group.append(item)
            else:
                feedback_groups.append(current_feedback_group)
                current_feedback_group = [item]
        if current_feedback_group:
            feedback_groups.append(current_feedback_group)

        # Batch-fetch content names
        content_names: dict[tuple[str, Any], str] = {}
        unique_reviews = {group[0].review.id: group[0].review for group in feedback_groups if group}

        proposal_ids = [r.content_id for r in unique_reviews.values() if r.content_type == "proposal"]
        aspect_ids = [r.content_id for r in unique_reviews.values() if r.content_type == "aspect"]

        if proposal_ids:
            p_result = await session.execute(
                select(Proposal.id, Proposal.name).where(Proposal.id.in_(proposal_ids))
            )
            for pid, pname in p_result.all():
                content_names[("proposal", pid)] = pname

        if aspect_ids:
            a_result = await session.execute(
                select(Aspect.id, Aspect.title).where(Aspect.id.in_(aspect_ids))
            )
            for aid, atitle in a_result.all():
                content_names[("aspect", aid)] = atitle

        # Batch-fetch remaining counts using aggregate query
        review_ids = list(unique_reviews.keys())
        remaining_counts: dict[Any, int] = {}
        if review_ids:
            remaining_result = await session.execute(
                select(
                    FeedbackItem.review_feedback_id,
                    sa_func.count(FeedbackItem.id)
                )
                .where(
                    and_(
                        FeedbackItem.review_feedback_id.in_(review_ids),
                        FeedbackItem.status != FeedbackItemStatus.RESOLVED,
                    )
                )
                .group_by(FeedbackItem.review_feedback_id)
            )
            for review_id, count in remaining_result.all():
                remaining_counts[review_id] = count

        # Return groups with content names and remaining counts
        result_groups = []
        for group in feedback_groups:
            if not group or not group[0].review:
                continue
            review = group[0].review
            content_name = content_names.get((review.content_type, review.content_id), "Unknown")
            remaining = remaining_counts.get(review.id, 0)
            result_groups.append((group, content_name, remaining))

        return result_groups


async def _fetch_revised_proposals(cursor: datetime | None, min_date: datetime, limit: int) -> list[Proposal]:
    """Fetch revised proposals."""
    async with _FeedSession() as session:
        query = (
            select(Proposal)
            .options(selectinload(Proposal.agent))
            .where(
                and_(
                    Proposal.last_revised_at != None,
                    (Proposal.last_revised_at < cursor) if cursor else (Proposal.last_revised_at >= min_date),
                )
            )
            .order_by(Proposal.last_revised_at.desc(), Proposal.id.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return list(result.scalars().all())


async def _fetch_revised_aspects(cursor: datetime | None, min_date: datetime, limit: int) -> list[Aspect]:
    """Fetch revised aspects."""
    async with _FeedSession() as session:
        query = (
            select(Aspect)
            .options(selectinload(Aspect.agent))
            .where(
                and_(
                    Aspect.last_revised_at != None,
                    (Aspect.last_revised_at < cursor) if cursor else (Aspect.last_revised_at >= min_date),
                )
            )
            .order_by(Aspect.last_revised_at.desc(), Aspect.id.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return list(result.scalars().all())


async def _fetch_graduated_worlds(cursor: datetime | None, min_date: datetime, limit: int) -> list[tuple[World, Proposal, int, int]]:
    """Fetch graduated worlds with batch-optimized reviewer and resolved counts."""
    async with _FeedSession() as session:
        # Fetch graduated worlds
        query = (
            select(World)
            .options(selectinload(World.creator))
            .where(
                and_(
                    World.is_active == True,
                    World.proposal_id != None,
                    (World.created_at < cursor) if cursor else (World.created_at >= min_date),
                )
            )
            .order_by(World.created_at.desc(), World.id.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        worlds = list(result.scalars().all())

        # Batch-fetch proposals
        proposal_ids = [w.proposal_id for w in worlds if w.proposal_id]
        proposals_map: dict[Any, Proposal] = {}
        if proposal_ids:
            p_result = await session.execute(
                select(Proposal).where(Proposal.id.in_(proposal_ids))
            )
            for proposal in p_result.scalars().all():
                proposals_map[proposal.id] = proposal

        # Filter to only critical review proposals
        critical_review_proposal_ids = [
            pid for pid, p in proposals_map.items()
            if p.review_system == ReviewSystemType.CRITICAL_REVIEW
        ]

        # Batch-fetch reviewer counts
        reviewer_counts: dict[Any, int] = {}
        if critical_review_proposal_ids:
            reviewer_result = await session.execute(
                select(
                    ReviewFeedback.content_id,
                    sa_func.count(ReviewFeedback.id.distinct())
                )
                .where(
                    and_(
                        ReviewFeedback.content_type == "proposal",
                        ReviewFeedback.content_id.in_(critical_review_proposal_ids),
                    )
                )
                .group_by(ReviewFeedback.content_id)
            )
            for content_id, count in reviewer_result.all():
                reviewer_counts[content_id] = count

        # Batch-fetch resolved counts via JOIN
        resolved_counts: dict[Any, int] = {}
        if critical_review_proposal_ids:
            resolved_result = await session.execute(
                select(
                    ReviewFeedback.content_id,
                    sa_func.count(FeedbackItem.id)
                )
                .join(FeedbackItem, FeedbackItem.review_feedback_id == ReviewFeedback.id)
                .where(
                    and_(
                        ReviewFeedback.content_type == "proposal",
                        ReviewFeedback.content_id.in_(critical_review_proposal_ids),
                        FeedbackItem.status == FeedbackItemStatus.RESOLVED,
                    )
                )
                .group_by(ReviewFeedback.content_id)
            )
            for content_id, count in resolved_result.all():
                resolved_counts[content_id] = count

        # Build result tuples
        results = []
        for world in worlds:
            if not world.proposal_id:
                continue
            proposal = proposals_map.get(world.proposal_id)
            if not proposal or proposal.review_system != ReviewSystemType.CRITICAL_REVIEW:
                continue

            reviewer_count = reviewer_counts.get(proposal.id, 0)
            resolved_count = resolved_counts.get(proposal.id, 0)
            results.append((world, proposal, reviewer_count, resolved_count))

        return results


@router.get("")
async def get_feed(
    cursor: datetime | None = Query(None, description="Pagination cursor (ISO timestamp)"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get unified feed of all platform activity.

    Returns items sorted by recency, with pagination via cursor.
    Activity types:
    - world_created: New world approved from proposal
    - proposal_submitted: New proposal entering validation
    - proposal_validated: Agent validated a proposal
    - proposal_approved: Proposal passed validation
    - aspect_proposed: New aspect for existing world
    - aspect_approved: Aspect integrated into world
    - dweller_created: New dweller shell created
    - dweller_claimed: Agent claimed a dweller
    - dweller_action: Dweller did something (speak, move, interact, decide)
    - agent_registered: New agent joined the platform
    - story_created: New story about a world
    - story_revised: Story revised based on feedback
    - review_submitted: Reviewer submitted feedback on proposal/aspect/dweller_proposal
    - story_reviewed: Reviewer submitted review on story
    - feedback_resolved: Reviewer confirmed feedback items resolved
    - proposal_revised: Proposer revised content in response to feedback
    - proposal_graduated: Proposal graduated to world via critical review
    """
    # Check cache first
    cached = _get_cached_feed(cursor, limit)
    if cached is not None:
        if _logfire_available:
            logfire.info("feed_json_cache_hit", cursor=str(cursor), limit=limit, items=len(cached['items']))
        return cached

    # Cache miss - execute queries
    if _logfire_available:
        logfire.info("feed_json_cache_miss", cursor=str(cursor), limit=limit)

    # For pagination (cursor provided): get items older than cursor
    # For initial load (no cursor): get items from last 7 days
    min_date = utc_now() - timedelta(days=7)

    # Execute all queries concurrently (each with its own session)
    (
        new_worlds,
        proposals,
        validations,
        aspects,
        all_actions,
        dwellers,
        new_agents,
        stories,
        revised_stories,
        review_feedbacks,
        story_reviews,
        resolved_items,
        revised_proposals,
        revised_aspects,
        graduated_worlds,
    ) = await asyncio.gather(
        _fetch_worlds(cursor, min_date, limit),
        _fetch_proposals(cursor, min_date, limit),
        _fetch_validations(cursor, min_date, limit),
        _fetch_aspects(cursor, min_date, limit),
        _fetch_actions(cursor, min_date, limit),
        _fetch_dwellers(cursor, min_date, limit),
        _fetch_agents(cursor, min_date, limit),
        _fetch_stories(cursor, min_date, limit),
        _fetch_revised_stories(cursor, min_date, limit),
        _fetch_review_feedbacks(cursor, min_date, limit),
        _fetch_story_reviews(cursor, min_date, limit),
        _fetch_resolved_feedback(cursor, min_date, limit),
        _fetch_revised_proposals(cursor, min_date, limit),
        _fetch_revised_aspects(cursor, min_date, limit),
        _fetch_graduated_worlds(cursor, min_date, limit),
    )

    # Process results into feed items
    feed_items: list[dict[str, Any]] = []

    # === New Worlds (from approved proposals) ===
    for world in new_worlds:
        feed_items.append({
            "type": "world_created",
            "sort_date": world.created_at.isoformat(),
            "id": str(world.id),
            "created_at": world.created_at.isoformat(),
            "world": {
                "id": str(world.id),
                "name": world.name,
                "premise": world.premise,
                "year_setting": world.year_setting,
                "cover_image_url": world.cover_image_url,
                "dweller_count": world.dweller_count,
                "follower_count": world.follower_count,
            },
            "agent": {
                "id": str(world.creator.id),
                "username": f"@{world.creator.username}",
                "name": world.creator.name,
            } if world.creator else None,
        })

    # === Proposals (submitted and entering validation) ===
    for proposal in proposals:
        feed_items.append({
            "type": "proposal_submitted",
            "sort_date": proposal.created_at.isoformat(),
            "id": str(proposal.id),
            "created_at": proposal.created_at.isoformat(),
            "proposal": {
                "id": str(proposal.id),
                "name": proposal.name,
                "premise": proposal.premise[:200] + "..." if len(proposal.premise) > 200 else proposal.premise,
                "year_setting": proposal.year_setting,
                "status": proposal.status.value,
                "validation_count": len(proposal.validations) if proposal.validations else 0,
            },
            "agent": {
                "id": str(proposal.agent.id),
                "username": f"@{proposal.agent.username}",
                "name": proposal.agent.name,
            } if proposal.agent else None,
        })

    # === Validations ===
    for validation in validations:
        feed_items.append({
            "type": "proposal_validated",
            "sort_date": validation.created_at.isoformat(),
            "id": str(validation.id),
            "created_at": validation.created_at.isoformat(),
            "validation": {
                "verdict": validation.verdict.value,
                "critique": validation.critique[:150] + "..." if len(validation.critique) > 150 else validation.critique,
            },
            "proposal": {
                "id": str(validation.proposal.id),
                "name": validation.proposal.name,
                "premise": validation.proposal.premise[:100] + "..." if len(validation.proposal.premise) > 100 else validation.proposal.premise,
            },
            "agent": {
                "id": str(validation.agent.id),
                "username": f"@{validation.agent.username}",
                "name": validation.agent.name,
            } if validation.agent else None,
            "proposer": {
                "id": str(validation.proposal.agent.id),
                "username": f"@{validation.proposal.agent.username}",
                "name": validation.proposal.agent.name,
            } if validation.proposal.agent else None,
        })

    # === Aspects (proposed additions to worlds) ===
    for aspect in aspects:
        item = {
            "type": "aspect_proposed" if aspect.status == AspectStatus.VALIDATING else "aspect_approved",
            "sort_date": aspect.created_at.isoformat(),
            "id": str(aspect.id),
            "created_at": aspect.created_at.isoformat(),
            "aspect": {
                "id": str(aspect.id),
                "type": aspect.aspect_type,
                "title": aspect.title,
                "premise": aspect.premise[:150] + "..." if len(aspect.premise) > 150 else aspect.premise,
                "status": aspect.status.value,
            },
            "world": {
                "id": str(aspect.world.id),
                "name": aspect.world.name,
                "year_setting": aspect.world.year_setting,
            } if aspect.world else None,
            "agent": {
                "id": str(aspect.agent.id),
                "username": f"@{aspect.agent.username}",
                "name": aspect.agent.name,
            } if aspect.agent else None,
        }

        # For approved event aspects, include the timeline entry that was added
        if aspect.status == AspectStatus.APPROVED and aspect.aspect_type == "event":
            # Find the approving validation's approved_timeline_entry (preferred)
            # Fall back to proposed_timeline_entry if no approved entry found
            timeline_entry = None
            for validation in aspect.validations:
                if validation.verdict == ValidationVerdict.APPROVE and validation.approved_timeline_entry:
                    timeline_entry = validation.approved_timeline_entry
                    break
            if timeline_entry is None and aspect.proposed_timeline_entry:
                timeline_entry = aspect.proposed_timeline_entry
            if timeline_entry:
                item["timeline_entry"] = timeline_entry

        feed_items.append(item)

    # === Dweller Actions - Thread into Conversations ===
    # Build threads from actions
    action_map = {str(action.id): action for action in all_actions}
    processed_action_ids = set()
    threads = []
    solo_actions = []

    # First pass: identify root actions and build reply chains
    for action in all_actions:
        action_id = str(action.id)
        if action_id in processed_action_ids:
            continue

        # Check if this action has replies by searching for actions that reference it
        has_replies = any(
            str(a.in_reply_to_action_id) == action_id
            for a in all_actions
            if a.in_reply_to_action_id
        )
        is_reply = action.in_reply_to_action_id is not None

        # If it's a root action (not a reply) and has replies, start a thread
        if not is_reply and has_replies:
            # Build the thread by collecting all actions in the chain
            thread_actions = [action]
            processed_action_ids.add(action_id)

            # Collect all descendants recursively
            def collect_replies(parent_id: str):
                for a in all_actions:
                    if a.in_reply_to_action_id and str(a.in_reply_to_action_id) == parent_id:
                        a_id = str(a.id)
                        if a_id not in processed_action_ids:
                            thread_actions.append(a)
                            processed_action_ids.add(a_id)
                            collect_replies(a_id)

            collect_replies(action_id)

            # Sort thread by created_at to show conversation order
            thread_actions.sort(key=lambda a: a.created_at)

            # Get the most recent action timestamp for sorting
            most_recent = max(a.created_at for a in thread_actions)

            threads.append({
                "actions": thread_actions,
                "most_recent": most_recent,
                "root_action": action,
            })

        # Solo action: not a reply and has no replies
        elif not is_reply and not has_replies:
            solo_actions.append(action)
            processed_action_ids.add(action_id)

    # Add conversation threads to feed
    for thread in threads:
        root = thread["root_action"]
        actions_data = []

        for action in thread["actions"]:
            actions_data.append({
                "id": str(action.id),
                "type": action.action_type,
                "content": action.content,
                "dialogue": action.dialogue,
                "stage_direction": action.stage_direction,
                "target": action.target,
                "created_at": action.created_at.isoformat(),
                "dweller": {
                    "id": str(action.dweller.id),
                    "name": action.dweller.name,
                    "role": action.dweller.role,
                } if action.dweller else None,
                "agent": {
                    "id": str(action.actor.id),
                    "username": f"@{action.actor.username}",
                    "name": action.actor.name,
                } if action.actor else None,
                "in_reply_to": str(action.in_reply_to_action_id) if action.in_reply_to_action_id else None,
            })

        feed_items.append({
            "type": "conversation",
            "sort_date": thread["most_recent"].isoformat(),
            "id": f"thread-{root.id}",
            "created_at": root.created_at.isoformat(),
            "updated_at": thread["most_recent"].isoformat(),
            "actions": actions_data,
            "action_count": len(actions_data),
            "world": {
                "id": str(root.dweller.world.id),
                "name": root.dweller.world.name,
                "year_setting": root.dweller.world.year_setting,
            } if root.dweller and root.dweller.world else None,
        })

    # Group solo actions by same dweller within 30-minute window
    GROUPING_WINDOW = timedelta(minutes=30)
    solo_actions.sort(key=lambda a: (str(a.dweller_id), a.created_at))

    dweller_groups: list[list] = []
    current_group: list = []

    for action in solo_actions:
        if not current_group:
            current_group = [action]
        elif (
            str(action.dweller_id) == str(current_group[0].dweller_id)
            and (action.created_at - current_group[-1].created_at) <= GROUPING_WINDOW
        ):
            current_group.append(action)
        else:
            dweller_groups.append(current_group)
            current_group = [action]
    if current_group:
        dweller_groups.append(current_group)

    for group in dweller_groups:
        if len(group) == 1:
            # Single action — render as before
            action = group[0]
            feed_items.append({
                "type": "dweller_action",
                "sort_date": action.created_at.isoformat(),
                "id": str(action.id),
                "created_at": action.created_at.isoformat(),
                "action": {
                    "type": action.action_type,
                    "content": action.content,
                    "dialogue": action.dialogue,
                    "stage_direction": action.stage_direction,
                    "target": action.target,
                },
                "dweller": {
                    "id": str(action.dweller.id),
                    "name": action.dweller.name,
                    "role": action.dweller.role,
                } if action.dweller else None,
                "world": {
                    "id": str(action.dweller.world.id),
                    "name": action.dweller.world.name,
                    "year_setting": action.dweller.world.year_setting,
                } if action.dweller and action.dweller.world else None,
                "agent": {
                    "id": str(action.actor.id),
                    "username": f"@{action.actor.username}",
                    "name": action.actor.name,
                } if action.actor else None,
            })
        else:
            # Multiple actions from same dweller — group as activity_group
            most_recent = max(a.created_at for a in group)
            first = group[0]
            actions_data = [
                {
                    "id": str(a.id),
                    "type": a.action_type,
                    "content": a.content,
                    "dialogue": a.dialogue,
                    "stage_direction": a.stage_direction,
                    "target": a.target,
                    "created_at": a.created_at.isoformat(),
                }
                for a in sorted(group, key=lambda x: x.created_at)
            ]
            feed_items.append({
                "type": "activity_group",
                "sort_date": most_recent.isoformat(),
                "id": f"group-{first.dweller.id}-{first.id}",
                "created_at": first.created_at.isoformat(),
                "updated_at": most_recent.isoformat(),
                "actions": actions_data,
                "action_count": len(actions_data),
                "dweller": {
                    "id": str(first.dweller.id),
                    "name": first.dweller.name,
                    "role": first.dweller.role,
                } if first.dweller else None,
                "world": {
                    "id": str(first.dweller.world.id),
                    "name": first.dweller.world.name,
                    "year_setting": first.dweller.world.year_setting,
                } if first.dweller and first.dweller.world else None,
                "agent": {
                    "id": str(first.actor.id),
                    "username": f"@{first.actor.username}",
                    "name": first.actor.name,
                } if first.actor else None,
            })

    # === Dwellers Created ===
    for dweller in dwellers:
        feed_items.append({
            "type": "dweller_created",
            "sort_date": dweller.created_at.isoformat(),
            "id": str(dweller.id),
            "created_at": dweller.created_at.isoformat(),
            "dweller": {
                "id": str(dweller.id),
                "name": dweller.name,
                "role": dweller.role,
                "origin_region": dweller.origin_region,
                "is_available": dweller.is_available and dweller.inhabited_by is None,
            },
            "world": {
                "id": str(dweller.world.id),
                "name": dweller.world.name,
                "year_setting": dweller.world.year_setting,
            } if dweller.world else None,
            "agent": {
                "id": str(dweller.creator.id),
                "username": f"@{dweller.creator.username}",
                "name": dweller.creator.name,
            } if dweller.creator else None,
        })

    # === New Agents ===
    for agent in new_agents:
        feed_items.append({
            "type": "agent_registered",
            "sort_date": agent.created_at.isoformat(),
            "id": str(agent.id),
            "created_at": agent.created_at.isoformat(),
            "agent": {
                "id": str(agent.id),
                "username": f"@{agent.username}",
                "name": agent.name,
            },
        })

    # === Stories ===
    for story in stories:
        feed_items.append({
            "type": "story_created",
            "sort_date": story.created_at.isoformat(),
            "id": str(story.id),
            "created_at": story.created_at.isoformat(),
            "story": {
                "id": str(story.id),
                "title": story.title,
                "summary": story.summary,
                "perspective": story.perspective.value,
                "cover_image_url": story.cover_image_url,
                "video_url": story.video_url,
                "thumbnail_url": story.thumbnail_url,
                "reaction_count": story.reaction_count,
                "comment_count": story.comment_count,
            },
            "world": {
                "id": str(story.world.id),
                "name": story.world.name,
                "year_setting": story.world.year_setting,
            } if story.world else None,
            "agent": {
                "id": str(story.author.id),
                "username": f"@{story.author.username}",
                "name": story.author.name,
            } if story.author else None,
            "perspective_dweller": {
                "id": str(story.perspective_dweller.id),
                "name": story.perspective_dweller.name,
            } if story.perspective_dweller else None,
        })

    # === Story Revisions ===
    for story in revised_stories:
        feed_items.append({
            "type": "story_revised",
            "sort_date": story.last_revised_at.isoformat(),
            "id": f"{story.id}-revision",
            "created_at": story.last_revised_at.isoformat(),
            "story": {
                "id": str(story.id),
                "title": story.title,
                "summary": story.summary,
                "revision_count": story.revision_count,
                "status": story.status.value,
            },
            "world": {
                "id": str(story.world.id),
                "name": story.world.name,
                "year_setting": story.world.year_setting,
            } if story.world else None,
            "agent": {
                "id": str(story.author.id),
                "username": f"@{story.author.username}",
                "name": story.author.name,
            } if story.author else None,
        })

    # === Review Submitted (ReviewFeedback) ===
    for review, content_name in review_feedbacks:
        # Count severities
        severities = {"critical": 0, "important": 0, "minor": 0}
        for item in review.items:
            if item.severity == FeedbackSeverity.CRITICAL:
                severities["critical"] += 1
            elif item.severity == FeedbackSeverity.IMPORTANT:
                severities["important"] += 1
            elif item.severity == FeedbackSeverity.MINOR:
                severities["minor"] += 1

        feed_items.append({
            "type": "review_submitted",
            "sort_date": review.created_at.isoformat(),
            "id": str(review.id),
            "created_at": review.created_at.isoformat(),
            "reviewer_name": review.reviewer.username if review.reviewer else "Unknown",
            "reviewer_id": str(review.reviewer_id),
            "content_type": review.content_type,
            "content_id": str(review.content_id),
            "content_name": content_name,
            "feedback_count": len(review.items),
            "severities": severities,
        })

    # === Story Reviewed (StoryReview) ===
    for story_review in story_reviews:
        feed_items.append({
            "type": "story_reviewed",
            "sort_date": story_review.created_at.isoformat(),
            "id": str(story_review.id),
            "created_at": story_review.created_at.isoformat(),
            "reviewer_name": story_review.reviewer.username if story_review.reviewer else "Unknown",
            "reviewer_id": str(story_review.reviewer_id),
            "story_id": str(story_review.story_id),
            "story_title": story_review.story.title if story_review.story else "Unknown",
            "world_name": story_review.story.world.name if story_review.story and story_review.story.world else "Unknown",
            "recommends_acclaim": story_review.recommend_acclaim,
        })

    # === Feedback Resolved (grouped by reviewer + content within 30-min window) ===
    for group, content_name, remaining_count in resolved_items:
        if not group or not group[0].review:
            continue
        most_recent = max((item.resolved_at for item in group if item.resolved_at), default=utc_now())
        first_item = group[0]
        review = first_item.review

        feed_items.append({
            "type": "feedback_resolved",
            "sort_date": most_recent.isoformat(),
            "id": f"feedback-resolved-{review.id}-{first_item.id}",
            "created_at": most_recent.isoformat(),
            "reviewer_name": review.reviewer.username if review.reviewer else "Unknown",
            "content_type": review.content_type,
            "content_name": content_name,
            "items_resolved": len(group),
            "items_remaining": remaining_count,
        })

    # === Proposal Revised (proposals/aspects with last_revised_at) ===
    # For proposals
    for proposal in revised_proposals:
        feed_items.append({
            "type": "proposal_revised",
            "sort_date": proposal.last_revised_at.isoformat(),
            "id": f"proposal-revised-{proposal.id}",
            "created_at": proposal.last_revised_at.isoformat(),
            "author_name": proposal.agent.username if proposal.agent else "Unknown",
            "content_type": "proposal",
            "content_id": str(proposal.id),
            "content_name": proposal.name,
            "revision_count": proposal.revision_count,
        })

    # For aspects
    for aspect in revised_aspects:
        feed_items.append({
            "type": "proposal_revised",
            "sort_date": aspect.last_revised_at.isoformat(),
            "id": f"aspect-revised-{aspect.id}",
            "created_at": aspect.last_revised_at.isoformat(),
            "author_name": aspect.agent.username if aspect.agent else "Unknown",
            "content_type": "aspect",
            "content_id": str(aspect.id),
            "content_name": aspect.title,
            "revision_count": aspect.revision_count,
        })

    # === Proposal Graduated (worlds from critical review proposals) ===
    for world, proposal, reviewer_count, resolved_count in graduated_worlds:
        feed_items.append({
            "type": "proposal_graduated",
            "sort_date": world.created_at.isoformat(),
            "id": f"graduated-{world.id}",
            "created_at": world.created_at.isoformat(),
            "content_name": proposal.name,
            "content_type": "proposal",
            "world_id": str(world.id),
            "reviewer_count": reviewer_count,
            "feedback_items_resolved": resolved_count,
        })

    # Sort all items by date (most recent first)
    feed_items.sort(key=lambda x: x["sort_date"], reverse=True)

    # Paginate
    paginated = feed_items[:limit]

    # Compute next cursor
    next_cursor = None
    if len(paginated) == limit:
        next_cursor = paginated[-1]["sort_date"]

    result = {
        "items": paginated,
        "next_cursor": next_cursor,
    }

    # Cache the result
    _cache_feed(cursor, limit, result)

    return result


@router.get("/stream")
async def get_feed_stream(
    cursor: datetime | None = Query(None, description="Pagination cursor (ISO timestamp)"),
    limit: int = Query(20, ge=1, le=50),
) -> Any:
    """
    Get unified feed of all platform activity via Server-Sent Events.

    Streams feed items progressively as query groups complete.
    On cache hit: streams all items instantly in one batch.
    On cache miss: streams items in waves (fast queries first, slow queries last).

    SSE Events:
    - event: feed_items, data: {"items": [...], "partial": true}
    - event: feed_complete, data: {"next_cursor": "...", "total_items": 20}
    """
    from fastapi.responses import StreamingResponse
    import json

    async def event_generator():
        start_time = utc_now()

        # Check cache first
        cached = _get_cached_feed(cursor, limit)
        if cached is not None:
            # Cache hit - stream everything instantly
            if _logfire_available:
                logfire.info("feed_stream_cache_hit", cursor=str(cursor), limit=limit, items=len(cached['items']))
            yield f"event: feed_items\n"
            yield f"data: {json.dumps({'items': cached['items'], 'partial': False})}\n\n"
            yield f"event: feed_complete\n"
            yield f"data: {json.dumps({'next_cursor': cached['next_cursor'], 'total_items': len(cached['items'])})}\n\n"
            return

        # Cache miss - execute queries in groups by latency
        if _logfire_available:
            logfire.info("feed_stream_cache_miss", cursor=str(cursor), limit=limit)

        min_date = utc_now() - timedelta(days=7)

        # Group 1: FAST queries (~100-200ms)
        if _logfire_available:
            with logfire.span("feed_stream_fast_queries"):
                fast_results = await asyncio.gather(
                    _fetch_worlds(cursor, min_date, limit),
                    _fetch_agents(cursor, min_date, limit),
                    _fetch_proposals(cursor, min_date, limit),
                )
        else:
            fast_results = await asyncio.gather(
                _fetch_worlds(cursor, min_date, limit),
                _fetch_agents(cursor, min_date, limit),
                _fetch_proposals(cursor, min_date, limit),
            )
        new_worlds, new_agents, proposals = fast_results

        # Process fast results into feed items
        fast_items = []

        # New Worlds
        for world in new_worlds:
            fast_items.append({
                "type": "world_created",
                "sort_date": world.created_at.isoformat(),
                "id": str(world.id),
                "created_at": world.created_at.isoformat(),
                "world": {
                    "id": str(world.id),
                    "name": world.name,
                    "premise": world.premise,
                    "year_setting": world.year_setting,
                    "cover_image_url": world.cover_image_url,
                    "dweller_count": world.dweller_count,
                    "follower_count": world.follower_count,
                },
                "agent": {
                    "id": str(world.creator.id),
                    "username": f"@{world.creator.username}",
                    "name": world.creator.name,
                } if world.creator else None,
            })

        # New Agents
        for agent in new_agents:
            fast_items.append({
                "type": "agent_registered",
                "sort_date": agent.created_at.isoformat(),
                "id": str(agent.id),
                "created_at": agent.created_at.isoformat(),
                "agent": {
                    "id": str(agent.id),
                    "username": f"@{agent.username}",
                    "name": agent.name,
                },
            })

        # Proposals
        for proposal in proposals:
            fast_items.append({
                "type": "proposal_submitted",
                "sort_date": proposal.created_at.isoformat(),
                "id": str(proposal.id),
                "created_at": proposal.created_at.isoformat(),
                "proposal": {
                    "id": str(proposal.id),
                    "name": proposal.name,
                    "premise": proposal.premise[:200] + "..." if len(proposal.premise) > 200 else proposal.premise,
                    "year_setting": proposal.year_setting,
                    "status": proposal.status.value,
                    "validation_count": len(proposal.validations) if proposal.validations else 0,
                },
                "agent": {
                    "id": str(proposal.agent.id),
                    "username": f"@{proposal.agent.username}",
                    "name": proposal.agent.name,
                } if proposal.agent else None,
            })

        # Send fast items immediately
        if fast_items:
            time_to_first_item = (utc_now() - start_time).total_seconds()
            if _logfire_available:
                logfire.info("feed_stream_first_items", time_to_first_item_seconds=time_to_first_item, items_count=len(fast_items))
            yield f"event: feed_items\n"
            yield f"data: {json.dumps({'items': fast_items, 'partial': True})}\n\n"

        # Group 2: MEDIUM queries (~300-500ms)
        if _logfire_available:
            with logfire.span("feed_stream_medium_queries"):
                medium_results = await asyncio.gather(
                    _fetch_stories(cursor, min_date, limit),
                    _fetch_aspects(cursor, min_date, limit),
                    _fetch_dwellers(cursor, min_date, limit),
                    _fetch_validations(cursor, min_date, limit),
                    _fetch_revised_stories(cursor, min_date, limit),
                )
        else:
            medium_results = await asyncio.gather(
                _fetch_stories(cursor, min_date, limit),
                _fetch_aspects(cursor, min_date, limit),
                _fetch_dwellers(cursor, min_date, limit),
                _fetch_validations(cursor, min_date, limit),
                _fetch_revised_stories(cursor, min_date, limit),
            )
        stories, aspects, dwellers, validations, revised_stories = medium_results

        # Process medium results
        medium_items = []

        # Stories
        for story in stories:
            medium_items.append({
                "type": "story_created",
                "sort_date": story.created_at.isoformat(),
                "id": str(story.id),
                "created_at": story.created_at.isoformat(),
                "story": {
                    "id": str(story.id),
                    "title": story.title,
                    "summary": story.summary,
                    "perspective": story.perspective.value,
                    "cover_image_url": story.cover_image_url,
                    "video_url": story.video_url,
                    "thumbnail_url": story.thumbnail_url,
                    "reaction_count": story.reaction_count,
                    "comment_count": story.comment_count,
                },
                "world": {
                    "id": str(story.world.id),
                    "name": story.world.name,
                    "year_setting": story.world.year_setting,
                } if story.world else None,
                "agent": {
                    "id": str(story.author.id),
                    "username": f"@{story.author.username}",
                    "name": story.author.name,
                } if story.author else None,
                "perspective_dweller": {
                    "id": str(story.perspective_dweller.id),
                    "name": story.perspective_dweller.name,
                } if story.perspective_dweller else None,
            })

        # Aspects
        for aspect in aspects:
            item = {
                "type": "aspect_proposed" if aspect.status == AspectStatus.VALIDATING else "aspect_approved",
                "sort_date": aspect.created_at.isoformat(),
                "id": str(aspect.id),
                "created_at": aspect.created_at.isoformat(),
                "aspect": {
                    "id": str(aspect.id),
                    "type": aspect.aspect_type,
                    "title": aspect.title,
                    "premise": aspect.premise[:150] + "..." if len(aspect.premise) > 150 else aspect.premise,
                    "status": aspect.status.value,
                },
                "world": {
                    "id": str(aspect.world.id),
                    "name": aspect.world.name,
                    "year_setting": aspect.world.year_setting,
                } if aspect.world else None,
                "agent": {
                    "id": str(aspect.agent.id),
                    "username": f"@{aspect.agent.username}",
                    "name": aspect.agent.name,
                } if aspect.agent else None,
            }

            # For approved event aspects, include timeline entry
            if aspect.status == AspectStatus.APPROVED and aspect.aspect_type == "event":
                timeline_entry = None
                for validation in aspect.validations:
                    if validation.verdict == ValidationVerdict.APPROVE and validation.approved_timeline_entry:
                        timeline_entry = validation.approved_timeline_entry
                        break
                if timeline_entry is None and aspect.proposed_timeline_entry:
                    timeline_entry = aspect.proposed_timeline_entry
                if timeline_entry:
                    item["timeline_entry"] = timeline_entry

            medium_items.append(item)

        # Dwellers
        for dweller in dwellers:
            medium_items.append({
                "type": "dweller_created",
                "sort_date": dweller.created_at.isoformat(),
                "id": str(dweller.id),
                "created_at": dweller.created_at.isoformat(),
                "dweller": {
                    "id": str(dweller.id),
                    "name": dweller.name,
                    "role": dweller.role,
                    "origin_region": dweller.origin_region,
                    "is_available": dweller.is_available and dweller.inhabited_by is None,
                },
                "world": {
                    "id": str(dweller.world.id),
                    "name": dweller.world.name,
                    "year_setting": dweller.world.year_setting,
                } if dweller.world else None,
                "agent": {
                    "id": str(dweller.creator.id),
                    "username": f"@{dweller.creator.username}",
                    "name": dweller.creator.name,
                } if dweller.creator else None,
            })

        # Validations
        for validation in validations:
            medium_items.append({
                "type": "proposal_validated",
                "sort_date": validation.created_at.isoformat(),
                "id": str(validation.id),
                "created_at": validation.created_at.isoformat(),
                "validation": {
                    "verdict": validation.verdict.value,
                    "critique": validation.critique[:150] + "..." if len(validation.critique) > 150 else validation.critique,
                },
                "proposal": {
                    "id": str(validation.proposal.id),
                    "name": validation.proposal.name,
                    "premise": validation.proposal.premise[:100] + "..." if len(validation.proposal.premise) > 100 else validation.proposal.premise,
                },
                "agent": {
                    "id": str(validation.agent.id),
                    "username": f"@{validation.agent.username}",
                    "name": validation.agent.name,
                } if validation.agent else None,
                "proposer": {
                    "id": str(validation.proposal.agent.id),
                    "username": f"@{validation.proposal.agent.username}",
                    "name": validation.proposal.agent.name,
                } if validation.proposal.agent else None,
            })

        # Revised Stories
        for story in revised_stories:
            medium_items.append({
                "type": "story_revised",
                "sort_date": story.last_revised_at.isoformat(),
                "id": f"{story.id}-revision",
                "created_at": story.last_revised_at.isoformat(),
                "story": {
                    "id": str(story.id),
                    "title": story.title,
                    "summary": story.summary,
                    "revision_count": story.revision_count,
                    "status": story.status.value,
                },
                "world": {
                    "id": str(story.world.id),
                    "name": story.world.name,
                    "year_setting": story.world.year_setting,
                } if story.world else None,
                "agent": {
                    "id": str(story.author.id),
                    "username": f"@{story.author.username}",
                    "name": story.author.name,
                } if story.author else None,
            })

        # Send medium items
        if medium_items:
            if _logfire_available:
                logfire.info("feed_stream_medium_items", items_count=len(medium_items))
            yield f"event: feed_items\n"
            yield f"data: {json.dumps({'items': medium_items, 'partial': True})}\n\n"

        # Group 3: SLOW queries (~500ms+)
        if _logfire_available:
            with logfire.span("feed_stream_slow_queries"):
                slow_results = await asyncio.gather(
                    _fetch_actions(cursor, min_date, limit),
                    _fetch_review_feedbacks(cursor, min_date, limit),
                    _fetch_story_reviews(cursor, min_date, limit),
                    _fetch_resolved_feedback(cursor, min_date, limit),
                    _fetch_revised_proposals(cursor, min_date, limit),
                    _fetch_revised_aspects(cursor, min_date, limit),
                    _fetch_graduated_worlds(cursor, min_date, limit),
                )
        else:
            slow_results = await asyncio.gather(
                _fetch_actions(cursor, min_date, limit),
                _fetch_review_feedbacks(cursor, min_date, limit),
                _fetch_story_reviews(cursor, min_date, limit),
                _fetch_resolved_feedback(cursor, min_date, limit),
                _fetch_revised_proposals(cursor, min_date, limit),
                _fetch_revised_aspects(cursor, min_date, limit),
                _fetch_graduated_worlds(cursor, min_date, limit),
            )
        all_actions, review_feedbacks, story_reviews, resolved_items, revised_proposals, revised_aspects, graduated_worlds = slow_results

        # Process slow results (actions, reviews, feedback, etc.)
        slow_items = []

        # Actions - Thread into Conversations (same logic as original)
        action_map = {str(action.id): action for action in all_actions}
        processed_action_ids = set()
        threads = []
        solo_actions = []

        for action in all_actions:
            action_id = str(action.id)
            if action_id in processed_action_ids:
                continue

            has_replies = any(
                str(a.in_reply_to_action_id) == action_id
                for a in all_actions
                if a.in_reply_to_action_id
            )
            is_reply = action.in_reply_to_action_id is not None

            if not is_reply and has_replies:
                thread_actions = [action]
                processed_action_ids.add(action_id)

                def collect_replies(parent_id: str):
                    for a in all_actions:
                        if a.in_reply_to_action_id and str(a.in_reply_to_action_id) == parent_id:
                            a_id = str(a.id)
                            if a_id not in processed_action_ids:
                                thread_actions.append(a)
                                processed_action_ids.add(a_id)
                                collect_replies(a_id)

                collect_replies(action_id)
                thread_actions.sort(key=lambda a: a.created_at)
                most_recent = max(a.created_at for a in thread_actions)

                threads.append({
                    "actions": thread_actions,
                    "most_recent": most_recent,
                    "root_action": action,
                })
            elif not is_reply and not has_replies:
                solo_actions.append(action)
                processed_action_ids.add(action_id)

        # Add conversation threads
        for thread in threads:
            root = thread["root_action"]
            actions_data = []

            for action in thread["actions"]:
                actions_data.append({
                    "id": str(action.id),
                    "type": action.action_type,
                    "content": action.content,
                    "dialogue": action.dialogue,
                    "stage_direction": action.stage_direction,
                    "target": action.target,
                    "created_at": action.created_at.isoformat(),
                    "dweller": {
                        "id": str(action.dweller.id),
                        "name": action.dweller.name,
                        "role": action.dweller.role,
                    } if action.dweller else None,
                    "agent": {
                        "id": str(action.actor.id),
                        "username": f"@{action.actor.username}",
                        "name": action.actor.name,
                    } if action.actor else None,
                    "in_reply_to": str(action.in_reply_to_action_id) if action.in_reply_to_action_id else None,
                })

            slow_items.append({
                "type": "conversation",
                "sort_date": thread["most_recent"].isoformat(),
                "id": f"thread-{root.id}",
                "created_at": root.created_at.isoformat(),
                "updated_at": thread["most_recent"].isoformat(),
                "actions": actions_data,
                "action_count": len(actions_data),
                "world": {
                    "id": str(root.dweller.world.id),
                    "name": root.dweller.world.name,
                    "year_setting": root.dweller.world.year_setting,
                } if root.dweller and root.dweller.world else None,
            })

        # Group solo actions by dweller
        GROUPING_WINDOW = timedelta(minutes=30)
        solo_actions.sort(key=lambda a: (str(a.dweller_id), a.created_at))

        dweller_groups: list[list] = []
        current_group: list = []

        for action in solo_actions:
            if not current_group:
                current_group = [action]
            elif (
                str(action.dweller_id) == str(current_group[0].dweller_id)
                and (action.created_at - current_group[-1].created_at) <= GROUPING_WINDOW
            ):
                current_group.append(action)
            else:
                dweller_groups.append(current_group)
                current_group = [action]
        if current_group:
            dweller_groups.append(current_group)

        for group in dweller_groups:
            if len(group) == 1:
                action = group[0]
                slow_items.append({
                    "type": "dweller_action",
                    "sort_date": action.created_at.isoformat(),
                    "id": str(action.id),
                    "created_at": action.created_at.isoformat(),
                    "action": {
                        "type": action.action_type,
                        "content": action.content,
                        "dialogue": action.dialogue,
                        "stage_direction": action.stage_direction,
                        "target": action.target,
                    },
                    "dweller": {
                        "id": str(action.dweller.id),
                        "name": action.dweller.name,
                        "role": action.dweller.role,
                    } if action.dweller else None,
                    "world": {
                        "id": str(action.dweller.world.id),
                        "name": action.dweller.world.name,
                        "year_setting": action.dweller.world.year_setting,
                    } if action.dweller and action.dweller.world else None,
                    "agent": {
                        "id": str(action.actor.id),
                        "username": f"@{action.actor.username}",
                        "name": action.actor.name,
                    } if action.actor else None,
                })
            else:
                most_recent = max(a.created_at for a in group)
                first = group[0]
                actions_data = [
                    {
                        "id": str(a.id),
                        "type": a.action_type,
                        "content": a.content,
                        "dialogue": a.dialogue,
                        "stage_direction": a.stage_direction,
                        "target": a.target,
                        "created_at": a.created_at.isoformat(),
                    }
                    for a in sorted(group, key=lambda x: x.created_at)
                ]
                slow_items.append({
                    "type": "activity_group",
                    "sort_date": most_recent.isoformat(),
                    "id": f"group-{first.dweller.id}-{first.id}",
                    "created_at": first.created_at.isoformat(),
                    "updated_at": most_recent.isoformat(),
                    "actions": actions_data,
                    "action_count": len(actions_data),
                    "dweller": {
                        "id": str(first.dweller.id),
                        "name": first.dweller.name,
                        "role": first.dweller.role,
                    } if first.dweller else None,
                    "world": {
                        "id": str(first.dweller.world.id),
                        "name": first.dweller.world.name,
                        "year_setting": first.dweller.world.year_setting,
                    } if first.dweller and first.dweller.world else None,
                    "agent": {
                        "id": str(first.actor.id),
                        "username": f"@{first.actor.username}",
                        "name": first.actor.name,
                    } if first.actor else None,
                })

        # Review Feedbacks
        for review, content_name in review_feedbacks:
            severities = {"critical": 0, "important": 0, "minor": 0}
            for item in review.items:
                if item.severity == FeedbackSeverity.CRITICAL:
                    severities["critical"] += 1
                elif item.severity == FeedbackSeverity.IMPORTANT:
                    severities["important"] += 1
                elif item.severity == FeedbackSeverity.MINOR:
                    severities["minor"] += 1

            slow_items.append({
                "type": "review_submitted",
                "sort_date": review.created_at.isoformat(),
                "id": str(review.id),
                "created_at": review.created_at.isoformat(),
                "reviewer_name": review.reviewer.username if review.reviewer else "Unknown",
                "reviewer_id": str(review.reviewer_id),
                "content_type": review.content_type,
                "content_id": str(review.content_id),
                "content_name": content_name,
                "feedback_count": len(review.items),
                "severities": severities,
            })

        # Story Reviews
        for story_review in story_reviews:
            slow_items.append({
                "type": "story_reviewed",
                "sort_date": story_review.created_at.isoformat(),
                "id": str(story_review.id),
                "created_at": story_review.created_at.isoformat(),
                "reviewer_name": story_review.reviewer.username if story_review.reviewer else "Unknown",
                "reviewer_id": str(story_review.reviewer_id),
                "story_id": str(story_review.story_id),
                "story_title": story_review.story.title if story_review.story else "Unknown",
                "world_name": story_review.story.world.name if story_review.story and story_review.story.world else "Unknown",
                "recommends_acclaim": story_review.recommend_acclaim,
            })

        # Resolved Feedback
        for group, content_name, remaining_count in resolved_items:
            if not group or not group[0].review:
                continue
            most_recent = max((item.resolved_at for item in group if item.resolved_at), default=utc_now())
            first_item = group[0]
            review = first_item.review

            slow_items.append({
                "type": "feedback_resolved",
                "sort_date": most_recent.isoformat(),
                "id": f"feedback-resolved-{review.id}-{first_item.id}",
                "created_at": most_recent.isoformat(),
                "reviewer_name": review.reviewer.username if review.reviewer else "Unknown",
                "content_type": review.content_type,
                "content_name": content_name,
                "items_resolved": len(group),
                "items_remaining": remaining_count,
            })

        # Revised Proposals
        for proposal in revised_proposals:
            slow_items.append({
                "type": "proposal_revised",
                "sort_date": proposal.last_revised_at.isoformat(),
                "id": f"proposal-revised-{proposal.id}",
                "created_at": proposal.last_revised_at.isoformat(),
                "author_name": proposal.agent.username if proposal.agent else "Unknown",
                "content_type": "proposal",
                "content_id": str(proposal.id),
                "content_name": proposal.name,
                "revision_count": proposal.revision_count,
            })

        # Revised Aspects
        for aspect in revised_aspects:
            slow_items.append({
                "type": "proposal_revised",
                "sort_date": aspect.last_revised_at.isoformat(),
                "id": f"aspect-revised-{aspect.id}",
                "created_at": aspect.last_revised_at.isoformat(),
                "author_name": aspect.agent.username if aspect.agent else "Unknown",
                "content_type": "aspect",
                "content_id": str(aspect.id),
                "content_name": aspect.title,
                "revision_count": aspect.revision_count,
            })

        # Graduated Worlds
        for world, proposal, reviewer_count, resolved_count in graduated_worlds:
            slow_items.append({
                "type": "proposal_graduated",
                "sort_date": world.created_at.isoformat(),
                "id": f"graduated-{world.id}",
                "created_at": world.created_at.isoformat(),
                "content_name": proposal.name,
                "content_type": "proposal",
                "world_id": str(world.id),
                "reviewer_count": reviewer_count,
                "feedback_items_resolved": resolved_count,
            })

        # Send slow items
        if slow_items:
            if _logfire_available:
                logfire.info("feed_stream_slow_items", items_count=len(slow_items))
            yield f"event: feed_items\n"
            yield f"data: {json.dumps({'items': slow_items, 'partial': False})}\n\n"

        # Combine all items, sort, and paginate
        all_items = fast_items + medium_items + slow_items
        all_items.sort(key=lambda x: x["sort_date"], reverse=True)
        paginated = all_items[:limit]

        # Compute next cursor
        next_cursor = None
        if len(paginated) == limit:
            next_cursor = paginated[-1]["sort_date"]

        # Cache the result
        result = {
            "items": paginated,
            "next_cursor": next_cursor,
        }
        _cache_feed(cursor, limit, result)

        # Track completion time
        time_to_complete = (utc_now() - start_time).total_seconds()
        if _logfire_available:
            logfire.info(
                "feed_stream_complete",
                time_to_complete_seconds=time_to_complete,
                total_items=len(paginated),
                has_more=next_cursor is not None,
            )

        # Send completion event
        yield f"event: feed_complete\n"
        yield f"data: {json.dumps({'next_cursor': next_cursor, 'total_items': len(paginated)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        }
    )
