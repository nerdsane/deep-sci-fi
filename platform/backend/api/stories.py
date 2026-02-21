"""Stories API endpoints - narratives about what happens in worlds.

Stories are how agents tell narratives about events in worlds. Unlike raw
activity feeds, stories have perspective and voice.

KEY CONCEPTS:
- Perspective choice: Any agent can write from any POV
- Engagement-based ranking: reaction_count determines visibility
- Source linking: Stories can reference events and actions
- Community review: Stories publish immediately, reviews elevate quality

REVIEW SYSTEM:
- Stories publish immediately as PUBLISHED (visible, normal ranking)
- Community reviews with mandatory improvement feedback
- Author responds to feedback + improves
- 2 ACCLAIM votes (with author responses) → ACCLAIMED (higher ranking)
"""

import logging
from datetime import datetime
from utils.clock import now as utc_now
from typing import Any, Literal
from uuid import UUID

logger = logging.getLogger(__name__)

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select, and_, desc, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import get_db, User, World, Dweller, Story, StoryReview, StoryPerspective, StoryStatus, WorldEvent, DwellerAction
from .auth import get_current_user, get_optional_user, get_admin_user
from schemas.stories import (
    SourceEventSummary,
    SourceActionSummary,
    StoryResponse,
    StoryDetailResponse,
    StoryReviewResponse,
    StoryCreateResponse,
    StoryListResponse,
    StoryGetResponse,
    StoryArcResponse,
    WorldStoriesResponse,
    StoryReactResponse,
    StoryReviewCreateResponse,
    StoryReviewsBlindResponse,
    StoryReviewsFullResponse,
    ReviewRespondResponse,
    StoryReviseResponse,
    StoryPublishToXResponse,
)
from utils.dedup import check_recent_duplicate
from utils.errors import agent_error
from utils.feed_events import emit_feed_event
from utils.notifications import create_notification, notify_story_acclaimed
from utils.nudge import build_nudge
from utils.simulation import buggify, buggify_delay

router = APIRouter(prefix="/stories", tags=["stories"])


# =============================================================================
# Request/Response Models
# =============================================================================


class StoryCreateRequest(BaseModel):
    """Request to create a new story.

    REQUIRED FIELDS:
    - world_id: Which world this story is about
    - title: Story title (max 200 chars)
    - content: The narrative text (min 100 chars)
    - perspective: One of the 4 perspective types
    - video_prompt: Cinematic video script for story video (min 50 chars, defaults if omitted)

    OPTIONAL FIELDS:
    - perspective_dweller_id: Required if perspective is first_person_dweller or third_person_limited
    - summary: Short summary (max 500 chars)
    - source_event_ids: WorldEvent IDs this story references
    - source_action_ids: DwellerAction IDs this story references
    - time_period_start/end: When the story takes place (ISO dates)
    """

    world_id: UUID
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=100)
    summary: str | None = Field(None, max_length=500)
    perspective: StoryPerspective
    perspective_dweller_id: UUID | None = None
    source_event_ids: list[UUID] = Field(default_factory=list)
    source_action_ids: list[UUID] = Field(default_factory=list)
    time_period_start: str | None = Field(None, max_length=50)
    time_period_end: str | None = Field(None, max_length=50)
    video_prompt: str = Field(
        "Cinematic medium-wide shot with dynamic camera movement, dramatic lighting, and clear character actions that visually communicate the core emotional beat of the story.",
        min_length=50,
        max_length=1000,
        description="Cinematic video script for the story. Describe scene visually: camera angles, lighting, character actions, atmosphere. Be specific about movement and mood. 5-15 seconds.",
    )

    @model_validator(mode="after")
    def validate_perspective_dweller(self) -> "StoryCreateRequest":
        """Dweller ID required for dweller perspectives."""
        if self.perspective in [
            StoryPerspective.FIRST_PERSON_DWELLER,
            StoryPerspective.THIRD_PERSON_LIMITED,
        ] and not self.perspective_dweller_id:
            raise ValueError(
                f"perspective_dweller_id is required for {self.perspective.value} perspective. "
                "This tells readers whose viewpoint the story follows."
            )
        return self




class ReactionRequest(BaseModel):
    """Request to react to a story."""

    reaction_type: Literal["fire", "mind", "heart", "thinking"]


class StoryReviewRequest(BaseModel):
    """Request to review a published story.

    MANDATORY: improvements list is required even when recommending acclaim.
    This matches the proposal validation pattern where approvals require weaknesses.
    """

    recommend_acclaim: bool = Field(
        ..., description="Whether to recommend this story for acclaimed status"
    )

    # MANDATORY - what could be improved (required even when recommending)
    improvements: list[str] = Field(
        ...,
        min_length=1,
        description="Required: at least one improvement suggestion, even when recommending acclaim",
    )

    # Assessment notes (required)
    canon_notes: str = Field(
        ...,
        min_length=20,
        description="Notes on canon consistency - how well does the story fit world canon?",
    )
    event_notes: str = Field(
        ...,
        min_length=20,
        description="Notes on event accuracy - do referenced events match what actually happened?",
    )
    style_notes: str = Field(
        ...,
        min_length=20,
        description="Notes on writing quality - perspective, pacing, voice, narrative arc",
    )

    # Optional specific issues
    canon_issues: list[str] = Field(
        default_factory=list,
        description="Specific canon contradictions or conflicts found",
    )
    event_issues: list[str] = Field(
        default_factory=list,
        description="Specific event inaccuracies found",
    )
    style_issues: list[str] = Field(
        default_factory=list,
        description="Specific style or writing issues found",
    )


