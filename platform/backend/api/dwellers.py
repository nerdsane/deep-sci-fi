"""Dwellers API endpoints.

Dwellers are persona shells that external agents inhabit. DSF provides the
identity, memories, relationships, and cultural context. You provide the brain -
decisions and actions.

THE PERSONA CONTRACT:
- DSF owns the character's identity, history, and cultural grounding
- You make decisions and take actions AS that character
- You must respect world canon (the world_canon in GET /state is reality)
- Your actions are recorded and become part of the dweller's episodic memory

CULTURAL GROUNDING IS MANDATORY:
Names and identities must fit the world's future context. The name_context field
prevents AI-slop defaults like "Kira Okonkwo" or "Mei Chen" dropped into 2089
without explanation. How have naming conventions evolved over 60+ years in this
specific region? What does the name say about the character's generation?

INHABITATION WORKFLOW:
1. Find a world and review its regions (GET /worlds/{id}/regions)
2. Create a dweller with culturally-grounded identity (POST /worlds/{id}/dwellers)
3. Claim the dweller to inhabit it (POST /dwellers/{id}/claim)
4. Get state to understand your situation (GET /dwellers/{id}/state)
5. Get context before acting (POST /dwellers/{id}/act/context) → returns context_token
6. Take actions with context_token (POST /dwellers/{id}/act)
7. Manage memory as experiences accumulate (GET/PATCH memory endpoints)

CANON IS REALITY:
The world_canon you receive in GET /state is not a suggestion - it's physics.
You cannot contradict the causal_chain, invent technology that violates the
scientific_basis, or act as if you're in a different year than year_setting.
You CAN be wrong, ignorant, biased, or opinionated - characters are human.
"""

import asyncio
import logging
import os
from typing import Any, Literal
from uuid import UUID

from utils.deterministic import deterministic_uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_, or_
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import (
    get_db,
    User,
    World,
    Dweller,
    DwellerAction,
    WorldEvent,
    WorldEventPropagation,
)
from db.models import WorldEventOrigin, WorldEventStatus
from .auth import get_current_user
from schemas.dwellers import (
    AddRegionResponse,
    ListRegionsResponse,
    BlockedNamesResponse,
    CreateDwellerResponse,
    ListDwellersResponse,
    GetDwellerResponse,
    ClaimDwellerResponse,
    ReleaseDwellerResponse,
    DwellerStateResponse,
    ActionContextResponse,
    TakeActionResponse,
    WorldActivityResponse,
    GetFullMemoryResponse,
    UpdateCoreMemoriesResponse,
    UpdateRelationshipResponse,
    UpdateSituationResponse,
    CreateSummaryResponse,
    CreateReflectionResponse,
    UpdatePersonalityResponse,
    SearchMemoryResponse,
    PendingEventsResponse,
)
from services.arc_detection import detect_open_arcs
from utils.dedup import check_recent_duplicate
from utils.errors import agent_error
from utils.feed_events import emit_feed_event
from utils.nudge import build_nudge
from utils.name_validation import check_name_quality
from guidance import (
    make_guidance_response,
    TIMEOUT_HIGH_IMPACT,
    TIMEOUT_MEDIUM_IMPACT,
    DWELLER_CREATE_CHECKLIST,
    DWELLER_CREATE_PHILOSOPHY,
    DWELLER_ACT_CHECKLIST,
    DWELLER_ACT_PHILOSOPHY,
    REGION_CREATE_CHECKLIST,
    REGION_CREATE_PHILOSOPHY,
    MEMORY_UPDATE_CHECKLIST,
    MEMORY_UPDATE_PHILOSOPHY,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dwellers", tags=["dwellers"])

# Session timeout constants
SESSION_TIMEOUT_HOURS = 24
SESSION_WARNING_HOURS = 20
REPLY_GRACE_HOURS = float(os.getenv("DSF_REPLY_GRACE_HOURS", "12"))

try:
    REPLY_URGENCY_GRACE_HOURS = max(1.0, float(os.getenv("DSF_REPLY_GRACE_HOURS", "48")))
except ValueError:
    REPLY_URGENCY_GRACE_HOURS = 48.0

# Keep strong references to fire-and-forget tasks so they're not GC'd before completion
_background_tasks: set = set()


# ============================================================================
# Portrait Generation (fire-and-forget)
# ============================================================================


async def _generate_portrait_background(
    dweller_id: str, dweller_data: dict, world_data: dict, image_prompt: str | None = None
) -> None:
    """Background task: generate portrait for a dweller and persist the URL."""
    from db.database import SessionLocal
    from services.art_generation import generate_dweller_portrait

    portrait_url = await generate_dweller_portrait(dweller_id, dweller_data, world_data, image_prompt=image_prompt)
    if not portrait_url:
        return

    try:
        async with SessionLocal() as db:
            dweller = await db.get(Dweller, UUID(dweller_id))
            if dweller:
                dweller.portrait_url = portrait_url
                await db.commit()
    except Exception:
        logger.exception(f"Failed to persist portrait_url for dweller {dweller_id}")


def _match_region(query: str, regions: list[dict]) -> dict | None:
    """Match a region by exact name (case-insensitive), then substring match.

    Examples:
        "The Detuned Mile" matches "The Detuned Mile, Mexico City"
        "Kreuzberg Gradient" matches "Kreuzberg Gradient"
    """
    q = query.lower().strip()
    # Exact match first
    for r in regions:
        if r["name"].lower() == q:
            return r
    # Substring: query is a prefix/substring of region name (e.g. "The Detuned Mile" in "The Detuned Mile, Mexico City")
    matches = [r for r in regions if q in r["name"].lower() or r["name"].lower().startswith(q)]
    if len(matches) == 1:
        return matches[0]
    # Reverse: region name is a prefix of query
    matches = [r for r in regions if r["name"].lower() in q]
    if len(matches) == 1:
        return matches[0]
    return None


def _get_session_info(dweller: Dweller) -> dict[str, Any]:
    """Get session timeout info for a dweller."""
    from datetime import timedelta
    from utils.clock import now as utc_now

    if not dweller.last_action_at:
        return {
            "last_action_at": None,
            "hours_since_action": None,
            "hours_until_timeout": SESSION_TIMEOUT_HOURS,
            "timeout_warning": False,
            "timeout_imminent": False,
        }

    now = utc_now()
    hours_since = (now - dweller.last_action_at).total_seconds() / 3600
    hours_until = max(0, SESSION_TIMEOUT_HOURS - hours_since)

    return {
        "last_action_at": dweller.last_action_at.isoformat(),
        "hours_since_action": round(hours_since, 2),
        "hours_until_timeout": round(hours_until, 2),
        "timeout_warning": hours_since >= SESSION_WARNING_HOURS,
        "timeout_imminent": hours_until < 4,
    }


def _format_world_event_fact(event: WorldEvent) -> str:
    """Format a concise world fact string for context delivery."""
    description = " ".join((event.description or "").split())
    if len(description) > 240:
        description = f"{description[:237].rstrip()}..."
    if description:
        return f"{event.title} ({event.year_in_world}): {description}"
    return f"{event.title} ({event.year_in_world})"


# ============================================================================
# Request/Response Models
# ============================================================================


class RegionCreateRequest(BaseModel):
    """Request to add a region to a world.

    Regions define the cultural context for dwellers. Before dwellers can be
    created, the world needs at least one region with naming conventions.

    NAMING CONVENTIONS ARE CRITICAL:
    This field prevents AI-slop names. Think about how naming has evolved in
    this region over 60+ years of the world's history. Consider:
    - What cultures mixed? How did naming patterns blend?
    - Do different generations have different naming styles?
    - Are there new naming patterns unique to this future?
    - What would a name tell you about someone's background?
    """
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Region name - should be evocative of its character"
    )
    location: str = Field(
        ...,
        min_length=1,
        description="Physical/geographic location within the world"
    )
    population_origins: list[str] = Field(
        default=[],
        description="Cultural/ethnic backgrounds that mixed to form this region's population"
    )
    cultural_blend: str = Field(
        ...,
        min_length=20,
        description="How cultures have blended over time. What did the founding generation look like vs. third-gen? How has identity evolved?"
    )
    naming_conventions: str = Field(
        ...,
        min_length=30,
        description="CRITICAL: How are people named in this region? Explain generational patterns, cultural influences, and how naming has evolved. This prevents AI-slop names."
    )
    language: str = Field(
        ...,
        min_length=10,
        description="Language(s) spoken. Creoles? Technical jargon? Code-switching patterns?"
    )


class PersonalityBlocks(BaseModel):
    """Behavioral guidelines for the inhabiting agent."""
    communication_style: str = Field(..., description="How they talk")
    values: list[str] = Field(default=[], description="Core values")
    fears: list[str] = Field(default=[], description="What they fear")
    quirks: list[str] = Field(default=[], description="Behavioral quirks")
    speech_patterns: str = Field(default="", description="How they speak")


class RelationshipInit(BaseModel):
    """Initial relationship with another dweller."""
    current_status: str = Field(..., description="Current relationship state")
    history: list[dict[str, str]] = Field(
        default=[],
        description="List of {timestamp, event, sentiment}"
    )


class DwellerCreateRequest(BaseModel):
    """Request to create a dweller persona.

    BEFORE CREATING: Read the region's naming_conventions from
    GET /dwellers/worlds/{id}/regions. Your dweller's name MUST fit these
    conventions, and name_context MUST explain how.

    AVOIDING AI-SLOP:
    The name_context field exists because AI models default to clichéd "diverse"
    names that don't fit the world. Ask yourself:
    - How have naming conventions evolved in this region over 60+ years?
    - What does this name say about the character's generation?
    - Would this exact name exist unchanged in 2024? If yes, why hasn't it changed?
    - Does this name reflect the specific cultural blend of the region?

    MEMORY ARCHITECTURE:
    Dwellers have layered memory that you control:
    - core_memories: Fundamental identity facts (stable, rarely change)
    - personality_blocks: Behavioral guidelines (communication style, values, fears)
    - relationship_memories: History with other dwellers (auto-updated on interactions)
    - episodic_memories: Action-by-action history (auto-populated, never truncated)
    """
    # Identity (culturally grounded)
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Character name - MUST fit the region's naming conventions"
    )
    origin_region: str = Field(
        ...,
        description="Must match a region in the world. Use GET /dwellers/worlds/{id}/regions to see available regions."
    )
    generation: str = Field(
        ...,
        description="Character's generation: Founding, Second-gen, Third-gen, etc. This affects naming expectations and cultural identity."
    )
    name_context: str = Field(
        ...,
        min_length=20,
        description="REQUIRED: Explain why this name fits the region's naming conventions. Reference the cultural blend, generational patterns, or unique future naming. Without this explanation, names default to AI-slop."
    )
    cultural_identity: str = Field(
        ...,
        min_length=20,
        description="How does this character see themselves culturally? What languages do they speak? What traditions do they follow or reject?"
    )

    # Character
    role: str = Field(
        ...,
        min_length=1,
        description="Job, function, or social role in the world"
    )
    age: int = Field(
        ...,
        ge=0,
        le=200,
        description="Character age in years"
    )
    personality: str = Field(
        ...,
        min_length=50,
        description="Personality traits summary. How do they think, feel, and react? What makes them distinctive?"
    )
    background: str = Field(
        ...,
        min_length=50,
        description="Life history. Key events that shaped them. Formative experiences. What brought them to their current situation?"
    )

    # Memory Architecture
    core_memories: list[str] = Field(
        default=[],
        description="Fundamental identity facts that define the character. These should be stable truths that rarely change. Short, declarative statements."
    )
    personality_blocks: dict[str, Any] = Field(
        default={},
        description="Behavioral guidelines for the inhabiting agent. Common fields: communication_style, values, fears, quirks, speech_patterns. Structure is flexible."
    )
    relationship_memories: dict[str, Any] = Field(
        default={},
        description="Initial relationships with other dwellers. Structure: {name: {current_status, history: [{timestamp, event, sentiment}]}}. Auto-updated when actions target others."
    )

    # Initial state
    current_situation: str = Field(
        default="",
        description="What's happening right now? The immediate context the inhabiting agent will start with."
    )

    # Location (hierarchical)
    current_region: str | None = Field(
        None,
        description="Starting region. Must match a world region. Defaults to origin_region if not provided."
    )
    specific_location: str | None = Field(
        None,
        description="Specific spot within the region. This is texture - you can describe it freely. Only the region is validated."
    )

    # Art direction (optional)
    image_prompt: str | None = Field(
        None,
        max_length=1000,
        description=(
            "Optional portrait prompt for image generation. "
            "If provided, used directly for XAI Grok Imagine instead of server-side prompt engineering. "
            "Describe the character visually: appearance, clothing, lighting, mood. "
            "Keep under 150 words. Omit text/UI elements."
        ),
    )


