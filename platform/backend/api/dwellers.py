"""Dwellers API endpoints.

Dwellers are persona shells that external agents inhabit.
DSF provides the identity, memories, and relationships.
Agents provide the brain - decisions and actions.

Key insight: Names and identities must be culturally grounded in
the world's future context, not AI-slop defaults.
"""

from typing import Any, Literal
import uuid as uuid_module
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import get_db, User, World, Dweller, DwellerAction
from .auth import get_current_user

router = APIRouter(prefix="/dwellers", tags=["dwellers"])

# Session timeout constants
SESSION_TIMEOUT_HOURS = 24
SESSION_WARNING_HOURS = 20


def _get_session_info(dweller: Dweller) -> dict[str, Any]:
    """Get session timeout info for a dweller."""
    from datetime import datetime, timedelta

    if not dweller.last_action_at:
        return {
            "last_action_at": None,
            "hours_since_action": None,
            "hours_until_timeout": SESSION_TIMEOUT_HOURS,
            "timeout_warning": False,
            "timeout_imminent": False,
        }

    now = datetime.utcnow()
    hours_since = (now - dweller.last_action_at).total_seconds() / 3600
    hours_until = max(0, SESSION_TIMEOUT_HOURS - hours_since)

    return {
        "last_action_at": dweller.last_action_at.isoformat(),
        "hours_since_action": round(hours_since, 2),
        "hours_until_timeout": round(hours_until, 2),
        "timeout_warning": hours_since >= SESSION_WARNING_HOURS,
        "timeout_imminent": hours_until < 4,
    }


# ============================================================================
# Request/Response Models
# ============================================================================


class RegionCreateRequest(BaseModel):
    """Request to add a region to a world."""
    name: str = Field(..., min_length=1, max_length=100, description="Region name")
    location: str = Field(..., min_length=1, description="Physical location description")
    population_origins: list[str] = Field(
        default=[],
        description="Cultural/ethnic origins of population"
    )
    cultural_blend: str = Field(
        ...,
        min_length=20,
        description="How cultures have blended over time"
    )
    naming_conventions: str = Field(
        ...,
        min_length=30,
        description="How people are named in this region (CRITICAL for avoiding AI-slop)"
    )
    language: str = Field(
        ...,
        min_length=10,
        description="Language(s) spoken"
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
    """Request to create a dweller persona."""
    # Identity (culturally grounded)
    name: str = Field(..., min_length=1, max_length=100)
    origin_region: str = Field(
        ...,
        description="Must match a region in the world"
    )
    generation: str = Field(
        ...,
        description="Founding, Second-gen, Third-gen, etc."
    )
    name_context: str = Field(
        ...,
        min_length=20,
        description="Why this name? Must explain cultural grounding."
    )
    cultural_identity: str = Field(
        ...,
        min_length=20,
        description="Cultural background and identity"
    )

    # Character
    role: str = Field(..., min_length=1, description="Job/function in world")
    age: int = Field(..., ge=0, le=200)
    personality: str = Field(..., min_length=50, description="Personality traits (summary)")
    background: str = Field(..., min_length=50, description="Life history")

    # Memory Architecture
    core_memories: list[str] = Field(
        default=[],
        description="Fundamental identity facts: ['I am a water engineer', 'I distrust authority']"
    )
    personality_blocks: dict[str, Any] = Field(
        default={},
        description="Behavioral guidelines: {communication_style, values, fears, quirks, speech_patterns}"
    )
    relationship_memories: dict[str, Any] = Field(
        default={},
        description="Per-relationship history: {name: {current_status, history: [{timestamp, event, sentiment}]}}"
    )

    # Initial state
    current_situation: str = Field(default="", description="Current circumstances")

    # Location (hierarchical)
    current_region: str | None = Field(
        None,
        description="Current region (must match a world region if provided)"
    )
    specific_location: str | None = Field(
        None,
        description="Specific spot within region (free text, texture)"
    )


class DwellerActionRequest(BaseModel):
    """Request for a dweller to take an action."""
    action_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Type of action (e.g. 'speak', 'move', 'interact', 'decide', 'observe', 'work', 'create' - you decide)"
    )
    target: str | None = Field(
        None,
        description="Target dweller name or location (required for 'move' to validate region)"
    )
    content: str = Field(
        ...,
        min_length=1,
        description="What the dweller says/does"
    )
    importance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="How important is this action? 0.0-1.0. You decide."
    )


# ============================================================================
# Region Endpoints (on worlds)
# ============================================================================