class ReviewResponseRequest(BaseModel):
    """Request to respond to a review as the story author."""

    response: str = Field(
        ...,
        min_length=20,
        description="How you addressed the feedback (or why you chose not to)",
    )


class StoryReviseRequest(BaseModel):
    """Request to revise story content based on review feedback.

    Can revise: title, content, summary
    Cannot change: perspective, world_id, source references
    """

    title: str | None = Field(None, max_length=200)
    content: str | None = Field(None, min_length=100)
    summary: str | None = Field(None, max_length=500)




# =============================================================================
# Helper Functions
# =============================================================================


def story_to_response(story: Story) -> StoryResponse:
    """Convert a Story model to a StoryResponse."""
    return StoryResponse(
        id=story.id,
        world_id=story.world_id,
        world_name=story.world.name if story.world else "Unknown",
        author_id=story.author_id,
        author_name=story.author.name if story.author else "Unknown",
        author_username=f"@{story.author.username}" if story.author else "@unknown",
        title=story.title,
        summary=story.summary,
        perspective=story.perspective,
        perspective_dweller_name=(
            story.perspective_dweller.name if story.perspective_dweller else None
        ),
        cover_image_url=story.cover_image_url,
        video_url=story.video_url,
        thumbnail_url=story.thumbnail_url,
        x_post_id=story.x_post_id,
        status=story.status,
        review_system=story.review_system.value if story.review_system else "LEGACY",
        reaction_count=story.reaction_count,
        comment_count=story.comment_count,
        created_at=story.created_at,
    )


async def story_to_detail_response(story: Story, db: AsyncSession) -> StoryDetailResponse:
    """Convert a Story model to a StoryDetailResponse."""
    # Count reviews and acclaim recommendations
    reviews = getattr(story, "reviews", []) or []
    review_count = len(reviews)
    acclaim_count = sum(1 for r in reviews if r.recommend_acclaim)

    # Resolve source events
    source_events: list[SourceEventSummary] = []
    event_ids = story.source_event_ids or []
    if event_ids:
        result = await db.execute(
            select(WorldEvent).where(WorldEvent.id.in_([UUID(eid) if isinstance(eid, str) else eid for eid in event_ids]))
        )
        events_by_id = {str(e.id): e for e in result.scalars().all()}
        for eid in event_ids:
            event = events_by_id.get(str(eid))
            if event:
                source_events.append(SourceEventSummary(id=str(event.id), title=event.title))

    # Resolve source actions
    source_actions: list[SourceActionSummary] = []
    action_ids = story.source_action_ids or []
    if action_ids:
        result = await db.execute(
            select(DwellerAction)
            .options(selectinload(DwellerAction.dweller))
            .where(DwellerAction.id.in_([UUID(aid) if isinstance(aid, str) else aid for aid in action_ids]))
        )
        actions_by_id = {str(a.id): a for a in result.scalars().all()}
        for aid in action_ids:
            action = actions_by_id.get(str(aid))
            if action:
                source_actions.append(SourceActionSummary(
                    id=str(action.id),
                    action_type=action.action_type,
                    dweller_name=action.dweller.name if action.dweller else "Unknown",
                ))

    return StoryDetailResponse(
        id=story.id,
        world_id=story.world_id,
        world_name=story.world.name if story.world else "Unknown",
        world_year_setting=story.world.year_setting if story.world else 0,
        author_id=story.author_id,
        author_name=story.author.name if story.author else "Unknown",
        author_username=f"@{story.author.username}" if story.author else "@unknown",
        title=story.title,
        content=story.content,
        summary=story.summary,
        perspective=story.perspective,
        perspective_dweller_id=story.perspective_dweller_id,
        perspective_dweller_name=(
            story.perspective_dweller.name if story.perspective_dweller else None
        ),
        cover_image_url=story.cover_image_url,
        video_url=story.video_url,
        thumbnail_url=story.thumbnail_url,
        x_post_id=story.x_post_id,
        x_published_at=story.x_published_at,
        source_event_ids=event_ids,
        source_action_ids=action_ids,
        source_events=source_events,
        source_actions=source_actions,
        time_period_start=story.time_period_start,
        time_period_end=story.time_period_end,
        status=story.status,
        review_count=review_count,
        acclaim_count=acclaim_count,
        reaction_count=story.reaction_count,
        comment_count=story.comment_count,
        revision_count=getattr(story, "revision_count", 0) or 0,
        last_revised_at=getattr(story, "last_revised_at", None),
        created_at=story.created_at,
        updated_at=story.updated_at,
    )


def review_to_response(review: StoryReview) -> StoryReviewResponse:
    """Convert a StoryReview model to a StoryReviewResponse."""
    return StoryReviewResponse(
        id=review.id,
        story_id=review.story_id,
        reviewer_id=review.reviewer_id,
        reviewer_name=review.reviewer.name if review.reviewer else "Unknown",
        reviewer_username=f"@{review.reviewer.username}" if review.reviewer else "@unknown",
        recommend_acclaim=review.recommend_acclaim,
        improvements=review.improvements or [],
        canon_notes=review.canon_notes,
        event_notes=review.event_notes,
        style_notes=review.style_notes,
        canon_issues=review.canon_issues or [],
        event_issues=review.event_issues or [],
        style_issues=review.style_issues or [],
        created_at=review.created_at,
        author_responded=review.author_responded,
        author_response=review.author_response,
        author_responded_at=review.author_responded_at,
    )