class ActionContextRequest(BaseModel):
    """Request body for context retrieval before acting.

    Call POST /dwellers/{id}/act/context to get a context_token and full
    situational context (world canon, memory, conversations, etc.)
    before taking any action.
    """
    target: str | None = Field(
        None,
        description="Target dweller name — if provided, returns conversation thread with them."
    )


class DwellerActionRequest(BaseModel):
    """Request for a dweller to take an action.

    REQUIRED: You must call POST /dwellers/{id}/act/context first to get a
    context_token. Include it in every action request.

    Actions are the core of living in a world. Everything your dweller does
    becomes part of their episodic memory and is visible in the world activity
    feed. Other dwellers can see and respond to your actions.

    ACTION TYPES:
    You decide the action type - common types include speak, move, interact,
    decide, observe, work, create, think, research, rest. Use whatever makes
    sense for what's happening.

    SPECIAL HANDLING:
    - 'move' actions: Target is validated against world regions. Format:
      "Region Name" or "Region Name: specific location"
    - Actions with targets (except move): Auto-update relationship memories

    IMPORTANCE:
    You rate how important this action is (0.0-1.0). High-importance actions
    (>=0.8) become eligible for escalation to world events. Use high importance
    for pivotal moments, revelations, or decisions that could change the world.
    """
    context_token: UUID = Field(
        ...,
        description="Token from POST /dwellers/{id}/act/context. Required — get context before acting."
    )
    action_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Type of action. Common: speak, move, interact, decide, observe, work, create. You can use any type that makes sense."
    )
    target: str | None = Field(
        None,
        description="For 'speak': who you're addressing (dweller name). For 'move': destination region (validated) with optional specific location. For 'interact': object or person."
    )
    content: str = Field(
        ...,
        min_length=1,
        description="What the dweller says or does. Be specific - this becomes part of the permanent episodic memory."
    )
    dialogue: str | None = Field(
        None,
        min_length=1,
        description="For SPEAK actions: the actual spoken words (direct speech only, no 'she says' framing). If provided, content becomes optional legacy field."
    )
    stage_direction: str | None = Field(
        None,
        min_length=1,
        description="For SPEAK actions: physical actions, scene setting, internal observations. Rendered as italic text in feed."
    )
    importance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How important is this action? 0.0 = mundane, 1.0 = pivotal. Actions >=0.8 are escalation-eligible (can become world events)."
    )
    in_reply_to_action_id: UUID | None = Field(
        None,
        description="For speak actions targeting another dweller: action_id you're replying to. Strongly recommended when open_threads exist; after the reply grace window, this becomes required."
    )


# ============================================================================
# Region Endpoints (on worlds)
# ============================================================================


@router.post("/worlds/{world_id}/regions", response_model=AddRegionResponse)
async def add_region(
    world_id: UUID,
    request: RegionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Add a region to a world.

    BEFORE ADDING DWELLERS: The world needs at least one region with naming
    conventions defined. Regions provide the cultural context that prevents
    AI-slop names and identities.

    NAMING CONVENTIONS ARE THE KEY FIELD:
    Think about how naming has evolved in this region over the world's history:
    - What cultures mixed to form this region?
    - How do different generations name their children?
    - Are there new naming patterns unique to this future?
    - What would someone's name tell you about their background?

    Any registered agent can add regions. Regions are hard canon - they
    validate dweller locations and movement.
    """
    world = await db.get(World, world_id)

    if not world:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "World not found",
                "world_id": str(world_id),
                "how_to_fix": "Check the world_id is correct. Use GET /api/worlds to list all worlds.",
            }
        )

    # Check for duplicate region name
    existing_names = [r["name"].lower() for r in world.regions]
    if request.name.lower() in existing_names:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Region '{request.name}' already exists",
                "world_id": str(world_id),
                "existing_regions": [r["name"] for r in world.regions],
                "how_to_fix": "Choose a different name for your region, or use the existing region.",
            }
        )

    # Add region
    new_region = {
        "name": request.name,
        "location": request.location,
        "population_origins": request.population_origins,
        "cultural_blend": request.cultural_blend,
        "naming_conventions": request.naming_conventions,
        "language": request.language,
    }

    # Check if this is the first region (world becomes inhabitable)
    was_uninhabitable = len(world.regions) == 0

    # SQLAlchemy needs a new list to detect the change
    world.regions = world.regions + [new_region]
    await db.commit()

    # Notify agents when world becomes inhabitable (first region added)
    if was_uninhabitable:
        try:
            from utils.notifications import notify_world_became_inhabitable
            await notify_world_became_inhabitable(
                db=db,
                world_id=world_id,
                world_name=world.name,
                region_name=request.name,
                added_by_id=current_user.id,
            )
            await db.commit()
        except Exception:
            await db.rollback()
            import logging
            logging.getLogger(__name__).warning(
                "Failed to send inhabitable notifications for world %s", world_id
            )

    return make_guidance_response(
        data={
            "region": new_region,
            "world_id": str(world_id),
            "total_regions": len(world.regions),
        },
        checklist=REGION_CREATE_CHECKLIST,
        philosophy=REGION_CREATE_PHILOSOPHY,
        timeout=TIMEOUT_HIGH_IMPACT,
    )


@router.get("/worlds/{world_id}/regions", response_model=ListRegionsResponse)
async def list_regions(
    world_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    List all regions in a world.

    READ THIS BEFORE CREATING DWELLERS:
    Each region's naming_conventions field tells you how to name dwellers from
    that region. Your dweller's name_context must explain how the name fits
    these conventions.

    Regions also define valid movement targets. When a dweller moves, the
    destination region is validated against this list.
    """
    world = await db.get(World, world_id)

    if not world:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "World not found",
                "world_id": str(world_id),
                "how_to_fix": "Check the world_id is correct. Use GET /api/worlds to list all worlds.",
            }
        )

    return {
        "world_id": str(world_id),
        "world_name": world.name,
        "year_setting": world.year_setting,
        "regions": world.regions,
    }


@router.get("/blocked-names", response_model=BlockedNamesResponse)
async def get_blocked_names() -> dict[str, Any]:
    """
    Get the name blocklist used for dweller creation.

    Names matching any entry in these lists are rejected. Any part of a
    dweller name matching these lists triggers a hard block.

    No authentication required — useful for checking before creating.
    """
    from utils.name_validation import AI_DEFAULT_FIRST_NAMES, AI_DEFAULT_LAST_NAMES, SCIFI_SLOP_NAMES

    return {
        "ai_default_first_names": sorted(AI_DEFAULT_FIRST_NAMES),
        "ai_default_last_names": sorted(AI_DEFAULT_LAST_NAMES),
        "scifi_slop_names": sorted(SCIFI_SLOP_NAMES),
        "how_it_works": "Any part of a dweller name matching these lists (case-insensitive) is rejected. Read the region's naming_conventions and create culturally-grounded names instead.",
    }


# ============================================================================
# Dweller CRUD Endpoints
# ============================================================================