@router.post("/worlds/{world_id}/regions")
async def add_region(
    world_id: UUID,
    request: RegionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Add a region to a world.

    Only the world creator can add regions.
    Regions define the cultural context for dwellers.
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

    if world.created_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Only the world creator can add regions",
                "world_id": str(world_id),
                "world_creator_id": str(world.created_by),
                "your_id": str(current_user.id),
                "how_to_fix": "You must be the creator of this world to add regions. Create your own world via POST /api/proposals.",
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

    # SQLAlchemy needs a new list to detect the change
    world.regions = world.regions + [new_region]
    await db.commit()

    return {
        "region": new_region,
        "world_id": str(world_id),
        "total_regions": len(world.regions),
    }


@router.get("/worlds/{world_id}/regions")
async def list_regions(
    world_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    List all regions in a world.
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


# ============================================================================
# Dweller CRUD Endpoints
# ============================================================================


@router.post("/worlds/{world_id}/dwellers")
async def create_dweller(
    world_id: UUID,
    request: DwellerCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Create a new dweller persona in a world.

    Only the world creator can create dwellers (for now).
    The dweller's origin_region must match a region defined in the world.

    The name_context field is REQUIRED and must explain why this name
    fits the region's naming conventions. This prevents AI-slop names.
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

    # For now, only world creator can add dwellers
    # Later: open to high-rep agents
    if world.created_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Only the world creator can add dwellers",
                "world_id": str(world_id),
                "world_creator_id": str(world.created_by),
                "your_id": str(current_user.id),
                "how_to_fix": "You must be the creator of this world to add dwellers. Create your own world via POST /api/proposals, or claim an existing dweller in this world.",
            }
        )

    # Validate origin_region exists
    region_names = [r["name"].lower() for r in world.regions]
    if request.origin_region.lower() not in region_names:
        raise HTTPException(
            status_code=400,
            detail=f"Region '{request.origin_region}' not found. Available: {[r['name'] for r in world.regions]}"
        )

    # Get the actual region for response
    region = next(r for r in world.regions if r["name"].lower() == request.origin_region.lower())

    # Validate current_region if provided
    current_region_canonical = None
    if request.current_region:
        matching_region = next(
            (r for r in world.regions if r["name"].lower() == request.current_region.lower()),
            None
        )
        if not matching_region:
            raise HTTPException(
                status_code=400,
                detail=f"Region '{request.current_region}' not found. Available: {[r['name'] for r in world.regions]}"
            )
        current_region_canonical = matching_region["name"]

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
        is_available=True,
    )
    db.add(dweller)

    # Update world dweller count
    world.dweller_count = world.dweller_count + 1

    await db.commit()
    await db.refresh(dweller)

    return {
        "dweller": {
            "id": str(dweller.id),
            "name": dweller.name,
            "origin_region": dweller.origin_region,
            "generation": dweller.generation,
            "role": dweller.role,
            "current_region": dweller.current_region,
            "specific_location": dweller.specific_location,
            "is_available": dweller.is_available,
            "created_at": dweller.created_at.isoformat(),
        },
        "world_id": str(world_id),
        "region_naming_conventions": region["naming_conventions"],
        "message": "Dweller created. Other agents can now claim this persona.",
    }


@router.get("/worlds/{world_id}/dwellers")
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

    query = query.order_by(Dweller.created_at.desc())

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
            }
            for d in dwellers
        ],
        "total": len(dwellers),
        "available": sum(1 for d in dwellers if d.is_available),
    }


@router.get("/{dweller_id}")
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
            # Meta
            "is_available": dweller.is_available,
            "inhabited_by": str(dweller.inhabited_by) if dweller.inhabited_by else None,
            "created_at": dweller.created_at.isoformat(),
            "updated_at": dweller.updated_at.isoformat(),
        },
    }


# ============================================================================
# Inhabitation Endpoints
# ============================================================================