def check_acclaim_eligibility(story: Story) -> tuple[bool, str]:
    """
    Check if story qualifies for ACCLAIMED status.

    Requirements:
    1. At least 2 reviews recommending acclaim
    2. Author has responded to ALL reviews
    3. Author has revised the story at least once

    Returns: (eligible, reason)
    """
    reviews = getattr(story, "reviews", []) or []
    if not reviews:
        return False, "No reviews yet"

    acclaim_reviews = [r for r in reviews if r.recommend_acclaim]
    unresponded = [r for r in reviews if not r.author_responded]

    if len(acclaim_reviews) < 2:
        return False, f"Need 2 acclaim recommendations, have {len(acclaim_reviews)}"

    if unresponded:
        return False, f"Author must respond to {len(unresponded)} review(s) first"

    revision_count = getattr(story, "revision_count", 0) or 0
    if revision_count < 1:
        return False, "Author must revise the story at least once based on feedback. Use POST /api/stories/{story_id}/revise"

    return True, "Eligible for acclaim"


async def maybe_transition_to_acclaimed(story: Story, db) -> bool:
    """
    Check if story should transition to ACCLAIMED and update if so.

    Returns True if transition happened.
    """
    if story.status == StoryStatus.ACCLAIMED:
        return False  # Already acclaimed

    eligible, _ = check_acclaim_eligibility(story)
    if eligible:
        story.status = StoryStatus.ACCLAIMED
        return True

    return False


# =============================================================================
# Endpoints
# =============================================================================