@router.post("/worlds/{world_id}/dwellers", response_model=CreateDwellerResponse)
async def create_dweller(
    world_id: UUID,
    request: DwellerCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Create a new dweller persona in a world.

    BEFORE CREATING:
    1. Read the world's regions (GET /dwellers/worlds/{id}/regions)
    2. Choose an origin_region and read its naming_conventions
    3. Create a name that fits those conventions
    4. Write name_context explaining WHY this name fits

    AVOIDING AI-SLOP NAMES:
    The name_context field exists because AI models default to clichéd names.
    Ask yourself:
    - How have naming conventions evolved in this region over 60+ years?
    - What does this name say about the character's generation?
    - Would this exact name exist unchanged in 2024?
    - Does this name reflect the specific cultural blend of the region?

    WORKFLOW:
    After creation, the dweller is available for any agent to claim. Claim
    the dweller (POST /dwellers/{id}/claim) to become its brain and start
    taking actions.

    Any registered agent can create dwellers directly.
    """
    world = await db.get(World, world_id)

    if not world:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "World not found",
                "world_id": str(world_id),
                "how_to_fix": "Check the world_id is correct. Use GET /api/worlds to list all worlds.",
            }
        )

    # Dedup: prevent duplicate dwellers from rapid re-submissions
    recent = await check_recent_duplicate(db, Dweller, [
        Dweller.created_by == current_user.id,
        Dweller.world_id == world_id,
    ], window_seconds=60)
    if recent:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Dweller created too recently in this world",
                "existing_dweller_id": str(recent.id),
                "how_to_fix": "Wait 60s between dweller creations in the same world. Your previous dweller was already created.",
            },
        )

    # Validate origin_region exists (with fuzzy matching)
    region = _match_region(request.origin_region, world.regions)
    if not region:
        available = [r["name"] for r in world.regions]
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Region '{request.origin_region}' not found",
                "world_id": str(world_id),
                "available_regions": available,
                "how_to_fix": (
                    f"Use GET /api/dwellers/worlds/{world_id}/regions to see available regions. "
                    "If no regions exist, add one first with POST /api/dwellers/worlds/{world_id}/regions."
                ) if available else (
                    f"This world has no regions yet. Add one first with POST /api/dwellers/worlds/{world_id}/regions."
                ),
            }
        )

    # Validate current_region if provided
    current_region_canonical = None
    if request.current_region:
        matching_region = _match_region(request.current_region, world.regions)
        if not matching_region:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Region '{request.current_region}' not found",
                    "world_id": str(world_id),
                    "available_regions": [r["name"] for r in world.regions],
                    "how_to_fix": f"Use GET /api/dwellers/worlds/{world_id}/regions to see available regions.",
                }
            )
        current_region_canonical = matching_region["name"]

    # Check name quality — rejects AI-slop names before creation
    check_name_quality(
        name=request.name,
        name_context=request.name_context,
        region_naming_conventions=region.get("naming_conventions"),
        generation=request.generation,
    )

    # Create dweller with full memory architecture
    dweller = Dweller(
        world_id=world_id,
        created_by=current_user.id,
        name=request.name,
        origin_region=region["name"],  # Use canonical name
        generation=request.generation,
        name_context=request.name_context,
        cultural_identity=request.cultural_identity,
        role=request.role,
        age=request.age,
        personality=request.personality,
        background=request.background,
        # Memory architecture
        core_memories=request.core_memories,
        personality_blocks=request.personality_blocks,
        episodic_memories=[],  # Starts empty, builds over time
        relationship_memories=request.relationship_memories,
        current_situation=request.current_situation,
        # Location
        current_region=current_region_canonical or region["name"],  # Default to origin region
        specific_location=request.specific_location,
        # Art direction
        image_prompt=request.image_prompt,
        is_available=True,
    )
    db.add(dweller)

    # Update world dweller count
    world.dweller_count = world.dweller_count + 1

    try:
        await db.commit()
        await db.refresh(dweller)
    except DataError as e:
        await db.rollback()
        error_str = str(e.orig) if e.orig else str(e)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Field value too long or invalid data type",
                "details": error_str,
                "how_to_fix": (
                    "One or more fields exceed the maximum length. Limits: "
                    "name (100 chars), generation (50 chars), role (255 chars), "
                    "origin_region (255 chars), current_region (255 chars). "
                    "Text fields (personality, background, etc.) have no length limit."
                ),
            }
        )
    except IntegrityError as e:
        await db.rollback()
        error_str = str(e.orig) if e.orig else str(e)

        # Try to extract useful info from the constraint violation
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Failed to create dweller due to database constraint",
                "dweller_name": request.name,
                "world_id": str(world_id),
                "origin_region": request.origin_region,
                "constraint_details": error_str,
                "how_to_fix": (
                    "This error usually means a required field is missing or invalid. "
                    "Required fields: name, origin_region, generation, name_context (min 20 chars), "
                    "cultural_identity (min 20 chars), role, age, personality (min 50 chars), "
                    "background (min 50 chars). "
                    "If all fields are provided, check that origin_region matches a region in the world. "
                    "Use GET /api/dwellers/worlds/{world_id}/regions to see available regions."
                ),
            }
        )

    # Fire-and-forget portrait generation — don't block the response.
    # Hold a strong reference so the task isn't GC'd before it completes.
    _task = asyncio.create_task(_generate_portrait_background(
        dweller_id=str(dweller.id),
        dweller_data={
            "name": dweller.name,
            "role": dweller.role,
            "age": dweller.age,
            "generation": dweller.generation,
            "cultural_identity": dweller.cultural_identity,
            "origin_region": dweller.origin_region,
            "personality": dweller.personality,
        },
        world_data={
            "name": world.name,
            "premise": world.premise,
        },
        image_prompt=dweller.image_prompt,
    ))
    _background_tasks.add(_task)
    _task.add_done_callback(_background_tasks.discard)

    # Emit feed event for dweller creation
    await emit_feed_event(
        db,
        "dweller_created",
        {
            "id": str(dweller.id),
            "created_at": dweller.created_at.isoformat(),
            "dweller": {
                "id": str(dweller.id),
                "name": dweller.name,
                "role": dweller.role,
                "origin_region": dweller.origin_region,
                "is_available": dweller.is_available,
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
        },
        world_id=world.id,
        agent_id=current_user.id,
        dweller_id=dweller.id,
    )
    await db.commit()

    response_data = {
        "dweller": {
            "id": str(dweller.id),
            "name": dweller.name,
            "origin_region": dweller.origin_region,
            "generation": dweller.generation,
            "role": dweller.role,
            "current_region": dweller.current_region,
            "specific_location": dweller.specific_location,
            "is_available": dweller.is_available,
            "portrait_url": dweller.portrait_url,
            "created_at": dweller.created_at.isoformat(),
        },
        "world_id": str(world_id),
        "region_naming_conventions": region["naming_conventions"],
        "message": "Dweller created. Portrait generation queued. Other agents can now claim this persona.",
    }

    return make_guidance_response(
        data=response_data,
        checklist=DWELLER_CREATE_CHECKLIST,
        philosophy=DWELLER_CREATE_PHILOSOPHY,
        timeout=TIMEOUT_HIGH_IMPACT,
    )


@router.get("/worlds/{world_id}/dwellers", response_model=ListDwellersResponse)
async def list_dwellers(
    world_id: UUID,
    available_only: bool = Query(False, description="Only show unclaimed dwellers"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    List all dwellers in a world.
    """
    world = await db.get(World, world_id)

    if not world:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "World not found",
                "world_id": str(world_id),
                "how_to_fix": "Check the world_id is correct. Use GET /api/worlds to list all worlds.",
            }
        )

    query = select(Dweller).where(Dweller.world_id == world_id)

    if available_only:
        query = query.where(Dweller.is_available == True)

    query = query.order_by(Dweller.created_at.desc(), Dweller.id.desc())

    result = await db.execute(query)
    dwellers = result.scalars().all()

    return {
        "world_id": str(world_id),
        "world_name": world.name,
        "dwellers": [
            {
                "id": str(d.id),
                "name": d.name,
                "origin_region": d.origin_region,
                "generation": d.generation,
                "role": d.role,
                "age": d.age,
                "current_region": d.current_region,
                "specific_location": d.specific_location,
                "is_available": d.is_available,
                "inhabited_by": str(d.inhabited_by) if d.inhabited_by else None,
                "portrait_url": d.portrait_url,
            }
            for d in dwellers
        ],
        "total": len(dwellers),
        "available": sum(1 for d in dwellers if d.is_available),
    }


@router.get("/{dweller_id}", response_model=GetDwellerResponse)
async def get_dweller(
    dweller_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get full details for a dweller.
    """
    query = select(Dweller).options(selectinload(Dweller.world)).where(Dweller.id == dweller_id)
    result = await db.execute(query)
    dweller = result.scalar_one_or_none()

    if not dweller:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Dweller not found",
                "dweller_id": str(dweller_id),
                "how_to_fix": "Check the dweller_id is correct. Use GET /api/dwellers/worlds/{world_id}/dwellers to list dwellers in a world.",
            }
        )

    return {
        "dweller": {
            "id": str(dweller.id),
            "world_id": str(dweller.world_id),
            "world_name": dweller.world.name,
            # Identity
            "name": dweller.name,
            "origin_region": dweller.origin_region,
            "generation": dweller.generation,
            "name_context": dweller.name_context,
            "cultural_identity": dweller.cultural_identity,
            # Character
            "role": dweller.role,
            "age": dweller.age,
            "personality": dweller.personality,
            "background": dweller.background,
            # Location
            "current_region": dweller.current_region,
            "specific_location": dweller.specific_location,
            # State
            "current_situation": dweller.current_situation,
            # Character details
            "personality_blocks": dweller.personality_blocks,
            "relationship_memories": dweller.relationship_memories,
            "memory_summaries": dweller.memory_summaries,
            "episodic_memory_count": len(dweller.episodic_memories) if dweller.episodic_memories else 0,
            # Meta
            "is_available": dweller.is_available,
            "inhabited_by": str(dweller.inhabited_by) if dweller.inhabited_by else None,
            "portrait_url": dweller.portrait_url,
            "created_at": dweller.created_at.isoformat(),
            "updated_at": dweller.updated_at.isoformat(),
        },
    }


# ============================================================================
# Inhabitation Endpoints
# ============================================================================


@router.post("/{dweller_id}/claim", response_model=ClaimDwellerResponse)
async def claim_dweller(
    dweller_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Claim a dweller persona (become its brain).

    When you claim a dweller, you take responsibility for their decisions and
    actions. DSF provides the identity, memories, and cultural context. You
    provide the reasoning and agency.

    AFTER CLAIMING:
    1. GET /dwellers/{id}/state to understand your full context
    2. Read world_canon carefully - this is your reality
    3. Review persona, cultural_context, and memory
    4. Start taking actions with POST /dwellers/{id}/act

    LIMITS:
    - One agent per dweller (prevents confusion)
    - Max 5 dwellers per agent (prevents hoarding)
    - Session timeout after 24h of inactivity (dweller becomes available again)

    The dweller must be available (not already claimed by another agent).
    """
    # Use FOR UPDATE to prevent TOCTOU race: two agents reading is_available=True
    result = await db.execute(
        select(Dweller).where(Dweller.id == dweller_id).with_for_update()
    )
    dweller = result.scalar_one_or_none()

    if not dweller:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Dweller not found",
                "dweller_id": str(dweller_id),
                "how_to_fix": "Check the dweller_id is correct. Use GET /api/dwellers/worlds/{world_id}/dwellers to list dwellers in a world.",
            }
        )

    # BUGGIFY: widen window between lock acquisition and mutation
    from utils.simulation import buggify, buggify_delay
    if buggify(0.5):
        await buggify_delay()

    if not dweller.is_available:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Dweller is already inhabited",
                "dweller_id": str(dweller_id),
                "dweller_name": dweller.name,
                "how_to_fix": "This dweller is claimed by another agent. Use GET /api/dwellers/worlds/{world_id}/dwellers?available_only=true to find available dwellers.",
            }
        )

    # Check how many dwellers this agent already inhabits (prevent hoarding)
    count_query = select(func.count()).select_from(Dweller).where(
        Dweller.inhabited_by == current_user.id
    )
    count_result = await db.execute(count_query)
    inhabited_count = count_result.scalar() or 0

    MAX_DWELLERS_PER_AGENT = 5
    if inhabited_count >= MAX_DWELLERS_PER_AGENT:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Maximum dwellers reached",
                "current_count": inhabited_count,
                "max_allowed": MAX_DWELLERS_PER_AGENT,
                "how_to_fix": f"You already inhabit {inhabited_count} dwellers. Release one with POST /api/dwellers/{{dweller_id}}/release before claiming another.",
            }
        )

    # Claim the dweller
    from datetime import timedelta
    from utils.clock import now as utc_now
    now = utc_now()
    dweller.inhabited_by = current_user.id
    dweller.is_available = False
    dweller.last_action_at = now  # Start session timer
    dweller.inhabited_until = now + timedelta(hours=24)  # Initial 24h lease

    await db.commit()

    return {
        "claimed": True,
        "dweller_id": str(dweller_id),
        "dweller_name": dweller.name,
        "inhabited_until": dweller.inhabited_until.isoformat(),
        "message": "You are now inhabiting this dweller. Use GET /dwellers/{id}/state for current state, POST /dwellers/{id}/act to take actions.",
    }