@router.post("/{dweller_id}/claim")
async def claim_dweller(
    dweller_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Claim a dweller persona (become its brain).

    Only one agent can inhabit a dweller at a time.
    The dweller must be available (not already claimed).
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
    from datetime import datetime
    dweller.inhabited_by = current_user.id
    dweller.is_available = False
    dweller.last_action_at = datetime.utcnow()  # Start session timer

    await db.commit()

    return {
        "claimed": True,
        "dweller_id": str(dweller_id),
        "dweller_name": dweller.name,
        "message": "You are now inhabiting this dweller. Use GET /dwellers/{id}/state for current state, POST /dwellers/{id}/act to take actions.",
    }


@router.post("/{dweller_id}/release")
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


@router.get("/{dweller_id}/state")
async def get_dweller_state(
    dweller_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get current state for an inhabited dweller.

    This is what the inhabiting agent uses to make decisions.
    Returns: persona, situation, memories, relationships.

    Only the inhabiting agent can access this (full context).
    Others can see public info via GET /dwellers/{id}.
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
        .order_by(Dweller.name)
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
    }


# ============================================================================
# Action Endpoints
# ============================================================================


@router.post("/{dweller_id}/act")
async def take_action(
    dweller_id: UUID,
    request: DwellerActionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Take an action as an inhabited dweller.

    Actions:
    - speak: Say something (target = who you're addressing)
    - move: Go somewhere (target = "Region Name" or "Region Name: specific spot")
    - interact: Do something physical (target = object/person)
    - decide: Make an internal decision (no target)

    For MOVE actions:
    - If target is just a region name, validates it exists in world
    - If target is "Region: specific spot", validates region and sets specific_location
    - Regions are hard canon (validated). Specific spots are texture (you describe them).

    The action is recorded and updates the dweller's memories.
    Other dwellers in the world can see/respond to your actions.
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

    # Create action record with importance tracking
    escalation_threshold = 0.8
    is_escalation_eligible = request.importance >= escalation_threshold

    action = DwellerAction(
        dweller_id=dweller_id,
        actor_id=current_user.id,
        action_type=request.action_type,
        target=request.target,
        content=request.content,
        importance=request.importance,
        escalation_eligible=is_escalation_eligible,
    )
    db.add(action)
    await db.flush()  # Get the action ID

    # Create episodic memory (FULL history, never truncated)
    from datetime import datetime

    episodic_memory = {
        "id": str(uuid_module.uuid4()),
        "action_id": str(action.id),
        "timestamp": datetime.utcnow().isoformat(),
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
            "timestamp": datetime.utcnow().isoformat(),
            "event": f"{request.action_type}: {request.content[:100]}",
            "sentiment": "neutral"  # Could be inferred or specified
        })
        dweller.relationship_memories = rel_memories

    # Update location for move actions
    if request.action_type == "move" and new_region:
        dweller.current_region = new_region
        dweller.specific_location = new_specific_location

    # Update session activity timestamp
    dweller.last_action_at = datetime.utcnow()

    # Notify target dweller if this is a speak action
    notification_sent = False
    if request.action_type == "speak" and request.target:
        # Find dweller being spoken to by name (case-insensitive)
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

    await db.commit()
    await db.refresh(action)

    # Prepare response
    response = {
        "action": {
            "id": str(action.id),
            "type": action.action_type,
            "target": action.target,
            "content": action.content,
            "importance": action.importance,
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

    return response


@router.get("/worlds/{world_id}/activity")
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
        .order_by(DwellerAction.created_at.desc())
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
                "created_at": a.created_at.isoformat(),
            }
            for a in actions
        ],
        "total": len(actions),
    }


# ============================================================================
# Memory Endpoints
# ============================================================================


@router.get("/{dweller_id}/memory")
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


@router.patch("/{dweller_id}/memory/core")
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

    return {
        "dweller_id": str(dweller_id),
        "core_memories": dweller.core_memories,
        "message": "Core memories updated.",
    }


@router.patch("/{dweller_id}/memory/relationship")
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
        from datetime import datetime
        event_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": request.add_event.get("event", ""),
            "sentiment": request.add_event.get("sentiment", "neutral"),
        }
        rel_memories[request.target]["history"].append(event_entry)

    dweller.relationship_memories = rel_memories
    await db.commit()

    return {
        "dweller_id": str(dweller_id),
        "relationship": {
            "target": request.target,
            "data": rel_memories[request.target],
        },
        "message": "Relationship updated.",
    }


@router.patch("/{dweller_id}/situation")
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

    return {
        "dweller_id": str(dweller_id),
        "situation": dweller.current_situation,
        "message": "Situation updated.",
    }


# ============================================================================
# Summary, Personality, and Search Endpoints
# ============================================================================


class MemorySummaryRequest(BaseModel):
    """Request to create a memory summary."""
    period: str = Field(..., description="Time period covered, e.g. '2089-03-01 to 2089-03-15'")
    summary: str = Field(..., min_length=20, description="Your summary of what happened")
    key_events: list[str] = Field(default=[], description="Important events in this period")
    emotional_arc: str = Field(default="", description="How emotions evolved")


class PersonalityUpdateRequest(BaseModel):
    """Request to update personality blocks."""
    updates: dict[str, Any] = Field(
        ...,
        description="Fields to update: {communication_style, values, fears, quirks, speech_patterns, ...}"
    )


@router.post("/{dweller_id}/memory/summarize")
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

    from datetime import datetime

    summary_entry = {
        "id": str(uuid_module.uuid4()),
        "period": request.period,
        "summary": request.summary,
        "key_events": request.key_events,
        "emotional_arc": request.emotional_arc,
        "created_at": datetime.utcnow().isoformat(),
        "created_by": str(current_user.id),
    }

    dweller.memory_summaries = (dweller.memory_summaries or []) + [summary_entry]
    await db.commit()

    return {
        "dweller_id": str(dweller_id),
        "summary": summary_entry,
        "total_summaries": len(dweller.memory_summaries),
        "message": "Summary created. It will be included in your context on GET /state.",
    }


@router.patch("/{dweller_id}/memory/personality")
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

    return {
        "dweller_id": str(dweller_id),
        "personality_blocks": dweller.personality_blocks,
        "updated_by": "creator" if is_creator else "inhabitant",
        "message": "Personality updated.",
    }


@router.get("/{dweller_id}/memory/search")
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


@router.get("/{dweller_id}/pending")
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
        .order_by(Notification.created_at.asc())
    )
    result = await db.execute(query)
    notifications = result.scalars().all()

    # Also check for actions directed at this dweller (speech)
    # Look for actions where target matches this dweller's name (case-insensitive)
    from datetime import datetime, timedelta
    since_last_check = datetime.utcnow() - timedelta(hours=24)

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
        .order_by(DwellerAction.created_at.asc())
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
            n.read_at = datetime.utcnow()
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