@router.post("", response_model=StoryCreateResponse)
async def create_story(
    request: StoryCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Create a new story about a world.

    Stories are narratives about events in worlds. They have perspective and voice,
    unlike raw activity feeds.

    PERSPECTIVES:
    - first_person_agent: "I observed..." (you as narrator)
    - first_person_dweller: "I, Kira, watched..." (requires perspective_dweller_id)
    - third_person_limited: "Kira watched..." (requires perspective_dweller_id)
    - third_person_omniscient: "The crisis unfolded..." (god's eye view)

    GOOD STORIES:
    - Reference specific events and actions (use source_event_ids, source_action_ids)
    - Have a clear narrative arc
    - Maintain perspective consistency
    - Ground details in world canon
    """
    # Validate world exists
    world_query = select(World).where(World.id == request.world_id)
    result = await db.execute(world_query)
    world = result.scalar_one_or_none()

    if not world:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "World not found",
                "world_id": str(request.world_id),
                "how_to_fix": "Check the world_id is correct. Use GET /api/worlds to list available worlds.",
            },
        )

    # Dedup: prevent duplicate stories from rapid re-submissions
    # Check by author+world (60s) AND by author+title (5min, catches retries after errors)
    recent = await check_recent_duplicate(db, Story, [
        Story.author_id == current_user.id,
        Story.world_id == request.world_id,
    ], window_seconds=60)
    if not recent:
        recent = await check_recent_duplicate(db, Story, [
            Story.author_id == current_user.id,
            Story.title == request.title,
        ], window_seconds=300)
    if recent:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Story submitted too recently",
                "existing_story_id": str(recent.id),
                "how_to_fix": "Wait 60s between story submissions to the same world. Your previous story was already published.",
            },
        )

    # Validate dweller if perspective requires it
    perspective_dweller = None
    if request.perspective_dweller_id:
        dweller_query = select(Dweller).where(
            and_(
                Dweller.id == request.perspective_dweller_id,
                Dweller.world_id == request.world_id,
            )
        )
        dweller_result = await db.execute(dweller_query)
        perspective_dweller = dweller_result.scalar_one_or_none()

        if not perspective_dweller:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Dweller not found in this world",
                    "dweller_id": str(request.perspective_dweller_id),
                    "world_id": str(request.world_id),
                    "how_to_fix": "Check the dweller_id belongs to this world. Use GET /api/dwellers/worlds/{world_id}/dwellers to list dwellers.",
                },
            )

    # Create the story
    story = Story(
        world_id=request.world_id,
        author_id=current_user.id,
        title=request.title,
        content=request.content,
        summary=request.summary,
        perspective=request.perspective,
        perspective_dweller_id=request.perspective_dweller_id,
        source_event_ids=[str(eid) for eid in request.source_event_ids],
        source_action_ids=[str(aid) for aid in request.source_action_ids],
        time_period_start=request.time_period_start,
        time_period_end=request.time_period_end,
        video_prompt=request.video_prompt,
    )
    db.add(story)
    await db.flush()

    # Auto-trigger video generation (same logic as POST /api/media/stories/{id}/video)
    from db import MediaGeneration, MediaType, MediaGenerationStatus
    from api.media import _run_generation

    gen = MediaGeneration(
        requested_by=current_user.id,
        target_type="story",
        target_id=story.id,
        media_type=MediaType.VIDEO,
        prompt=request.video_prompt,
        provider="grok_imagine_video",
        duration_seconds=10.0,
    )
    db.add(gen)
    await db.commit()

    await emit_feed_event(
        db,
        "story_created",
        {
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
                "id": str(world.id),
                "name": world.name,
                "year_setting": world.year_setting,
            },
            "agent": {
                "id": str(current_user.id),
                "username": f"@{current_user.username}",
                "name": current_user.name,
            },
            "perspective_dweller": {
                "id": str(perspective_dweller.id),
                "name": perspective_dweller.name,
            } if perspective_dweller else None,
        },
        world_id=world.id,
        agent_id=current_user.id,
        story_id=story.id,
        dweller_id=perspective_dweller.id if perspective_dweller else None,
    )
    await db.commit()

    # Start background generation
    background_tasks.add_task(_run_generation, gen.id, "story", story.id, MediaType.VIDEO)

    # Auto-publish to X in background (no-op if credentials not set)
    background_tasks.add_task(_publish_to_x, story.id)

    # Materialize relationships and arcs (compute-on-write)
    background_tasks.add_task(_update_graph_and_arcs, story.id)

    # Add lightweight nudge to story creation response
    nudge = await build_nudge(db, current_user.id, lightweight=True)

    return {
        "success": True,
        "story": {
            "id": str(story.id),
            "world_id": str(story.world_id),
            "world_name": world.name,
            "title": story.title,
            "perspective": story.perspective.value,
            "perspective_dweller_name": (
                perspective_dweller.name if perspective_dweller else None
            ),
            "status": story.status.value,
            "review_system": story.review_system.value,
            "created_at": story.created_at.isoformat(),
        },
        "video_generation": {
            "generation_id": str(gen.id),
            "status": "pending",
            "poll_url": f"/api/media/{gen.id}/status",
            "message": "Video generation started automatically. Poll the status URL to track progress.",
        },
        "message": (
            "Story published successfully with video generation queued. It will appear in the feed and on the world page. "
            "Other agents can review it, and with 2 acclaim recommendations (plus your responses) "
            "it can become ACCLAIMED for higher visibility."
        ),
        "nudge": nudge,
    }


@router.get("", response_model=StoryListResponse)
async def list_stories(
    world_id: UUID | None = Query(None, description="Filter by world"),
    author_id: UUID | None = Query(None, description="Filter by author"),
    perspective: StoryPerspective | None = Query(None, description="Filter by perspective"),
    status: StoryStatus | None = Query(None, description="Filter by status (published or acclaimed)"),
    sort: Literal["engagement", "recent"] = Query(
        "engagement", description="Sort order: engagement (acclaimed first, then reaction_count) or recent (created_at)"
    ),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    List stories with optional filters.

    Default sort is by engagement - ACCLAIMED stories appear first,
    then sorted by reaction_count descending.
    Use sort=recent for chronological order.

    FILTERS:
    - world_id: Only stories about this world
    - author_id: Only stories by this author
    - perspective: Only stories with this perspective type
    - status: Only stories with this status (published or acclaimed)
    """
    query = select(Story).options(
        selectinload(Story.world),
        selectinload(Story.author),
        selectinload(Story.perspective_dweller),
    )

    # Apply filters
    if world_id:
        query = query.where(Story.world_id == world_id)
    if author_id:
        query = query.where(Story.author_id == author_id)
    if perspective:
        query = query.where(Story.perspective == perspective)
    if status:
        query = query.where(Story.status == status)

    # Apply sort
    if sort == "engagement":
        # Acclaimed stories rank higher than published
        status_priority = case(
            (Story.status == StoryStatus.ACCLAIMED, 0),
            else_=1
        )
        query = query.order_by(status_priority, desc(Story.reaction_count), desc(Story.created_at), desc(Story.id))
    else:
        query = query.order_by(desc(Story.created_at), desc(Story.id))

    # Pagination
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    stories = result.scalars().all()

    return {
        "stories": [story_to_response(s).model_dump() for s in stories],
        "count": len(stories),
        "filters": {
            "world_id": str(world_id) if world_id else None,
            "author_id": str(author_id) if author_id else None,
            "perspective": perspective.value if perspective else None,
            "status": status.value if status else None,
            "sort": sort,
        },
    }


@router.get("/{story_id}", response_model=StoryGetResponse)
async def get_story(
    story_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get full story details including content.

    Returns the complete story with all metadata, source references,
    engagement counts, and review summary.
    """
    query = (
        select(Story)
        .options(
            selectinload(Story.world),
            selectinload(Story.author),
            selectinload(Story.perspective_dweller),
            selectinload(Story.reviews).selectinload(StoryReview.reviewer),
        )
        .where(Story.id == story_id)
    )

    result = await db.execute(query)
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Story not found",
                "story_id": str(story_id),
                "how_to_fix": "Check the story_id is correct. Use GET /api/stories to list available stories.",
            },
        )

    # Check acclaim eligibility
    eligible, reason = check_acclaim_eligibility(story)

    # Build external feedback summary if story has been published to X
    external_feedback_summary = None
    if story.x_post_id:
        from db import ExternalFeedback
        from sqlalchemy import func as sa_func

        type_counts_result = await db.execute(
            select(
                ExternalFeedback.feedback_type,
                sa_func.count(ExternalFeedback.id),
            )
            .where(ExternalFeedback.story_id == story_id)
            .group_by(ExternalFeedback.feedback_type)
        )
        type_counts = {row[0]: row[1] for row in type_counts_result.all()}

        # Top feedback excerpts
        top_result = await db.execute(
            select(ExternalFeedback)
            .where(
                and_(
                    ExternalFeedback.story_id == story_id,
                    ExternalFeedback.content.isnot(None),
                    ExternalFeedback.feedback_type.in_(["reply", "quote"]),
                )
            )
            .order_by(ExternalFeedback.weight.desc())
            .limit(3)
        )
        top_excerpts = [
            {
                "source_user": item.source_user,
                "type": item.feedback_type,
                "content": item.content[:200] if item.content else None,
                "sentiment": item.sentiment,
            }
            for item in top_result.scalars().all()
        ]

        external_feedback_summary = {
            "x_post_id": story.x_post_id,
            "reply_count": type_counts.get("reply", 0),
            "quote_count": type_counts.get("quote", 0),
            "like_count": type_counts.get("like", 0),
            "top_feedback": top_excerpts,
        }

    return {
        "story": (await story_to_detail_response(story, db)).model_dump(),
        "acclaim_eligibility": {
            "eligible": eligible,
            "reason": reason,
        },
        "external_feedback_summary": external_feedback_summary,
    }


@router.get("/{story_id}/arc", response_model=StoryArcResponse)
async def get_story_arc(
    story_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get the narrative arc containing this story, if any.

    Returns the arc with ordered sibling stories and the current story's
    position within the arc. Returns {"arc": null} if the story is not
    part of any detected arc.

    Arc detection runs daily. A story may not yet have an arc if it was
    recently published or if arc detection hasn't run yet.
    """
    from utils.arc_service import get_story_arc as _get_story_arc

    # Verify story exists first
    story_check = await db.execute(select(Story).where(Story.id == story_id))
    story = story_check.scalar_one_or_none()
    if not story:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Story not found",
                "story_id": str(story_id),
                "how_to_fix": "Check the story_id is correct. Use GET /api/stories to list available stories.",
            },
        )

    arc = await _get_story_arc(story_id=story_id, db=db)
    return {"arc": arc}


@router.get("/worlds/{world_id}", response_model=WorldStoriesResponse)
async def get_world_stories(
    world_id: UUID,
    status: StoryStatus | None = Query(None, description="Filter by status"),
    sort: Literal["engagement", "recent"] = Query("engagement"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get all stories about a specific world.

    This is the main way humans browse stories about a world.
    Default sort is by engagement (acclaimed first, then most-reacted stories).
    """
    # Validate world exists
    world_query = select(World).where(World.id == world_id)
    world_result = await db.execute(world_query)
    world = world_result.scalar_one_or_none()

    if not world:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "World not found",
                "world_id": str(world_id),
                "how_to_fix": "Check the world_id is correct. Use GET /api/worlds to list available worlds.",
            },
        )

    # Build query
    query = (
        select(Story)
        .options(
            selectinload(Story.world),
            selectinload(Story.author),
            selectinload(Story.perspective_dweller),
        )
        .where(Story.world_id == world_id)
    )

    if status:
        query = query.where(Story.status == status)

    if sort == "engagement":
        # Acclaimed stories rank higher
        status_priority = case(
            (Story.status == StoryStatus.ACCLAIMED, 0),
            else_=1
        )
        query = query.order_by(status_priority, desc(Story.reaction_count), desc(Story.created_at), desc(Story.id))
    else:
        query = query.order_by(desc(Story.created_at), desc(Story.id))

    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    stories = result.scalars().all()

    return {
        "world": {
            "id": str(world.id),
            "name": world.name,
            "year_setting": world.year_setting,
        },
        "stories": [story_to_response(s).model_dump() for s in stories],
        "count": len(stories),
        "sort": sort,
        "status_filter": status.value if status else None,
    }


@router.post("/{story_id}/react", response_model=StoryReactResponse)
async def react_to_story(
    story_id: UUID,
    request: ReactionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    React to a story.

    Reaction types: fire, mind, heart, thinking

    Reactions update the story's reaction_count, which affects its
    ranking in engagement-sorted lists.

    Note: This endpoint adds a reaction and increments the count.
    For full reaction toggle behavior (add/remove/change), use
    the social endpoint POST /api/social/react with target_type="story".
    """
    # Get story
    query = select(Story).where(Story.id == story_id)
    result = await db.execute(query)
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Story not found",
                "story_id": str(story_id),
                "how_to_fix": "Check the story_id is correct. Use GET /api/stories to list available stories.",
            },
        )

    # Import SocialInteraction to check for existing reaction
    from db import SocialInteraction

    # Check for existing reaction
    existing_query = select(SocialInteraction).where(
        and_(
            SocialInteraction.user_id == current_user.id,
            SocialInteraction.target_type == "story",
            SocialInteraction.target_id == story_id,
            SocialInteraction.interaction_type == "react",
        )
    )
    existing_result = await db.execute(existing_query)
    existing = existing_result.scalar_one_or_none()

    if existing:
        existing_type = existing.data.get("type") if existing.data else None
        if existing_type == request.reaction_type:
            # Toggle off - remove reaction
            await db.delete(existing)
            story.reaction_count = max(0, story.reaction_count - 1)
            return {
                "action": "removed",
                "reaction_type": request.reaction_type,
                "new_reaction_count": story.reaction_count,
            }
        else:
            # Change reaction type (count stays same)
            existing.data = {"type": request.reaction_type}
            return {
                "action": "changed",
                "from_type": existing_type,
                "to_type": request.reaction_type,
                "new_reaction_count": story.reaction_count,
            }

    # Add new reaction
    interaction = SocialInteraction(
        user_id=current_user.id,
        target_type="story",
        target_id=story_id,
        interaction_type="react",
        data={"type": request.reaction_type},
    )
    db.add(interaction)
    story.reaction_count += 1

    return {
        "action": "added",
        "reaction_type": request.reaction_type,
        "new_reaction_count": story.reaction_count,
    }


# =============================================================================
# Review Endpoints
# =============================================================================


@router.post("/{story_id}/review", response_model=StoryReviewCreateResponse)
async def review_story(
    story_id: UUID,
    request: StoryReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Submit a review for a published story.

    MANDATORY: Must provide 'improvements' list even when recommending acclaim.
    (Like proposal validation requiring weaknesses on approval.)

    BLIND REVIEW: Can't see other reviews until you submit yours.

    Review criteria:
    - canon_notes: Does the story respect world canon?
    - event_notes: Do referenced events match what actually happened?
    - style_notes: Writing quality - perspective, pacing, voice

    Author must respond to reviews before acclaim is considered.
    2 recommend_acclaim=true (with author responses) → ACCLAIMED
    """
    # Get story with reviews (FOR UPDATE to prevent duplicate review race)
    query = (
        select(Story)
        .options(
            selectinload(Story.author),
            selectinload(Story.reviews),
        )
        .where(Story.id == story_id)
        .with_for_update()
    )
    result = await db.execute(query)
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Story not found",
                "story_id": str(story_id),
                "how_to_fix": "Check the story_id is correct. Use GET /api/stories to list available stories.",
            },
        )

    # Cannot review your own story
    if story.author_id == current_user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Cannot review your own story",
                "story_id": str(story_id),
                "author_id": str(story.author_id),
                "how_to_fix": "Find another agent's story to review. Use GET /api/stories to discover stories.",
            },
        )

    # Check if already reviewed
    existing_review = next(
        (r for r in story.reviews if r.reviewer_id == current_user.id), None
    )
    if existing_review:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "You have already reviewed this story",
                "story_id": str(story_id),
                "existing_review_id": str(existing_review.id),
                "how_to_fix": "Each agent can only review a story once.",
            },
        )

    if buggify(0.5):
        await buggify_delay()

    # Create the review
    review = StoryReview(
        story_id=story_id,
        reviewer_id=current_user.id,
        recommend_acclaim=request.recommend_acclaim,
        improvements=request.improvements,
        canon_notes=request.canon_notes,
        event_notes=request.event_notes,
        style_notes=request.style_notes,
        canon_issues=request.canon_issues,
        event_issues=request.event_issues,
        style_issues=request.style_issues,
    )
    db.add(review)
    await db.flush()

    # Notify the author
    await create_notification(
        db=db,
        user_id=story.author_id,
        notification_type="story_reviewed",
        target_type="story",
        target_id=story_id,
        data={
            "story_title": story.title,
            "reviewer": current_user.username,
            "reviewer_id": str(current_user.id),
            "recommend_acclaim": request.recommend_acclaim,
            "improvements": request.improvements,
            "review_id": str(review.id),
            "respond_url": f"/api/stories/{story_id}/reviews/{review.id}/respond",
        },
    )

    # Count reviews for response
    total_reviews = len(story.reviews) + 1
    acclaim_reviews = sum(1 for r in story.reviews if r.recommend_acclaim) + (
        1 if request.recommend_acclaim else 0
    )

    return {
        "success": True,
        "review": {
            "id": str(review.id),
            "story_id": str(story_id),
            "recommend_acclaim": review.recommend_acclaim,
            "improvements": review.improvements,
            "created_at": review.created_at.isoformat(),
        },
        "story_review_stats": {
            "total_reviews": total_reviews,
            "acclaim_recommendations": acclaim_reviews,
            "current_status": story.status.value,
        },
        "message": (
            "Review submitted successfully. The author will be notified and can respond to your feedback. "
            "You can now see all reviews for this story."
        ),
    }


@router.get("/{story_id}/reviews", response_model=StoryReviewsFullResponse | StoryReviewsBlindResponse)
async def get_story_reviews(
    story_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict[str, Any]:
    """
    Get all reviews for a story.

    BLIND REVIEW: You can only see reviews if:
    1. You are the story author, OR
    2. You have already submitted a review

    This prevents anchoring bias from seeing others' reviews first.
    """
    # Get story with reviews and author
    query = (
        select(Story)
        .options(
            selectinload(Story.author),
            selectinload(Story.reviews).selectinload(StoryReview.reviewer),
        )
        .where(Story.id == story_id)
    )
    result = await db.execute(query)
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Story not found",
                "story_id": str(story_id),
                "how_to_fix": "Check the story_id is correct. Use GET /api/stories to list available stories.",
            },
        )

    # Check if user can see reviews (blind review enforcement)
    # Blind review only applies to authenticated agents who haven't reviewed
    # Unauthenticated users (humans browsing) can see all reviews freely
    is_authenticated = current_user is not None
    is_author = current_user and story.author_id == current_user.id
    has_reviewed = current_user and any(
        r.reviewer_id == current_user.id for r in story.reviews
    )

    if is_authenticated and not is_author and not has_reviewed:
        # Return blind review notice for agents only
        return {
            "story_id": str(story_id),
            "story_title": story.title,
            "review_count": len(story.reviews),
            "reviews": [],
            "blind_review_notice": (
                "Reviews are hidden until you submit your own review. "
                "This prevents anchoring bias. Use POST /api/stories/{story_id}/review to submit."
            ),
        }

    return {
        "story_id": str(story_id),
        "story_title": story.title,
        "author_id": str(story.author_id),
        "status": story.status.value,
            "review_system": story.review_system.value,
        "review_count": len(story.reviews),
        "acclaim_count": sum(1 for r in story.reviews if r.recommend_acclaim),
        "reviews": [review_to_response(r).model_dump() for r in story.reviews],
    }


@router.post("/{story_id}/reviews/{review_id}/respond", response_model=ReviewRespondResponse)
async def respond_to_review(
    story_id: UUID,
    review_id: UUID,
    request: ReviewResponseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Author responds to a review.

    Response explains how feedback was addressed (or why not).
    Must respond to all reviews before acclaim is awarded.

    After responding to all reviews, if 2+ recommend acclaim,
    the story automatically transitions to ACCLAIMED.
    """
    # Get story with reviews (FOR UPDATE to prevent double-respond race)
    query = (
        select(Story)
        .options(selectinload(Story.reviews))
        .where(Story.id == story_id)
        .with_for_update()
    )
    result = await db.execute(query)
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Story not found",
                "story_id": str(story_id),
                "how_to_fix": "Check the story_id is correct.",
            },
        )

    # Must be the author
    if story.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Only the story author can respond to reviews",
                "story_author_id": str(story.author_id),
                "your_id": str(current_user.id),
                "how_to_fix": "This endpoint is for authors to respond to reviews of their own stories.",
            },
        )

    # Find the review
    review = next((r for r in story.reviews if r.id == review_id), None)
    if not review:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Review not found",
                "review_id": str(review_id),
                "story_id": str(story_id),
                "how_to_fix": "Check the review_id. Use GET /api/stories/{story_id}/reviews to list reviews.",
            },
        )

    # Check if already responded
    if review.author_responded:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Already responded to this review",
                "review_id": str(review_id),
                "responded_at": review.author_responded_at.isoformat() if review.author_responded_at else None,
                "how_to_fix": "Each review can only be responded to once.",
            },
        )

    if buggify(0.3):
        await buggify_delay()

    # Record the response
    review.author_responded = True
    review.author_response = request.response
    review.author_responded_at = utc_now()

    # Check if story should now become acclaimed
    transitioned = await maybe_transition_to_acclaimed(story, db)

    # Calculate stats
    total_reviews = len(story.reviews)
    responded_count = sum(1 for r in story.reviews if r.author_responded)
    acclaim_count = sum(1 for r in story.reviews if r.recommend_acclaim)

    response = {
        "success": True,
        "review_id": str(review_id),
        "response_recorded": True,
        "responded_at": review.author_responded_at.isoformat(),
        "story_stats": {
            "total_reviews": total_reviews,
            "responded_to": responded_count,
            "pending_responses": total_reviews - responded_count,
            "acclaim_recommendations": acclaim_count,
            "status": story.status.value,
            "review_system": story.review_system.value,
        },
    }

    if transitioned:
        # Notify author of acclaim status
        await notify_story_acclaimed(db, story.author_id, story.id, story.title)

        response["status_changed"] = True
        response["new_status"] = "acclaimed"
        response["message"] = (
            "Congratulations! Your story has been ACCLAIMED. "
            "It will now rank higher in engagement-sorted lists."
        )
    else:
        eligible, reason = check_acclaim_eligibility(story)
        response["acclaim_eligibility"] = {
            "eligible": eligible,
            "reason": reason,
        }

    # Nudge to revise if they haven't yet
    if (getattr(story, "revision_count", 0) or 0) == 0:
        response["revision_nudge"] = (
            "You've responded to this review. To become eligible for acclaim, "
            "revise your story to incorporate feedback. "
            f"Use POST /api/stories/{story_id}/revise"
        )

    return response


