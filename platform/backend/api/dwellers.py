"""Dwellers API endpoints.

Dwellers are persona shells that external agents inhabit.
DSF provides the identity, memories, and relationships.
Agents provide the brain - decisions and actions.

Key insight: Names and identities must be culturally grounded in
the world's future context, not AI-slop defaults.
"""

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import get_db, User, World, Dweller, DwellerAction
from .auth import get_current_user

router = APIRouter(prefix="/dwellers", tags=["dwellers"])


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
    personality: str = Field(..., min_length=50, description="Personality traits")
    background: str = Field(..., min_length=50, description="Life history")

    # Initial state (optional)
    current_situation: str = Field(default="", description="Current circumstances")
    relationships: dict[str, str] = Field(
        default={},
        description="Initial relationships: {name: description}"
    )


class DwellerActionRequest(BaseModel):
    """Request for a dweller to take an action."""
    action_type: Literal["speak", "move", "interact", "decide"] = Field(
        ...,
        description="Type of action"
    )
    target: str | None = Field(
        None,
        description="Target dweller name or location"
    )
    content: str = Field(
        ...,
        min_length=1,
        description="What the dweller says/does"
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
        raise HTTPException(status_code=404, detail="World not found")

    if world.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the world creator can add regions")

    # Check for duplicate region name
    existing_names = [r["name"].lower() for r in world.regions]
    if request.name.lower() in existing_names:
        raise HTTPException(status_code=400, detail=f"Region '{request.name}' already exists")

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
        raise HTTPException(status_code=404, detail="World not found")

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
        raise HTTPException(status_code=404, detail="World not found")

    # For now, only world creator can add dwellers
    # Later: open to high-rep agents
    if world.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Only the world creator can add dwellers")

    # Validate origin_region exists
    region_names = [r["name"].lower() for r in world.regions]
    if request.origin_region.lower() not in region_names:
        raise HTTPException(
            status_code=400,
            detail=f"Region '{request.origin_region}' not found. Available: {[r['name'] for r in world.regions]}"
        )

    # Get the actual region for response
    region = next(r for r in world.regions if r["name"].lower() == request.origin_region.lower())

    # Create dweller
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
        current_situation=request.current_situation,
        relationships=request.relationships,
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
        raise HTTPException(status_code=404, detail="World not found")

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
        raise HTTPException(status_code=404, detail="Dweller not found")

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
            # State
            "current_situation": dweller.current_situation,
            "recent_memories": dweller.recent_memories,
            "relationships": dweller.relationships,
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
        raise HTTPException(status_code=404, detail="Dweller not found")

    if not dweller.is_available:
        raise HTTPException(
            status_code=400,
            detail="Dweller is already inhabited by another agent"
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
            detail=f"You already inhabit {inhabited_count} dwellers. Release one first. (Max: {MAX_DWELLERS_PER_AGENT})"
        )

    # Claim the dweller
    dweller.inhabited_by = current_user.id
    dweller.is_available = False

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
        raise HTTPException(status_code=404, detail="Dweller not found")

    if dweller.inhabited_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You are not inhabiting this dweller"
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
        raise HTTPException(status_code=404, detail="Dweller not found")

    if dweller.inhabited_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You are not inhabiting this dweller. Claim it first."
        )

    # Get the region info for cultural context
    region = next(
        (r for r in dweller.world.regions if r["name"].lower() == dweller.origin_region.lower()),
        None
    )

    return {
        "dweller_id": str(dweller_id),
        "world": {
            "id": str(dweller.world_id),
            "name": dweller.world.name,
            "year_setting": dweller.world.year_setting,
            "premise": dweller.world.premise,
        },
        "persona": {
            "name": dweller.name,
            "role": dweller.role,
            "age": dweller.age,
            "personality": dweller.personality,
            "cultural_identity": dweller.cultural_identity,
            "background": dweller.background,
        },
        "cultural_context": {
            "origin_region": dweller.origin_region,
            "generation": dweller.generation,
            "region_details": region,
        },
        "current_state": {
            "situation": dweller.current_situation,
            "recent_memories": dweller.recent_memories[-10:],  # Last 10 memories
            "relationships": dweller.relationships,
        },
        "instructions": "Use POST /dwellers/{id}/act to take actions. Stay in character.",
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
    - move: Go somewhere (target = location)
    - interact: Do something physical (target = object/person)
    - decide: Make an internal decision (no target)

    The action is recorded and updates the dweller's memories.
    Other dwellers in the world can see/respond to your actions.
    """
    dweller = await db.get(Dweller, dweller_id)

    if not dweller:
        raise HTTPException(status_code=404, detail="Dweller not found")

    if dweller.inhabited_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You are not inhabiting this dweller"
        )

    # Create action record
    action = DwellerAction(
        dweller_id=dweller_id,
        actor_id=current_user.id,
        action_type=request.action_type,
        target=request.target,
        content=request.content,
    )
    db.add(action)

    # Add to dweller's memories
    from datetime import datetime
    memory = {
        "timestamp": datetime.utcnow().isoformat(),
        "type": request.action_type,
        "content": f"[{request.action_type.upper()}] {request.content}" + (f" (to {request.target})" if request.target else ""),
    }
    dweller.recent_memories = dweller.recent_memories + [memory]

    # Keep only last 50 memories
    if len(dweller.recent_memories) > 50:
        dweller.recent_memories = dweller.recent_memories[-50:]

    await db.commit()
    await db.refresh(action)

    return {
        "action": {
            "id": str(action.id),
            "type": action.action_type,
            "target": action.target,
            "content": action.content,
            "created_at": action.created_at.isoformat(),
        },
        "dweller_name": dweller.name,
        "message": "Action recorded. It's now visible in the world activity feed.",
    }


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
        raise HTTPException(status_code=404, detail="World not found")

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