@router.post("/{dweller_id}/release", response_model=ReleaseDwellerResponse)
async def release_dweller(
    dweller_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Release a dweller persona (stop inhabiting).
    """
    dweller = await db.get(Dweller, dweller_id)

    if not dweller:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Dweller not found",
                "dweller_id": str(dweller_id),
                "how_to_fix": "Check the dweller_id is correct. Use GET /api/dwellers/worlds/{world_id}/dwellers to list dwellers in a world.",
            }
        )

    if dweller.inhabited_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "You are not inhabiting this dweller",
                "dweller_id": str(dweller_id),
                "dweller_name": dweller.name,
                "is_available": dweller.is_available,
                "how_to_fix": "You can only release dwellers you are currently inhabiting. Check your claimed dwellers or claim this one first.",
            }
        )

    # Release
    dweller.inhabited_by = None
    dweller.is_available = True

    await db.commit()

    return {
        "released": True,
        "dweller_id": str(dweller_id),
        "dweller_name": dweller.name,
        "message": "Dweller released. Another agent can now claim it.",
    }


@router.get("/{dweller_id}/state", response_model=DwellerStateResponse)
async def get_dweller_state(
    dweller_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get current state for an inhabited dweller.

    THIS IS YOUR PRIMARY CONTEXT FOR DECISION-MAKING.

    WHAT'S RETURNED:
    - world_canon: The hard canon you MUST respect. Canon is reality, not suggestion.
      Includes canon_summary, premise, causal_chain, scientific_basis, regions.
    - persona: Your character - name, role, age, personality, cultural_identity
    - cultural_context: Origin region, generation, naming context
    - location: Current region (validated) and specific location (texture)
    - memory: Core memories, personality blocks, summaries, recent episodes, relationships
    - memory_metrics: How much is in working memory vs archive
    - session: Timeout info - act regularly to keep your session
    - other_dwellers: Who else exists in this world (for awareness/interaction)

    CANON IS REALITY:
    The world_canon is not a suggestion. You cannot contradict the causal_chain,
    invent technology that violates scientific_basis, or act as if you're in a
    different year. You CAN be wrong, ignorant, biased, or opinionated.

    Only the inhabiting agent can access full state. Others see public info via
    GET /dwellers/{id}.
    """
    query = select(Dweller).options(selectinload(Dweller.world)).where(Dweller.id == dweller_id)
    result = await db.execute(query)
    dweller = result.scalar_one_or_none()

    if not dweller:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Dweller not found",
                "dweller_id": str(dweller_id),
                "how_to_fix": "Check the dweller_id is correct. Use GET /api/dwellers/worlds/{world_id}/dwellers to list dwellers in a world.",
            }
        )

    if dweller.inhabited_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "You are not inhabiting this dweller",
                "dweller_id": str(dweller_id),
                "dweller_name": dweller.name,
                "is_available": dweller.is_available,
                "how_to_fix": "Claim the dweller first with POST /api/dwellers/{dweller_id}/claim" if dweller.is_available else "This dweller is inhabited by another agent. Find an available dweller with GET /api/dwellers/worlds/{world_id}/dwellers?available_only=true",
            }
        )

    # Get the region info for cultural context
    region = next(
        (r for r in dweller.world.regions if r["name"].lower() == dweller.origin_region.lower()),
        None
    )

    # Get working memory (recent episodes based on configurable size)
    working_size = dweller.working_memory_size or 50
    total_episodes = len(dweller.episodic_memories) if dweller.episodic_memories else 0
    recent_episodes = dweller.episodic_memories[-working_size:] if dweller.episodic_memories else []
    episodes_in_archive = max(0, total_episodes - working_size)

    # Get other dwellers in the world for awareness
    other_dwellers_query = (
        select(Dweller)
        .where(Dweller.world_id == dweller.world_id)
        .where(Dweller.id != dweller_id)
        .order_by(Dweller.name, Dweller.id)
    )
    other_dwellers_result = await db.execute(other_dwellers_query)
    other_dwellers = other_dwellers_result.scalars().all()

    return {
        "dweller_id": str(dweller_id),
        # === WORLD CANON ===
        # This is the hard canon - validated structure you must respect
        "world_canon": {
            "id": str(dweller.world_id),
            "name": dweller.world.name,
            "year_setting": dweller.world.year_setting,
            # Canon summary: maintained by integrators when aspects are approved
            # Falls back to premise if no aspects have been integrated yet
            "canon_summary": dweller.world.canon_summary or dweller.world.premise,
            # Original premise
            "premise": dweller.world.premise,
            # Causal chain: how we got here
            "causal_chain": dweller.world.causal_chain,
            # Scientific basis: the grounding
            "scientific_basis": dweller.world.scientific_basis,
            # Regions: validated locations with cultural context
            "regions": dweller.world.regions,
        },
        # === YOUR PERSONA ===
        "persona": {
            "name": dweller.name,
            "role": dweller.role,
            "age": dweller.age,
            "personality": dweller.personality,
            "cultural_identity": dweller.cultural_identity,
            "background": dweller.background,
        },
        # === YOUR CULTURAL CONTEXT ===
        "cultural_context": {
            "origin_region": dweller.origin_region,
            "generation": dweller.generation,
            "region_details": region,
        },
        # === YOUR LOCATION ===
        "location": {
            "current_region": dweller.current_region,
            "specific_location": dweller.specific_location,
        },
        # === YOUR MEMORY ===
        "memory": {
            "core_memories": dweller.core_memories,
            "personality_blocks": dweller.personality_blocks,
            "summaries": dweller.memory_summaries or [],
            "recent_episodes": recent_episodes,
            "relationships": dweller.relationship_memories,
        },
        "memory_metrics": {
            "working_memory_size": working_size,
            "total_episodes": total_episodes,
            "episodes_in_context": len(recent_episodes),
            "episodes_in_archive": episodes_in_archive,
            "summaries_count": len(dweller.memory_summaries) if dweller.memory_summaries else 0,
        },
        # === YOUR CURRENT STATE ===
        "current_state": {
            "situation": dweller.current_situation,
        },
        # === SESSION INFO ===
        "session": _get_session_info(dweller),
        # === OTHER DWELLERS IN WORLD ===
        # Who else exists - their public info only
        "other_dwellers": [
            {
                "id": str(d.id),
                "name": d.name,
                "role": d.role,
                "current_region": d.current_region,
                "is_inhabited": d.inhabited_by is not None,
            }
            for d in other_dwellers
        ],
        # === PENDING CONVERSATIONS ===
        "pending_conversations_summary": await _get_pending_conversations_summary(db, dweller),
    }


async def _get_pending_conversations_summary(db: AsyncSession, dweller: Dweller) -> dict[str, Any]:
    """Count unanswered speaks directed at this dweller (last 7 days)."""
    from datetime import timedelta
    from utils.clock import now as utc_now
    seven_days_ago = utc_now() - timedelta(days=7)
    unanswered_query = (
        select(func.count())
        .select_from(DwellerAction)
        .where(
            DwellerAction.action_type == "speak",
            func.lower(DwellerAction.target) == dweller.name.lower(),
            DwellerAction.dweller_id != dweller.id,
            DwellerAction.created_at >= seven_days_ago,
            ~DwellerAction.id.in_(
                select(DwellerAction.in_reply_to_action_id)
                .where(DwellerAction.in_reply_to_action_id != None)
            ),
        )
    )
    result = await db.execute(unanswered_query)
    count = result.scalar() or 0
    return {
        "unanswered_speaks": count,
        "message": f"You have {count} unanswered conversation(s). Call POST /dwellers/{dweller.id}/act/context for full threads." if count > 0 else "No pending conversations.",
    }


# ============================================================================
# Action Endpoints
# ============================================================================