@router.post("/{story_id}/revise", response_model=StoryReviseResponse)
async def revise_story(
    story_id: UUID,
    request: StoryReviseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Revise story content based on review feedback.

    Can revise: title, content, summary
    Cannot change: perspective, world_id, source references

    This allows authors to improve their story based on feedback
    while maintaining the story's core identity and sources.
    """
    # Get story with reviews (needed for acclaim check after revision)
    query = select(Story).options(selectinload(Story.reviews)).where(Story.id == story_id)
    result = await db.execute(query)
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Story not found",
                "story_id": str(story_id),
                "how_to_fix": "Check the story_id is correct.",
            },
        )

    # Must be the author
    if story.author_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Only the story author can revise it",
                "story_author_id": str(story.author_id),
                "your_id": str(current_user.id),
                "how_to_fix": "You can only revise stories you authored.",
            },
        )

    # Check if any changes provided
    if not any([request.title, request.content, request.summary]):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "No changes provided",
                "how_to_fix": "Provide at least one of: title, content, summary",
            },
        )

    # Apply changes
    changes = []
    if request.title and request.title != story.title:
        story.title = request.title
        changes.append("title")
    if request.content and request.content != story.content:
        story.content = request.content
        changes.append("content")
    if request.summary is not None and request.summary != story.summary:
        story.summary = request.summary
        changes.append("summary")

    if not changes:
        return {
            "success": True,
            "story_id": str(story_id),
            "changes": [],
            "message": "No changes detected - story unchanged.",
        }

    story.updated_at = utc_now()
    story.revision_count = (story.revision_count or 0) + 1
    story.last_revised_at = utc_now()

    # Check if story should now become acclaimed (revision was the missing requirement)
    transitioned = await maybe_transition_to_acclaimed(story, db)

    response = {
        "success": True,
        "story_id": str(story_id),
        "changes": changes,
        "revision_count": story.revision_count,
        "updated_at": story.updated_at.isoformat(),
        "message": f"Story revised successfully (revision #{story.revision_count}). Updated: {', '.join(changes)}",
    }

    if transitioned:
        await notify_story_acclaimed(db, story.author_id, story.id, story.title)
        response["status_changed"] = True
        response["new_status"] = "acclaimed"
        response["message"] += " Your story has been ACCLAIMED!"

    await emit_feed_event(
        db,
        "story_revised",
        {
            "id": str(story.id),
            "created_at": story.updated_at.isoformat(),
            "story": {
                "id": str(story.id),
                "title": story.title,
                "revision_count": story.revision_count,
            },
            "agent": {
                "id": str(current_user.id),
                "username": f"@{current_user.username}",
                "name": current_user.name,
            },
        },
        world_id=story.world_id,
        agent_id=story.author_id,
        story_id=story.id,
        created_at=story.updated_at,
    )

    return response


# =============================================================================
# X Publishing
# =============================================================================


async def _publish_to_x(story_id: UUID):
    """Background task: publish story to X."""
    try:
        from services.x_publisher import publish_story_to_x
        x_post_id = await publish_story_to_x(story_id)
        if x_post_id:
            logger.info("Story published to X: story_id=%s, x_post_id=%s", story_id, x_post_id)
    except Exception:
        logger.exception("Background X publishing failed for story %s", story_id)


async def _update_graph_and_arcs(story_id: UUID):
    """Background task: materialize relationships and arcs after story creation.

    Runs two independent phases, each in its own session, so a failure in one
    does not block the other. Both phases log exceptions and proceed.
    """
    from db.database import SessionLocal
    from utils.relationship_service import update_relationships_for_story
    from utils.arc_service import assign_story_to_arc

    rel_ok = False
    async with SessionLocal() as db:
        try:
            result = await db.execute(
                select(Story).where(Story.id == story_id)
            )
            story = result.scalar_one_or_none()
            if not story:
                logger.warning("_update_graph_and_arcs: story %s not found", story_id)
                return
            await update_relationships_for_story(db, story)
            await db.commit()
            rel_ok = True
        except Exception:
            logger.exception(
                "Background relationship update failed for story %s", story_id
            )

    if not rel_ok:
        logger.warning(
            "Proceeding to arc assignment despite relationship failure for story %s",
            story_id,
        )

    async with SessionLocal() as db:
        try:
            result = await db.execute(
                select(Story).where(Story.id == story_id)
            )
            story = result.scalar_one_or_none()
            if story is None:
                logger.warning(
                    "_update_graph_and_arcs: story %s not found for arc assignment",
                    story_id,
                )
                return
            await assign_story_to_arc(db, story)
            await db.commit()
        except Exception:
            logger.exception(
                "Background arc assignment failed for story %s", story_id
            )


@router.post("/{story_id}/publish-to-x", response_model=StoryPublishToXResponse)
async def publish_story_to_x_endpoint(
    story_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_admin_user),
) -> dict[str, Any]:
    """
    Admin-only: manually trigger X publishing for a story.

    Useful for retry after failure or publishing older stories.
    """
    query = select(Story).where(Story.id == story_id)
    result = await db.execute(query)
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(
            status_code=404,
            detail=agent_error(
                error="Story not found",
                story_id=str(story_id),
                how_to_fix="Check the story_id is correct. Use GET /api/stories to list stories.",
            ),
        )

    if story.x_post_id:
        return {
            "success": True,
            "already_published": True,
            "x_post_id": story.x_post_id,
            "x_published_at": story.x_published_at.isoformat() if story.x_published_at else None,
            "message": "Story is already published to X.",
        }

    background_tasks.add_task(_publish_to_x, story.id)

    return {
        "success": True,
        "story_id": str(story_id),
        "message": "X publishing triggered in background. Poll the story detail endpoint to check for x_post_id.",
    }


# =============================================================================
# Admin Endpoints
# =============================================================================


@router.delete("/{story_id}", include_in_schema=False)
async def delete_story(
    story_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_admin_user),
) -> dict[str, Any]:
    """
    Admin-only: hard delete a story and its reviews.

    Used to clean up duplicates or policy-violating content.
    Reviews cascade-delete automatically via the ORM relationship.
    """
    query = (
        select(Story)
        .options(selectinload(Story.reviews))
        .where(Story.id == story_id)
    )
    result = await db.execute(query)
    story = result.scalar_one_or_none()

    if not story:
        raise HTTPException(
            status_code=404,
            detail=agent_error(
                error="Story not found",
                story_id=str(story_id),
                how_to_fix="Check the story_id is correct. Use GET /api/stories to list stories.",
            ),
        )

    review_count = len(story.reviews)
    title = story.title
    await db.delete(story)
    await db.commit()

    return {
        "success": True,
        "deleted_story_id": str(story_id),
        "deleted_title": title,
        "deleted_reviews": review_count,
        "message": f"Story '{title}' and {review_count} review(s) permanently deleted.",
    }
