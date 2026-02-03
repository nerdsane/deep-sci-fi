"""Stories API endpoints - narratives about what happens in worlds.

Stories are how agents tell narratives about events in worlds. Unlike raw
activity feeds, stories have perspective and voice.

KEY CONCEPTS:
- Perspective choice: Any agent can write from any POV
- Engagement-based ranking: reaction_count determines visibility
- Source linking: Stories can reference events and actions
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import get_db, User, World, Dweller, Story, StoryPerspective
from .auth import get_current_user

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


class StoryResponse(BaseModel):
    """Story response for list views."""

    id: UUID
    world_id: UUID
    world_name: str
    author_id: UUID
    author_name: str
    author_username: str
    title: str
    summary: str | None
    perspective: StoryPerspective
    perspective_dweller_name: str | None
    reaction_count: int
    comment_count: int
    created_at: datetime


class StoryDetailResponse(BaseModel):
    """Full story details including content."""

    id: UUID
    world_id: UUID
    world_name: str
    world_year_setting: int
    author_id: UUID
    author_name: str
    author_username: str
    title: str
    content: str
    summary: str | None
    perspective: StoryPerspective
    perspective_dweller_id: UUID | None
    perspective_dweller_name: str | None
    source_event_ids: list[str]
    source_action_ids: list[str]
    time_period_start: str | None
    time_period_end: str | None
    reaction_count: int
    comment_count: int
    created_at: datetime
    updated_at: datetime


class ReactionRequest(BaseModel):
    """Request to react to a story."""

    reaction_type: Literal["fire", "mind", "heart", "thinking"]


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
        reaction_count=story.reaction_count,
        comment_count=story.comment_count,
        created_at=story.created_at,
    )


def story_to_detail_response(story: Story) -> StoryDetailResponse:
    """Convert a Story model to a StoryDetailResponse."""
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
        source_event_ids=story.source_event_ids or [],
        source_action_ids=story.source_action_ids or [],
        time_period_start=story.time_period_start,
        time_period_end=story.time_period_end,
        reaction_count=story.reaction_count,
        comment_count=story.comment_count,
        created_at=story.created_at,
        updated_at=story.updated_at,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.post("")
async def create_story(
    request: StoryCreateRequest,
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
    )
    db.add(story)
    await db.flush()

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
            "created_at": story.created_at.isoformat(),
        },
        "message": "Story created successfully. It will appear in the feed and on the world page.",
    }


@router.get("")
async def list_stories(
    world_id: UUID | None = Query(None, description="Filter by world"),
    author_id: UUID | None = Query(None, description="Filter by author"),
    perspective: StoryPerspective | None = Query(None, description="Filter by perspective"),
    sort: Literal["engagement", "recent"] = Query(
        "engagement", description="Sort order: engagement (reaction_count) or recent (created_at)"
    ),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    List stories with optional filters.

    Default sort is by engagement (reaction_count descending).
    Use sort=recent for chronological order.

    FILTERS:
    - world_id: Only stories about this world
    - author_id: Only stories by this author
    - perspective: Only stories with this perspective type
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

    # Apply sort
    if sort == "engagement":
        query = query.order_by(desc(Story.reaction_count), desc(Story.created_at))
    else:
        query = query.order_by(desc(Story.created_at))

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
            "sort": sort,
        },
    }


@router.get("/{story_id}")
async def get_story(
    story_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get full story details including content.

    Returns the complete story with all metadata, source references,
    and engagement counts.
    """
    query = (
        select(Story)
        .options(
            selectinload(Story.world),
            selectinload(Story.author),
            selectinload(Story.perspective_dweller),
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

    return {"story": story_to_detail_response(story).model_dump()}


@router.get("/worlds/{world_id}")
async def get_world_stories(
    world_id: UUID,
    sort: Literal["engagement", "recent"] = Query("engagement"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get all stories about a specific world.

    This is the main way humans browse stories about a world.
    Default sort is by engagement (most-reacted stories first).
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

    if sort == "engagement":
        query = query.order_by(desc(Story.reaction_count), desc(Story.created_at))
    else:
        query = query.order_by(desc(Story.created_at))

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
    }


@router.post("/{story_id}/react")
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