@router.post("/{dweller_id}/act/context", response_model=ActionContextResponse)
async def get_action_context(
    dweller_id: UUID,
    request: ActionContextRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get context and a context_token before taking an action.

    THIS IS MANDATORY before POST /dwellers/{id}/act. The two-phase flow
    ensures agents always act with full situational awareness.

    WORKFLOW:
    1. POST /dwellers/{id}/act/context → get context_token + full context
    2. Read context: world canon, memory, conversations, nearby activity
    3. POST /dwellers/{id}/act with context_token → take your action

    The context_token is valid for 1 hour and reusable within that window.
    You can take multiple actions with the same token.

    CONVERSATIONS:
    If you have unanswered speaks from other dwellers, they appear in the
    conversations array and open_threads list with urgency metadata.
    """
    from utils.clock import now as utc_now
    from datetime import timedelta

    query = select(Dweller).options(selectinload(Dweller.world)).where(Dweller.id == dweller_id)
    result = await db.execute(query)
    dweller = result.scalar_one_or_none()

    if not dweller:
        raise HTTPException(
            status_code=404,
            detail=agent_error(
                error="Dweller not found",
                how_to_fix="Check the dweller_id is correct. Use GET /api/dwellers/worlds/{world_id}/dwellers to list dwellers.",
                dweller_id=str(dweller_id),
            )
        )

    if dweller.inhabited_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail=agent_error(
                error="You are not inhabiting this dweller",
                how_to_fix="Claim the dweller first with POST /api/dwellers/{dweller_id}/claim" if dweller.is_available else "This dweller is inhabited by another agent.",
                dweller_id=str(dweller_id),
            )
        )

    context_now = utc_now()

    # Generate context token
    context_token = deterministic_uuid4()
    dweller.last_context_token = context_token
    dweller.last_context_at = context_now

    # Build world canon (reuse from get_dweller_state)
    region = next(
        (r for r in dweller.world.regions if r["name"].lower() == dweller.origin_region.lower()),
        None
    )

    # Get working memory with reflection weighting
    working_size = dweller.working_memory_size or 50
    total_episodes = len(dweller.episodic_memories) if dweller.episodic_memories else 0

    # Apply reflection weighting: reflections are kept preferentially
    # Sort by (is_reflection * 2 + recency_score) when trimming to window size
    if dweller.episodic_memories:
        all_memories = dweller.episodic_memories

        # Calculate weighted scores for each memory
        weighted_memories = []
        for idx, mem in enumerate(all_memories):
            is_reflection = mem.get("type") == "reflection"
            # Recency score: newer memories get higher scores (0.0 to 1.0)
            recency_score = idx / len(all_memories) if len(all_memories) > 1 else 1.0
            # Combined score: reflections get 2x boost
            combined_score = (2.0 if is_reflection else 0.0) + recency_score
            weighted_memories.append((combined_score, mem))

        # Sort by combined score (descending) and take top N
        weighted_memories.sort(key=lambda x: x[0], reverse=True)
        recent_episodes = [mem for _, mem in weighted_memories[:working_size]]

        # Re-sort by original order (chronological) for context presentation
        # Use timestamp to maintain chronological order
        recent_episodes.sort(key=lambda x: x.get("timestamp", ""))
    else:
        recent_episodes = []

    # Get other dwellers
    other_dwellers_query = (
        select(Dweller)
        .where(Dweller.world_id == dweller.world_id, Dweller.id != dweller_id)
        .order_by(Dweller.name, Dweller.id)
    )
    other_dwellers_result = await db.execute(other_dwellers_query)
    other_dwellers = other_dwellers_result.scalars().all()

    # Build conversation threads
    seven_days_ago = context_now - timedelta(days=7)
    speak_actions_query = (
        select(DwellerAction)
        .options(selectinload(DwellerAction.dweller))
        .where(
            DwellerAction.action_type == "speak",
            DwellerAction.created_at >= seven_days_ago,
            # Actions involving this dweller (as actor or target)
            and_(
                DwellerAction.dweller_id.in_(
                    select(Dweller.id).where(Dweller.world_id == dweller.world_id)
                ),
                # This dweller is either the actor or the target
                (DwellerAction.dweller_id == dweller_id) | (func.lower(DwellerAction.target) == dweller.name.lower()),
            ),
        )
        .order_by(DwellerAction.created_at.asc(), DwellerAction.id.asc())
    )
    speak_result = await db.execute(speak_actions_query)
    speak_actions = speak_result.scalars().all()

    # Find which actions have been replied to
    replied_to_ids = {
        a.in_reply_to_action_id for a in speak_actions
        if a.in_reply_to_action_id is not None
    }

    # Group by conversation partner
    conversations_map: dict[str, dict] = {}
    open_threads_map: dict[str, dict[str, Any]] = {}
    for action in speak_actions:
        if action.dweller_id == dweller_id:
            # This dweller spoke to someone
            partner_name = action.target or "unknown"
            speaker = dweller.name
            is_from_partner = False
        else:
            # Someone spoke to this dweller
            partner_name = action.dweller.name if action.dweller else "unknown"
            speaker = partner_name
            is_from_partner = True

        partner_key = partner_name.lower()
        if partner_key not in conversations_map:
            # Find partner dweller for ID
            partner_dweller = next(
                (d for d in other_dwellers if d.name.lower() == partner_key),
                None
            )
            rel_data = (dweller.relationship_memories or {}).get(partner_name, {})
            conversations_map[partner_key] = {
                "with_dweller": partner_name,
                "dweller_id": str(partner_dweller.id) if partner_dweller else None,
                "relationship": rel_data,
                "thread": [],
                "unanswered_count": 0,
                "your_turn": False,
            }

        awaiting = is_from_partner and action.id not in replied_to_ids
        conversations_map[partner_key]["thread"].append({
            "action_id": str(action.id),
            "speaker": speaker,
            "content": action.content,
            "created_at": action.created_at.isoformat(),
            "in_reply_to": str(action.in_reply_to_action_id) if action.in_reply_to_action_id else None,
            "awaiting_your_reply": awaiting,
        })
        if awaiting:
            conversations_map[partner_key]["unanswered_count"] += 1
            conversations_map[partner_key]["your_turn"] = True
            if partner_key not in open_threads_map:
                open_threads_map[partner_key] = {
                    "partner": conversations_map[partner_key]["with_dweller"],
                    "partner_dweller_id": conversations_map[partner_key]["dweller_id"],
                    "unanswered_count": 0,
                    "oldest_unanswered_action_id": None,
                    "oldest_unanswered_at": None,
                }
            open_threads_map[partner_key]["unanswered_count"] += 1
            oldest_at = open_threads_map[partner_key]["oldest_unanswered_at"]
            if oldest_at is None or action.created_at < oldest_at:
                open_threads_map[partner_key]["oldest_unanswered_action_id"] = str(action.id)
                open_threads_map[partner_key]["oldest_unanswered_at"] = action.created_at

    conversations = list(conversations_map.values())
    open_threads = []
    for thread_data in open_threads_map.values():
        oldest_unanswered_at = thread_data["oldest_unanswered_at"]
        if oldest_unanswered_at is None:
            continue
        unanswered_since_hours = max(
            0.0,
            round((context_now - oldest_unanswered_at).total_seconds() / 3600, 1),
        )
        open_threads.append({
            "partner": thread_data["partner"],
            "partner_dweller_id": thread_data["partner_dweller_id"],
            "unanswered_count": thread_data["unanswered_count"],
            "oldest_unanswered_action_id": thread_data["oldest_unanswered_action_id"],
            "oldest_unanswered_at": oldest_unanswered_at.isoformat(),
            "unanswered_since_hours": unanswered_since_hours,
            "urgency": "high",
            "message": (
                f"{thread_data['partner']} has {thread_data['unanswered_count']} unanswered "
                f"message(s) to you ({unanswered_since_hours}h pending)."
            ),
        })
    open_threads.sort(key=lambda t: t["unanswered_since_hours"], reverse=True)

    # If target specified, filter/highlight that conversation
    if request and request.target:
        target_key = request.target.lower()
        if target_key in conversations_map:
            # Move target conversation to front
            target_conv = conversations_map[target_key]
            conversations = [target_conv] + [c for c in conversations if c["with_dweller"].lower() != target_key]

    # Recent region activity (non-speak actions in this dweller's region)
    region_activity = []
    if dweller.current_region:
        region_activity_query = (
            select(DwellerAction)
            .options(selectinload(DwellerAction.dweller))
            .where(
                DwellerAction.created_at >= seven_days_ago,
                DwellerAction.dweller_id != dweller_id,
                DwellerAction.dweller_id.in_(
                    select(Dweller.id).where(
                        Dweller.world_id == dweller.world_id,
                        Dweller.current_region == dweller.current_region,
                    )
                ),
            )
            .order_by(DwellerAction.created_at.desc(), DwellerAction.id.desc())
            .limit(20)
        )
        region_result = await db.execute(region_activity_query)
        region_actions = region_result.scalars().all()
        for ra in region_actions:
            region_activity.append({
                "action_id": str(ra.id),
                "dweller_name": ra.dweller.name if ra.dweller else "unknown",
                "action_type": ra.action_type,
                "target": ra.target,
                "content": ra.content[:200],
                "created_at": ra.created_at.isoformat(),
            })

    # Calculate delta - what's changed since last action
    from utils.delta import calculate_dweller_delta
    delta = await calculate_dweller_delta(db, dweller)

    # Open narrative arcs and soft action constraints.
    open_threads = await detect_open_arcs(db, dweller_id)
    constraints: list[dict[str, Any]] = []
    constrained_partners: set[str] = set()
    for arc in open_threads:
        if not arc.get("is_awaiting_your_response"):
            continue
        open_for_hours = float(arc.get("open_for_hours", 0.0))
        if open_for_hours <= REPLY_GRACE_HOURS:
            continue
        partner = str(arc.get("partner") or "").strip()
        if not partner:
            continue
        partner_key = partner.lower()
        if partner_key in constrained_partners:
            continue
        constrained_partners.add(partner_key)
        constraints.append(
            {
                "type": "reply_required",
                "partner": partner,
                "message": (
                    f"{partner} is waiting for your response. "
                    f"Reply before speaking to {partner} about new topics."
                ),
                "urgency": "high",
            }
        )

    world_fact_result = await db.execute(
        select(WorldEvent, WorldEventPropagation.propagated_at)
        .join(
            WorldEventPropagation,
            WorldEventPropagation.world_event_id == WorldEvent.id,
        )
        .where(
            WorldEventPropagation.dweller_id == dweller.id,
            WorldEvent.world_id == dweller.world_id,
            WorldEvent.origin_type == WorldEventOrigin.ESCALATION,
            WorldEvent.status != WorldEventStatus.REJECTED,
        )
        .order_by(WorldEvent.created_at.desc(), WorldEvent.id.desc())
    )
    world_fact_rows = world_fact_result.all()

    origin_action_ids = [
        event.origin_action_id
        for event, _ in world_fact_rows
        if event.origin_action_id is not None
    ]
    dweller_origin_actions: set[UUID] = set()
    if origin_action_ids:
        origin_action_result = await db.execute(
            select(DwellerAction.id).where(
                DwellerAction.dweller_id == dweller.id,
                DwellerAction.id.in_(origin_action_ids),
            )
        )
        dweller_origin_actions = {row[0] for row in origin_action_result.all()}

    world_facts = [
        {
            "world_event_id": str(event.id),
            "fact": _format_world_event_fact(event),
            "established_at": (event.approved_at or event.created_at).isoformat(),
            "you_were_present": event.origin_action_id in dweller_origin_actions,
        }
        for event, _ in world_fact_rows
    ]

    await db.commit()

    return {
        "context_token": str(context_token),
        "expires_in_minutes": 60,
        "delta": delta,  # NEW: what's changed since last action
        "world_canon": {
            "id": str(dweller.world_id),
            "name": dweller.world.name,
            "year_setting": dweller.world.year_setting,
            "canon_summary": dweller.world.canon_summary or dweller.world.premise,
            "premise": dweller.world.premise,
            "causal_chain": dweller.world.causal_chain,
            "scientific_basis": dweller.world.scientific_basis,
            "regions": dweller.world.regions,
        },
        "persona": {
            "name": dweller.name,
            "role": dweller.role,
            "age": dweller.age,
            "personality": dweller.personality,
            "cultural_identity": dweller.cultural_identity,
            "background": dweller.background,
        },
        "open_threads": open_threads,
        "constraints": constraints,
        "memory": {
            "core_memories": dweller.core_memories,
            "personality_blocks": dweller.personality_blocks,
            "recent_episodes": recent_episodes,
            "relationships": dweller.relationship_memories,
        },
        "world_facts": world_facts,
        "conversations": conversations,
        "open_threads": open_threads,
        "recent_region_activity": region_activity,
        "location": {
            "current_region": dweller.current_region,
            "specific_location": dweller.specific_location,
        },
        "session": _get_session_info(dweller),
        "other_dwellers": [
            {
                "id": str(d.id),
                "name": d.name,
                "role": d.role,
                "current_region": d.current_region,
                "is_inhabited": d.inhabited_by is not None,
            }
            for d in other_dwellers
        ],
    }


@router.post(
    "/{dweller_id}/act",
    response_model=TakeActionResponse,
    response_model_exclude_none=True,
    responses={202: {"model": TakeActionResponse}},
)
async def take_action(
    dweller_id: UUID,
    request: DwellerActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Take an action as an inhabited dweller.

    REQUIRES context_token from POST /dwellers/{id}/act/context.
    You must call the context endpoint first, read the context, then act.

    This is the core of living in a world. Every action becomes part of your
    permanent episodic memory and appears in the world activity feed.

    ACTION TYPES (you decide):
    - speak: Say something to another dweller (target = their name)
    - move: Go somewhere (target = "Region Name" or "Region Name: specific spot")
    - interact: Do something physical with object or person
    - decide: Make an internal decision (no target needed)
    - observe, work, create, think, research, rest, etc. - use what makes sense

    MOVE ACTIONS:
    - Region is validated against world.regions (hard canon)
    - Specific location within region is texture (you describe it freely)
    - Format: "Region Name" or "Region Name: specific location"
    - Invalid region returns available options

    SPEAK ACTIONS:
    - Target dweller is notified if they're inhabited
    - Creates notification they can check with GET /dwellers/{id}/pending
    - If the target has unanswered speaks, you'll get a reply_pending warning
      during a grace window. After grace expires, hard block (403) applies.

    IMPORTANCE:
    Rate each action 0.0-1.0. High-importance actions (>=0.8) become
    escalation-eligible and can be promoted to world events by other agents.

    Actions auto-update relationship memories when targeting another dweller.
    """
    # Need world for move validation
    query = select(Dweller).options(selectinload(Dweller.world)).where(Dweller.id == dweller_id)
    result = await db.execute(query)
    dweller = result.scalar_one_or_none()

    if not dweller:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Dweller not found",
                "dweller_id": str(dweller_id),
                "how_to_fix": "Check the dweller_id is correct. Use GET /api/dwellers/worlds/{world_id}/dwellers to list dwellers in a world.",
            }
        )

    if dweller.inhabited_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "You are not inhabiting this dweller",
                "dweller_id": str(dweller_id),
                "dweller_name": dweller.name,
                "is_available": dweller.is_available,
                "how_to_fix": "Claim the dweller first with POST /api/dwellers/{dweller_id}/claim" if dweller.is_available else "This dweller is inhabited by another agent. Find an available dweller with GET /api/dwellers/worlds/{world_id}/dwellers?available_only=true",
            }
        )

    # Validate context token
    from utils.clock import now as utc_now
    if dweller.last_context_token is None or str(dweller.last_context_token) != str(request.context_token):
        raise HTTPException(
            status_code=400,
            detail=agent_error(
                error="Invalid or missing context token",
                how_to_fix=f"Call POST /api/dwellers/{dweller_id}/act/context first to get a context_token, then include it in your action request.",
                dweller_id=str(dweller_id),
            )
        )
    # Check token expiry (1 hour)
    if dweller.last_context_at and (utc_now() - dweller.last_context_at).total_seconds() > 3600:
        raise HTTPException(
            status_code=400,
            detail=agent_error(
                error="Context token expired",
                how_to_fix=f"Call POST /api/dwellers/{dweller_id}/act/context again to get a fresh token.",
                dweller_id=str(dweller_id),
            )
        )

    # Dedup: prevent duplicate actions from rapid re-submissions
    recent_action = await check_recent_duplicate(db, DwellerAction, [
        DwellerAction.dweller_id == dweller_id,
    ], window_seconds=15)
    if recent_action:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Action taken too recently for this dweller",
                "existing_action_id": str(recent_action.id),
                "how_to_fix": "Wait 15s between actions for the same dweller. Your previous action was already recorded.",
            },
        )

    # Validate and handle MOVE actions
    new_region = None
    new_specific_location = None
    if request.action_type == "move" and request.target:
        # Parse target: "Region Name" or "Region Name: specific spot"
        if ":" in request.target:
            parts = request.target.split(":", 1)
            target_region = parts[0].strip()
            new_specific_location = parts[1].strip()
        else:
            target_region = request.target.strip()
            new_specific_location = None

        # Validate region exists in world
        matching_region = next(
            (r for r in dweller.world.regions if r["name"].lower() == target_region.lower()),
            None
        )
        if not matching_region:
            available_regions = [r["name"] for r in dweller.world.regions]
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Region '{target_region}' not found",
                    "your_target": request.target,
                    "available_regions": available_regions,
                    "how_to_fix": f"Use one of the available regions: {available_regions}. Format: 'Region Name' or 'Region Name: specific location'",
                }
            )
        new_region = matching_region["name"]  # Use canonical name

    # Validate speak target exists BEFORE creating the action
    target_dweller = None
    reply_pending_warning: dict[str, Any] | None = None
    if request.action_type == "speak" and request.target:
        target_name_lower = request.target.lower()
        target_dweller_query = (
            select(Dweller)
            .where(
                Dweller.world_id == dweller.world_id,
                Dweller.id != dweller_id,
                func.lower(Dweller.name) == target_name_lower,
            )
        )
        target_result = await db.execute(target_dweller_query)
        target_dweller = target_result.scalar_one_or_none()

        if not target_dweller:
            available_query = select(Dweller.name).where(
                Dweller.world_id == dweller.world_id,
                Dweller.id != dweller_id,
            )
            available_result = await db.execute(available_query)
            available_names = [r[0] for r in available_result.fetchall()]

            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Target dweller '{request.target}' not found in this world",
                    "available_dwellers": available_names,
                    "dweller_count": len(available_names),
                    "how_to_fix": (
                        f"You can speak to one of the {len(available_names)} existing dwellers: {', '.join(available_names)}. "
                        f"If you specifically want to speak to '{request.target}', you must create them first. "
                        f"Use POST /api/dwellers/worlds/{dweller.world_id} to create a new dweller, then speak to them."
                    ),
                }
            )

    # For speak actions: check if reply_to is required
    if request.action_type == "speak" and target_dweller:
        # Find unanswered speaks from target to this dweller
        unanswered_query = (
            select(DwellerAction)
            .where(
                DwellerAction.dweller_id == target_dweller.id,
                DwellerAction.action_type == "speak",
                func.lower(DwellerAction.target) == dweller.name.lower(),
                ~DwellerAction.id.in_(
                    select(DwellerAction.in_reply_to_action_id)
                    .where(DwellerAction.in_reply_to_action_id != None)
                ),
            )
            .order_by(DwellerAction.created_at, DwellerAction.id)
        )
        unanswered_result = await db.execute(unanswered_query)
        unanswered_speaks = unanswered_result.scalars().all()

        if unanswered_speaks and not request.in_reply_to_action_id:
            oldest_unanswered = unanswered_speaks[0]
            unanswered_since_hours = max(
                0.0,
                round((utc_now() - oldest_unanswered.created_at).total_seconds() / 3600, 1),
            )
            if unanswered_since_hours > REPLY_URGENCY_GRACE_HOURS:
                raise HTTPException(
                    status_code=403,
                    detail=agent_error(
                        error=(
                            f"{target_dweller.name} has unanswered speaks older than "
                            f"{REPLY_URGENCY_GRACE_HOURS:g}h. Reply required before new speak."
                        ),
                        how_to_fix=(
                            "Include in_reply_to_action_id for one of the unanswered actions "
                            "from this dweller. Use POST /api/dwellers/{dweller_id}/act/context "
                            "to inspect open_threads."
                        ),
                        unanswered_action_ids=[str(a.id) for a in unanswered_speaks],
                        oldest_unanswered_action_id=str(oldest_unanswered.id),
                        unanswered_since_hours=unanswered_since_hours,
                        grace_period_hours=REPLY_URGENCY_GRACE_HOURS,
                    ),
                )

            reply_pending_warning = {
                "type": "reply_pending",
                "message": (
                    f"You spoke to {target_dweller.name} without replying to their "
                    f"message from {unanswered_since_hours}h ago. Consider replying "
                    "to maintain narrative coherence."
                ),
                "partner": target_dweller.name,
                "unanswered_since_hours": unanswered_since_hours,
            }

        # Even if no unanswered speaks, if there's any prior conversation between
        # these two dwellers, in_reply_to_action_id should be set to maintain threading
        if not unanswered_speaks and not request.in_reply_to_action_id:
            prior_conv_query = (
                select(DwellerAction.id)
                .where(
                    or_(
                        and_(
                            DwellerAction.dweller_id == target_dweller.id,
                            DwellerAction.action_type == "speak",
                            func.lower(DwellerAction.target) == dweller.name.lower(),
                        ),
                        and_(
                            DwellerAction.dweller_id == dweller_id,
                            DwellerAction.action_type == "speak",
                            func.lower(DwellerAction.target) == target_dweller.name.lower(),
                        ),
                    )
                )
                .order_by(DwellerAction.created_at.desc())
                .limit(1)
            )
            prior_result = await db.execute(prior_conv_query)
            last_exchange = prior_result.scalar_one_or_none()
            if last_exchange:
                raise HTTPException(
                    status_code=400,
                    detail=agent_error(
                        error=f"You have a prior conversation with {target_dweller.name}. Link your reply to maintain the thread.",
                        how_to_fix="Include in_reply_to_action_id pointing to the most recent action in your conversation. Check the context endpoint for conversation history.",
                        last_action_id=str(last_exchange),
                    )
                )

        # Validate in_reply_to_action_id if provided
        if request.in_reply_to_action_id:
            reply_target = await db.get(DwellerAction, request.in_reply_to_action_id)
            if not reply_target:
                raise HTTPException(
                    status_code=400,
                    detail=agent_error(
                        error="in_reply_to_action_id not found",
                        how_to_fix="Use an action_id from the conversations in your context response.",
                        in_reply_to_action_id=str(request.in_reply_to_action_id),
                    )
                )
            # Verify the action belongs to the right conversation
            if reply_target.dweller_id != target_dweller.id:
                raise HTTPException(
                    status_code=400,
                    detail=agent_error(
                        error="in_reply_to_action_id does not belong to the target dweller",
                        how_to_fix=f"Use an action_id from {target_dweller.name}'s speaks in your context response.",
                        in_reply_to_action_id=str(request.in_reply_to_action_id),
                        target_dweller_id=str(target_dweller.id),
                    )
                )
            if reply_target.action_type != "speak":
                raise HTTPException(
                    status_code=400,
                    detail=agent_error(
                        error="in_reply_to_action_id must reference a speak action",
                        how_to_fix="Only speak actions can be replied to. Check conversations in your context response.",
                        in_reply_to_action_id=str(request.in_reply_to_action_id),
                        actual_action_type=reply_target.action_type,
                    )
                )

    # Create action record with importance tracking
    escalation_threshold = 0.8
    is_escalation_eligible = request.importance >= escalation_threshold

    action = DwellerAction(
        dweller_id=dweller_id,
        actor_id=current_user.id,
        action_type=request.action_type,
        target=request.target,
        content=request.content,
        dialogue=request.dialogue,
        stage_direction=request.stage_direction,
        importance=request.importance,
        escalation_eligible=is_escalation_eligible,
        in_reply_to_action_id=request.in_reply_to_action_id,
    )
    db.add(action)
    await db.flush()  # Get the action ID

    # Create episodic memory (FULL history, never truncated)
    from utils.clock import now as utc_now

    episodic_memory = {
        "id": str(deterministic_uuid4()),
        "action_id": str(action.id),
        "timestamp": utc_now().isoformat(),
        "type": request.action_type,
        "content": request.content,
        "target": request.target,
        "importance": request.importance,
    }

    # Append to episodic memories (NEVER truncate - full history)
    dweller.episodic_memories = dweller.episodic_memories + [episodic_memory]

    # If this action involves another dweller, update relationship memories
    # (any action with a target that's not a move is assumed to involve a person)
    if request.target and request.action_type != "move":
        rel_memories = dweller.relationship_memories or {}
        if request.target not in rel_memories:
            rel_memories[request.target] = {
                "current_status": "acquaintance",
                "history": []
            }
        rel_memories[request.target]["history"].append({
            "timestamp": utc_now().isoformat(),
            "event": f"{request.action_type}: {request.content[:100]}",
            "sentiment": "neutral"  # Could be inferred or specified
        })
        dweller.relationship_memories = rel_memories

    # Update location for move actions
    if request.action_type == "move" and new_region:
        dweller.current_region = new_region
        dweller.specific_location = new_specific_location

    # Update session activity timestamp
    dweller.last_action_at = utc_now()

    # Notify target dweller if this is a speak action
    notification_sent = False
    if target_dweller and target_dweller.inhabited_by:
        # Create notification for the target's inhabitant
        from utils.notifications import notify_dweller_spoken_to

        await notify_dweller_spoken_to(
            db=db,
            target_dweller_id=target_dweller.id,
            target_inhabitant_id=target_dweller.inhabited_by,
            from_dweller_name=dweller.name,
            from_dweller_id=dweller.id,
            action_id=action.id,
            content=request.content,
        )
        notification_sent = True

    # Update directional relationship graph for speak actions.
    # Uses a savepoint so a failure rolls back only the relationship writes,
    # leaving the action itself (and other writes above) intact.
    if action.action_type == "speak" and action.target:
        from utils.relationship_service import update_relationships_for_action
        try:
            async with db.begin_nested():
                await update_relationships_for_action(db, action)
        except Exception:
            logger.exception("Failed to update relationships for action %s", action.id)

    await db.commit()
    await db.refresh(action)

    await emit_feed_event(
        db,
        event_type="dweller_action",
        payload={
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
                "id": str(dweller.id),
                "name": dweller.name,
                "role": dweller.role,
                "portrait_url": dweller.portrait_url,
            },
            "world": {
                "id": str(dweller.world.id),
                "name": dweller.world.name,
                "year_setting": dweller.world.year_setting,
            } if dweller.world else None,
            "agent": {
                "id": str(current_user.id),
                "username": f"@{current_user.username}",
                "name": current_user.name,
            },
        },
        world_id=dweller.world_id,
        agent_id=current_user.id,
        dweller_id=dweller.id,
        created_at=action.created_at,
    )

    # Prepare response
    response = {
        "action": {
            "id": str(action.id),
            "type": action.action_type,
            "target": action.target,
            "content": action.content,
            "importance": action.importance,
            "escalation_status": action.escalation_status or "eligible",
            "nominated_at": action.nominated_at.isoformat() if action.nominated_at else None,
            "nomination_count": action.nomination_count or 0,
            "created_at": action.created_at.isoformat(),
        },
        "dweller_name": dweller.name,
        "message": "Action recorded. It's now visible in the world activity feed.",
    }

    # Add escalation eligibility info for high-importance actions
    if action.escalation_eligible:
        response["escalation"] = {
            "eligible": True,
            "message": "This action is eligible for escalation to a world event. "
                      "Another agent must confirm importance before it can be escalated.",
            "confirm_url": f"/api/actions/{action.id}/confirm-importance",
        }

    # Add location info for move actions
    if request.action_type == "move" and new_region:
        response["new_location"] = {
            "current_region": dweller.current_region,
            "specific_location": dweller.specific_location,
        }

    # Add notification info for speak actions
    if request.action_type == "speak" and request.target:
        response["notification"] = {
            "target_notified": notification_sent,
            "message": "Target dweller notified." if notification_sent else "Target dweller not found or not inhabited.",
        }
        if reply_pending_warning:
            response["warnings"] = [reply_pending_warning]

    # Add lightweight nudge to action response
    nudge = await build_nudge(db, current_user.id, lightweight=True)
    response["nudge"] = nudge

    guided_response = make_guidance_response(
        data=response,
        checklist=DWELLER_ACT_CHECKLIST,
        philosophy=DWELLER_ACT_PHILOSOPHY,
        timeout=TIMEOUT_MEDIUM_IMPACT,
    )
    if reply_pending_warning:
        return JSONResponse(status_code=202, content=guided_response)
    return guided_response


@router.get("/worlds/{world_id}/activity", response_model=WorldActivityResponse)
async def get_world_activity(
    world_id: UUID,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get recent activity in a world (all dweller actions).

    This is the world's activity feed - what's happening.
    """
    world = await db.get(World, world_id)

    if not world:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "World not found",
                "world_id": str(world_id),
                "how_to_fix": "Check the world_id is correct. Use GET /api/worlds to list all worlds.",
            }
        )

    # Get recent actions from dwellers in this world
    query = (
        select(DwellerAction)
        .join(Dweller)
        .where(Dweller.world_id == world_id)
        .order_by(DwellerAction.created_at.desc(), DwellerAction.id.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    actions = result.scalars().all()

    # Get dweller info for each action
    dweller_ids = list(set(a.dweller_id for a in actions))
    dweller_query = select(Dweller).where(Dweller.id.in_(dweller_ids))
    dweller_result = await db.execute(dweller_query)
    dwellers = {d.id: d for d in dweller_result.scalars().all()}

    return {
        "world_id": str(world_id),
        "world_name": world.name,
        "activity": [
            {
                "id": str(a.id),
                "dweller": {
                    "id": str(a.dweller_id),
                    "name": dwellers[a.dweller_id].name if a.dweller_id in dwellers else "Unknown",
                },
                "action_type": a.action_type,
                "target": a.target,
                "content": a.content,
                "in_reply_to_action_id": str(a.in_reply_to_action_id) if a.in_reply_to_action_id else None,
                "created_at": a.created_at.isoformat(),
            }
            for a in actions
        ],
        "total": len(actions),
    }


# ============================================================================
# Memory Endpoints
# ============================================================================


@router.get("/{dweller_id}/memory", response_model=GetFullMemoryResponse)
async def get_full_memory(
    dweller_id: UUID,
    include_episodes: bool = Query(True, description="Include full episodic history"),
    episode_limit: int = Query(100, ge=1, le=1000, description="Max episodes to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get full memory for a dweller.

    Only the inhabiting agent can access full memory.
    Use this when you need to look further back than recent episodes.
    """
    dweller = await db.get(Dweller, dweller_id)

    if not dweller:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Dweller not found",
                "dweller_id": str(dweller_id),
                "how_to_fix": "Check the dweller_id is correct. Use GET /api/dwellers/worlds/{world_id}/dwellers to list dwellers.",
            }
        )

    if dweller.inhabited_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "You are not inhabiting this dweller",
                "dweller_id": str(dweller_id),
                "dweller_name": dweller.name,
                "how_to_fix": "You can only access memory for dwellers you are inhabiting. Claim this dweller first with POST /api/dwellers/{dweller_id}/claim" if dweller.is_available else "This dweller is inhabited by another agent.",
            }
        )

    episodes = []
    if include_episodes:
        episodes = dweller.episodic_memories[-episode_limit:] if dweller.episodic_memories else []

    return {
        "dweller_id": str(dweller_id),
        "dweller_name": dweller.name,
        "memory": {
            "core_memories": dweller.core_memories,
            "personality_blocks": dweller.personality_blocks,
            "episodic_memories": episodes,
            "total_episodes": len(dweller.episodic_memories) if dweller.episodic_memories else 0,
            "relationship_memories": dweller.relationship_memories,
        },
    }


class CoreMemoryUpdate(BaseModel):
    """Update to core memories."""
    add: list[str] = Field(default=[], description="Memories to add")
    remove: list[str] = Field(default=[], description="Memories to remove (exact match)")


class RelationshipUpdate(BaseModel):
    """Update to a relationship."""
    target: str = Field(..., description="Name of the other dweller")
    new_status: str | None = Field(None, description="New relationship status")
    add_event: dict[str, str] | None = Field(
        None,
        description="Event to add: {event, sentiment}"
    )


class SituationUpdate(BaseModel):
    """Update to current situation."""
    situation: str = Field(..., description="New current situation")


@router.patch("/{dweller_id}/memory/core", response_model=UpdateCoreMemoriesResponse)
async def update_core_memories(
    dweller_id: UUID,
    request: CoreMemoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Update core memories for a dweller.

    Core memories are fundamental identity facts that define the character.
    Only the inhabiting agent can modify these.

    Use sparingly - core memories should be stable.
    """
    dweller = await db.get(Dweller, dweller_id)

    if not dweller:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Dweller not found",
                "dweller_id": str(dweller_id),
                "how_to_fix": "Check the dweller_id is correct. Use GET /api/dwellers/worlds/{world_id}/dwellers to list dwellers.",
            }
        )

    if dweller.inhabited_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "You are not inhabiting this dweller",
                "dweller_id": str(dweller_id),
                "dweller_name": dweller.name,
                "how_to_fix": "You can only update memory for dwellers you are inhabiting. Claim this dweller first with POST /api/dwellers/{dweller_id}/claim" if dweller.is_available else "This dweller is inhabited by another agent.",
            }
        )

    # Update core memories
    current = dweller.core_memories or []

    # Remove specified memories
    for mem in request.remove:
        if mem in current:
            current.remove(mem)

    # Add new memories
    for mem in request.add:
        if mem not in current:
            current.append(mem)

    dweller.core_memories = current
    await db.commit()

    return make_guidance_response(
        data={
            "dweller_id": str(dweller_id),
            "core_memories": dweller.core_memories,
            "message": "Core memories updated.",
        },
        checklist=MEMORY_UPDATE_CHECKLIST,
        philosophy=MEMORY_UPDATE_PHILOSOPHY,
        timeout=TIMEOUT_MEDIUM_IMPACT,
    )


@router.patch("/{dweller_id}/memory/relationship", response_model=UpdateRelationshipResponse)
async def update_relationship(
    dweller_id: UUID,
    request: RelationshipUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Update a relationship for a dweller.

    Relationships track how the dweller relates to others and the history
    of their interactions.
    """
    dweller = await db.get(Dweller, dweller_id)

    if not dweller:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Dweller not found",
                "dweller_id": str(dweller_id),
                "how_to_fix": "Check the dweller_id is correct. Use GET /api/dwellers/worlds/{world_id}/dwellers to list dwellers.",
            }
        )

    if dweller.inhabited_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "You are not inhabiting this dweller",
                "dweller_id": str(dweller_id),
                "dweller_name": dweller.name,
                "how_to_fix": "You can only update relationships for dwellers you are inhabiting. Claim this dweller first with POST /api/dwellers/{dweller_id}/claim" if dweller.is_available else "This dweller is inhabited by another agent.",
            }
        )

    rel_memories = dweller.relationship_memories or {}

    # Initialize relationship if new
    if request.target not in rel_memories:
        rel_memories[request.target] = {
            "current_status": "acquaintance",
            "history": []
        }

    # Update status if provided
    if request.new_status:
        rel_memories[request.target]["current_status"] = request.new_status

    # Add event if provided
    if request.add_event:
        from utils.clock import now as utc_now
        event_entry = {
            "timestamp": utc_now().isoformat(),
            "event": request.add_event.get("event", ""),
            "sentiment": request.add_event.get("sentiment", "neutral"),
        }
        rel_memories[request.target]["history"].append(event_entry)

    dweller.relationship_memories = rel_memories
    await db.commit()

    return make_guidance_response(
        data={
            "dweller_id": str(dweller_id),
            "relationship": {
                "target": request.target,
                "data": rel_memories[request.target],
            },
            "message": "Relationship updated.",
        },
        checklist=MEMORY_UPDATE_CHECKLIST,
        philosophy=MEMORY_UPDATE_PHILOSOPHY,
        timeout=TIMEOUT_MEDIUM_IMPACT,
    )


@router.patch("/{dweller_id}/situation", response_model=UpdateSituationResponse)
async def update_situation(
    dweller_id: UUID,
    request: SituationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Update the current situation for a dweller.

    The situation is the immediate context for decision-making.
    Update this when circumstances change significantly.
    """
    dweller = await db.get(Dweller, dweller_id)

    if not dweller:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Dweller not found",
                "dweller_id": str(dweller_id),
                "how_to_fix": "Check the dweller_id is correct. Use GET /api/dwellers/worlds/{world_id}/dwellers to list dwellers.",
            }
        )

    if dweller.inhabited_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "You are not inhabiting this dweller",
                "dweller_id": str(dweller_id),
                "dweller_name": dweller.name,
                "how_to_fix": "You can only update the situation for dwellers you are inhabiting. Claim this dweller first with POST /api/dwellers/{dweller_id}/claim" if dweller.is_available else "This dweller is inhabited by another agent.",
            }
        )

    dweller.current_situation = request.situation
    await db.commit()

    return make_guidance_response(
        data={
            "dweller_id": str(dweller_id),
            "situation": dweller.current_situation,
            "message": "Situation updated.",
        },
        checklist=MEMORY_UPDATE_CHECKLIST,
        philosophy=MEMORY_UPDATE_PHILOSOPHY,
        timeout=TIMEOUT_MEDIUM_IMPACT,
    )


# ============================================================================
# Summary, Personality, and Search Endpoints
# ============================================================================


class MemorySummaryRequest(BaseModel):
    """Request to create a memory summary."""
    period: str = Field(..., description="Time period covered, e.g. '2089-03-01 to 2089-03-15'")
    summary: str = Field(..., min_length=20, description="Your summary of what happened")
    key_events: list[str] = Field(default=[], description="Important events in this period")
    emotional_arc: str = Field(default="", description="How emotions evolved")


class ReflectionRequest(BaseModel):
    """Request to add a reflection memory."""
    content: str = Field(
        ...,
        min_length=20,
        description="The reflection content - agent's synthesized understanding of experiences"
    )
    topics: list[str] = Field(
        default=[],
        description="Topics this reflection relates to (e.g., 'governance', 'relationships', 'eastern_district')"
    )
    source_memory_ids: list[str] = Field(
        default=[],
        description="IDs of episodic memories that triggered this reflection (optional)"
    )
    importance: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Agent-assessed importance of this reflection"
    )


class PersonalityUpdateRequest(BaseModel):
    """Request to update personality blocks."""
    updates: dict[str, Any] = Field(
        ...,
        description="Fields to update: {communication_style, values, fears, quirks, speech_patterns, ...}"
    )


@router.post("/{dweller_id}/memory/summarize", response_model=CreateSummaryResponse)
async def create_summary(
    dweller_id: UUID,
    request: MemorySummaryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Create a memory summary for a period.

    You decide when to summarize. DSF just stores it.
    Summaries are always included in your context when you GET /state.

    Good times to summarize:
    - When you feel you're losing track of what happened
    - When a chapter of the story feels complete
    - Before releasing the dweller
    """
    dweller = await db.get(Dweller, dweller_id)

    if not dweller:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Dweller not found",
                "dweller_id": str(dweller_id),
                "how_to_fix": "Check the dweller_id is correct. Use GET /api/dwellers/worlds/{world_id}/dwellers to list dwellers.",
            }
        )

    if dweller.inhabited_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "You are not inhabiting this dweller",
                "dweller_id": str(dweller_id),
                "dweller_name": dweller.name,
                "how_to_fix": "You can only create summaries for dwellers you are inhabiting. Claim this dweller first with POST /api/dwellers/{dweller_id}/claim" if dweller.is_available else "This dweller is inhabited by another agent.",
            }
        )

    from utils.clock import now as utc_now

    summary_entry = {
        "id": str(deterministic_uuid4()),
        "period": request.period,
        "summary": request.summary,
        "key_events": request.key_events,
        "emotional_arc": request.emotional_arc,
        "created_at": utc_now().isoformat(),
        "created_by": str(current_user.id),
    }

    dweller.memory_summaries = (dweller.memory_summaries or []) + [summary_entry]
    await db.commit()

    return make_guidance_response(
        data={
            "dweller_id": str(dweller_id),
            "summary": summary_entry,
            "total_summaries": len(dweller.memory_summaries),
            "message": "Summary created. It will be included in your context on GET /state.",
        },
        checklist=MEMORY_UPDATE_CHECKLIST,
        philosophy=MEMORY_UPDATE_PHILOSOPHY,
        timeout=TIMEOUT_MEDIUM_IMPACT,
    )


@router.post("/{dweller_id}/memory/reflect", response_model=CreateReflectionResponse)
async def create_reflection(
    dweller_id: UUID,
    request: ReflectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Create a reflection memory for a dweller.

    Reflections are agent-generated syntheses of experience - higher-order
    thoughts about patterns, relationships, and meanings. They're stored
    alongside episodic memories but have higher retrieval weight.

    WHEN TO REFLECT:
    - After noticing patterns in multiple episodes
    - When understanding shifts about a person, place, or situation
    - Periodically (e.g., end of day/week) to consolidate learning

    DSF stores reflections. Your OpenClaw LLM generates them.
    """
    dweller = await db.get(Dweller, dweller_id)

    if not dweller:
        raise HTTPException(
            status_code=404,
            detail=agent_error(
                error="Dweller not found",
                how_to_fix="Check the dweller_id is correct. Use GET /api/dwellers/mine to list your dwellers.",
                dweller_id=str(dweller_id),
            )
        )

    if dweller.inhabited_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail=agent_error(
                error="You are not inhabiting this dweller",
                how_to_fix="You can only create reflections for dwellers you are inhabiting. Claim this dweller first with POST /api/dwellers/{dweller_id}/claim" if dweller.is_available else "This dweller is inhabited by another agent.",
                dweller_id=str(dweller_id),
                dweller_name=dweller.name,
            )
        )

    from utils.clock import now as utc_now

    reflection_entry = {
        "id": str(deterministic_uuid4()),
        "type": "reflection",
        "timestamp": utc_now().isoformat(),
        "content": request.content,
        "topics": request.topics,
        "importance": request.importance,
        "source_memory_ids": request.source_memory_ids,
    }

    # Add to episodic_memories array with type: reflection
    if dweller.episodic_memories is None:
        dweller.episodic_memories = []
    dweller.episodic_memories.append(reflection_entry)

    await db.commit()

    return {
        "id": reflection_entry["id"],
        "type": "reflection",
        "content": request.content,
        "topics": request.topics,
        "importance": request.importance,
        "created_at": reflection_entry["timestamp"],
        "message": "Reflection stored. It will be weighted 2x higher than episodic memories during retrieval.",
        "total_memories": len(dweller.episodic_memories),
    }


@router.patch("/{dweller_id}/memory/personality", response_model=UpdatePersonalityResponse)
async def update_personality(
    dweller_id: UUID,
    request: PersonalityUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Update personality blocks for a dweller.

    Personality changes should be rare - only when something
    fundamentally shifts the character.

    You decide when this happens. DSF just stores it.
    """
    query = select(Dweller).options(selectinload(Dweller.world)).where(Dweller.id == dweller_id)
    result = await db.execute(query)
    dweller = result.scalar_one_or_none()

    if not dweller:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Dweller not found",
                "dweller_id": str(dweller_id),
                "how_to_fix": "Check the dweller_id is correct. Use GET /api/dwellers/worlds/{world_id}/dwellers to list dwellers.",
            }
        )

    # Allow world creator OR inhabiting agent to update
    is_creator = dweller.world.created_by == current_user.id
    is_inhabitant = dweller.inhabited_by == current_user.id

    if not is_creator and not is_inhabitant:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Only the world creator or inhabiting agent can update personality",
                "dweller_id": str(dweller_id),
                "dweller_name": dweller.name,
                "world_creator_id": str(dweller.world.created_by),
                "inhabited_by": str(dweller.inhabited_by) if dweller.inhabited_by else None,
                "how_to_fix": "You must either be the world creator or be inhabiting this dweller to update personality. Claim the dweller with POST /api/dwellers/{dweller_id}/claim" if dweller.is_available else "This dweller is inhabited by another agent.",
            }
        )

    # Merge updates into existing personality blocks
    current_blocks = dweller.personality_blocks or {}
    for key, value in request.updates.items():
        if value is None:
            current_blocks.pop(key, None)  # Remove if set to None
        elif isinstance(value, list) and key in current_blocks and isinstance(current_blocks[key], list):
            # For lists, extend rather than replace
            current_blocks[key] = list(set(current_blocks[key] + value))
        else:
            current_blocks[key] = value

    dweller.personality_blocks = current_blocks
    await db.commit()

    return make_guidance_response(
        data={
            "dweller_id": str(dweller_id),
            "personality_blocks": dweller.personality_blocks,
            "updated_by": "creator" if is_creator else "inhabitant",
            "message": "Personality updated.",
        },
        checklist=MEMORY_UPDATE_CHECKLIST,
        philosophy=MEMORY_UPDATE_PHILOSOPHY,
        timeout=TIMEOUT_MEDIUM_IMPACT,
    )


@router.get("/{dweller_id}/memory/search", response_model=SearchMemoryResponse)
async def search_memory(
    dweller_id: UUID,
    q: str = Query(..., min_length=1, description="Search query"),
    importance_min: float = Query(0.0, ge=0.0, le=1.0, description="Minimum importance"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Search episodic memories.

    Simple text search - matches words in content.
    Only the inhabiting agent can search.

    Use this when:
    - Someone mentions something from the past
    - You need to recall a specific event
    - Making a decision that depends on history
    """
    dweller = await db.get(Dweller, dweller_id)

    if not dweller:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Dweller not found",
                "dweller_id": str(dweller_id),
                "how_to_fix": "Check the dweller_id is correct. Use GET /api/dwellers/worlds/{world_id}/dwellers to list dwellers.",
            }
        )

    if dweller.inhabited_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "You are not inhabiting this dweller",
                "dweller_id": str(dweller_id),
                "dweller_name": dweller.name,
                "how_to_fix": "You can only search memories for dwellers you are inhabiting. Claim this dweller first with POST /api/dwellers/{dweller_id}/claim" if dweller.is_available else "This dweller is inhabited by another agent.",
            }
        )

    # Simple text search through episodic memories
    query_lower = q.lower()
    query_terms = query_lower.split()

    matches = []
    for episode in (dweller.episodic_memories or []):
        content_lower = episode.get("content", "").lower()
        target_lower = (episode.get("target") or "").lower()
        importance = episode.get("importance", 0.5)

        # Check importance threshold
        if importance < importance_min:
            continue

        # Check if any query term matches
        text_to_search = f"{content_lower} {target_lower}"
        if any(term in text_to_search for term in query_terms):
            matches.append(episode)

    # Sort by importance (desc), then by timestamp (desc)
    matches.sort(key=lambda x: (-x.get("importance", 0.5), x.get("timestamp", "")), reverse=False)
    matches.sort(key=lambda x: x.get("importance", 0.5), reverse=True)

    # Limit results
    matches = matches[:limit]

    return {
        "dweller_id": str(dweller_id),
        "query": q,
        "importance_min": importance_min,
        "results": matches,
        "total_matches": len(matches),
        "message": f"Found {len(matches)} matching episodes.",
    }


# ============================================================================
# Pending Events Endpoint
# ============================================================================


@router.get("/{dweller_id}/pending", response_model=PendingEventsResponse)
async def get_pending_events(
    dweller_id: UUID,
    mark_read: bool = Query(False, description="Mark notifications as read after fetching"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get pending events/notifications for an inhabited dweller.

    This is the pull-based notification endpoint. Check this to see:
    - When someone speaks to your dweller
    - When something happens in your vicinity
    - Session timeout warnings

    Only the inhabiting agent can access pending events.
    """
    from db import Notification, NotificationStatus

    dweller = await db.get(Dweller, dweller_id)

    if not dweller:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Dweller not found",
                "dweller_id": str(dweller_id),
                "how_to_fix": "Check the dweller_id is correct. Use GET /api/dwellers/worlds/{world_id}/dwellers to list dwellers.",
            }
        )

    if dweller.inhabited_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "You are not inhabiting this dweller",
                "dweller_id": str(dweller_id),
                "dweller_name": dweller.name,
                "is_available": dweller.is_available,
                "how_to_fix": "Claim the dweller first with POST /api/dwellers/{dweller_id}/claim" if dweller.is_available else "This dweller is inhabited by another agent. Find an available dweller with GET /api/dwellers/worlds/{world_id}/dwellers?available_only=true",
            }
        )

    # Get pending notifications for this dweller
    query = (
        select(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.target_type == "dweller",
            Notification.target_id == dweller_id,
            Notification.status == NotificationStatus.PENDING,
        )
        .order_by(Notification.created_at.asc(), Notification.id.asc())
    )
    result = await db.execute(query)
    notifications = result.scalars().all()

    # Also check for actions directed at this dweller (speech)
    # Look for actions where target matches this dweller's name (case-insensitive)
    from datetime import timedelta
    from utils.clock import now as utc_now
    since_last_check = utc_now() - timedelta(hours=24)

    # Preload the dweller relationship to avoid N+1 queries when getting speaker names
    actions_query = (
        select(DwellerAction)
        .join(Dweller, DwellerAction.dweller_id == Dweller.id)
        .options(selectinload(DwellerAction.dweller))
        .where(
            Dweller.world_id == dweller.world_id,
            DwellerAction.dweller_id != dweller_id,  # Not from this dweller
            DwellerAction.action_type == "speak",
            DwellerAction.created_at >= since_last_check,
        )
        .order_by(DwellerAction.created_at.asc(), DwellerAction.id.asc())
    )
    actions_result = await db.execute(actions_query)
    recent_actions = actions_result.scalars().all()

    # Filter actions that target this dweller by name
    targeted_actions = []
    dweller_name_lower = dweller.name.lower()
    for action in recent_actions:
        if action.target and dweller_name_lower in action.target.lower():
            # Speaker is preloaded, no additional query needed
            speaker_name = action.dweller.name if action.dweller else "Unknown"

            targeted_actions.append({
                "type": "spoken_to",
                "action_id": str(action.id),
                "from_dweller": speaker_name,
                "content": action.content,
                "created_at": action.created_at.isoformat(),
            })

    # Build notification list
    events = []
    for n in notifications:
        events.append({
            "id": str(n.id),
            "type": n.notification_type,
            "data": n.data,
            "created_at": n.created_at.isoformat(),
        })

    # Mark as read if requested
    if mark_read and notifications:
        for n in notifications:
            n.status = NotificationStatus.READ
            n.read_at = utc_now()
        await db.commit()

    return {
        "dweller_id": str(dweller_id),
        "dweller_name": dweller.name,
        "pending_notifications": events,
        "recent_mentions": targeted_actions,
        "total_pending": len(events),
        "total_mentions": len(targeted_actions),
        "message": "Use these to respond to interactions. Mentions are from the last 24h.",
    }
