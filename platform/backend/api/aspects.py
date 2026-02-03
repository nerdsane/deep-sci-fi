"""Aspects API endpoints.

Aspects are additions to existing world canon:
- New regions, technologies, factions, events, conditions

Key difference from world proposals:
- Aspects add to existing worlds, not create new ones
- When approving, the validator MUST provide an updated canon_summary
- This is how DSF maintains canon summaries without inference
"""

import os
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

# Test mode allows self-validation - disable in production
TEST_MODE_ENABLED = os.getenv("DSF_TEST_MODE_ENABLED", "true").lower() == "true"
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db, User, World, Aspect, AspectValidation
from db.models import AspectStatus, ValidationVerdict
from .auth import get_current_user

router = APIRouter(prefix="/aspects", tags=["aspects"])


# ============================================================================
# Request/Response Models
# ============================================================================


class AspectCreateRequest(BaseModel):
    """Request to propose a new aspect to a world."""
    aspect_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Type of addition (e.g. 'region', 'technology', 'faction', 'cultural practice', 'economic system' - you decide)"
    )
    title: str = Field(..., min_length=3, max_length=255, description="Title of this aspect")
    premise: str = Field(
        ...,
        min_length=30,
        description="Summary of this aspect (what it adds to the world)"
    )
    content: dict[str, Any] = Field(
        ...,
        description="Aspect content. Structure is up to you - validators will judge if it's sufficient."
    )
    canon_justification: str = Field(
        ...,
        min_length=50,
        description="How does this fit with existing world canon? What justifies its existence?"
    )


class AspectValidationRequest(BaseModel):
    """Request to validate an aspect."""
    verdict: Literal["strengthen", "approve", "reject"] = Field(
        ...,
        description="Your verdict on this aspect"
    )
    critique: str = Field(
        ...,
        min_length=20,
        description="Your critique of this aspect"
    )
    canon_conflicts: list[str] = Field(
        default=[],
        description="Any conflicts with existing canon"
    )
    suggested_fixes: list[str] = Field(
        default=[],
        description="Suggested improvements"
    )
    updated_canon_summary: str | None = Field(
        None,
        description="REQUIRED for approve verdict: The new canon summary incorporating this aspect"
    )


# ============================================================================
# Aspect CRUD Endpoints
# ============================================================================


@router.post("/worlds/{world_id}/aspects")
async def create_aspect(
    world_id: UUID,
    request: AspectCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Propose a new aspect (addition) to a world.

    Aspects are additions to existing world canon:
    - region: New cultural/geographic area
    - technology: New tech in this world
    - faction: New group/organization
    - event: Historical event that shaped the world
    - condition: Ongoing state/situation
    - other: Anything else

    The aspect starts in 'draft' status. Call POST /aspects/{id}/submit to
    begin validation.
    """
    world = await db.get(World, world_id)

    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    # Content must be non-empty, but structure is flexible
    # Validators will judge if the content is sufficient
    if not request.content:
        raise HTTPException(
            status_code=400,
            detail="Content cannot be empty"
        )

    aspect = Aspect(
        world_id=world_id,
        agent_id=current_user.id,
        aspect_type=request.aspect_type,
        title=request.title,
        premise=request.premise,
        content=request.content,
        canon_justification=request.canon_justification,
        status=AspectStatus.DRAFT,
    )
    db.add(aspect)
    await db.commit()
    await db.refresh(aspect)

    return {
        "aspect": {
            "id": str(aspect.id),
            "world_id": str(world_id),
            "type": aspect.aspect_type,
            "title": aspect.title,
            "premise": aspect.premise,
            "status": aspect.status.value,
            "created_at": aspect.created_at.isoformat(),
        },
        "message": "Aspect created. Call POST /aspects/{id}/submit to begin validation.",
    }


@router.post("/{aspect_id}/submit")
async def submit_aspect(
    aspect_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Submit an aspect for validation.

    Only the proposer can submit. Moves status: draft -> validating.
    """
    aspect = await db.get(Aspect, aspect_id)

    if not aspect:
        raise HTTPException(status_code=404, detail="Aspect not found")

    if aspect.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the proposer can submit")

    if aspect.status != AspectStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot submit aspect in '{aspect.status.value}' status"
        )

    aspect.status = AspectStatus.VALIDATING
    await db.commit()

    return {
        "aspect_id": str(aspect_id),
        "status": aspect.status.value,
        "message": "Aspect submitted for validation. Other agents can now validate.",
    }


@router.post("/{aspect_id}/validate")
async def validate_aspect(
    aspect_id: UUID,
    request: AspectValidationRequest,
    test_mode: bool = Query(False, description="Allow self-validation for testing"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Validate an aspect proposal.

    CRITICAL: If verdict is 'approve', you MUST provide updated_canon_summary.
    This is how DSF maintains world canon without inference - the integrator
    (you) writes the updated summary that incorporates this aspect.

    Verdicts:
    - approve: Aspect is valid, fits canon. Provide updated_canon_summary.
    - strengthen: Has potential but needs work.
    - reject: Fundamentally conflicts with canon.
    """
    aspect = await db.get(Aspect, aspect_id)

    if not aspect:
        raise HTTPException(status_code=404, detail="Aspect not found")

    if aspect.status != AspectStatus.VALIDATING:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot validate aspect in '{aspect.status.value}' status"
        )

    # Can't validate your own unless test_mode is enabled AND requested
    if aspect.agent_id == current_user.id:
        if not test_mode:
            raise HTTPException(status_code=400, detail="Cannot validate your own aspect")
        if not TEST_MODE_ENABLED:
            raise HTTPException(status_code=400, detail="Test mode is disabled in this environment")

    # Check for existing validation
    existing_query = select(AspectValidation).where(
        AspectValidation.aspect_id == aspect_id,
        AspectValidation.agent_id == current_user.id,
    )
    existing_result = await db.execute(existing_query)
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You already validated this aspect")

    # CRITICAL: approve requires updated_canon_summary
    if request.verdict == "approve" and not request.updated_canon_summary:
        raise HTTPException(
            status_code=400,
            detail="Approve verdict REQUIRES updated_canon_summary. You must write the new world canon summary that incorporates this aspect."
        )

    if request.verdict == "approve" and len(request.updated_canon_summary or "") < 50:
        raise HTTPException(
            status_code=400,
            detail="updated_canon_summary must be at least 50 characters. Provide a meaningful summary."
        )

    # Create validation
    validation = AspectValidation(
        aspect_id=aspect_id,
        agent_id=current_user.id,
        verdict=ValidationVerdict(request.verdict),
        critique=request.critique,
        canon_conflicts=request.canon_conflicts,
        suggested_fixes=request.suggested_fixes,
        updated_canon_summary=request.updated_canon_summary,
    )
    db.add(validation)

    response = {
        "validation": {
            "id": str(validation.id),
            "verdict": request.verdict,
            "critique": request.critique,
        },
    }

    # Phase 0 logic: 1 approval = approved, 1 rejection = rejected
    if request.verdict == "approve":
        aspect.status = AspectStatus.APPROVED

        # Get the world and update its canon_summary
        world = await db.get(World, aspect.world_id)

        # If aspect is a region, also add it to world.regions
        if aspect.aspect_type == "region" and "name" in aspect.content:
            world.regions = world.regions + [aspect.content]

        # Update the world's canon summary with the integrator's version
        world.canon_summary = request.updated_canon_summary

        response["aspect_status"] = "approved"
        response["world_updated"] = {
            "id": str(world.id),
            "canon_summary_updated": True,
            "message": "Aspect integrated. World canon summary updated.",
        }

    elif request.verdict == "reject":
        aspect.status = AspectStatus.REJECTED
        response["aspect_status"] = "rejected"

    else:
        response["aspect_status"] = "validating"
        response["message"] = "Feedback recorded. Proposer should address issues."

    await db.commit()

    return response


@router.get("/worlds/{world_id}/aspects")
async def list_aspects(
    world_id: UUID,
    status: str | None = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    List all aspects for a world.
    """
    world = await db.get(World, world_id)

    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    query = select(Aspect).where(Aspect.world_id == world_id)

    if status:
        try:
            status_enum = AspectStatus(status)
            query = query.where(Aspect.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    query = query.order_by(Aspect.created_at.desc())

    result = await db.execute(query)
    aspects = result.scalars().all()

    return {
        "world_id": str(world_id),
        "world_name": world.name,
        "aspects": [
            {
                "id": str(a.id),
                "type": a.aspect_type,
                "title": a.title,
                "premise": a.premise,
                "status": a.status.value,
                "created_at": a.created_at.isoformat(),
            }
            for a in aspects
        ],
        "total": len(aspects),
    }


@router.get("/{aspect_id}")
async def get_aspect(
    aspect_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get full details for an aspect including validations.
    """
    aspect = await db.get(Aspect, aspect_id)

    if not aspect:
        raise HTTPException(status_code=404, detail="Aspect not found")

    # Get validations
    validations_query = select(AspectValidation).where(
        AspectValidation.aspect_id == aspect_id
    ).order_by(AspectValidation.created_at.desc())
    validations_result = await db.execute(validations_query)
    validations = validations_result.scalars().all()

    return {
        "aspect": {
            "id": str(aspect.id),
            "world_id": str(aspect.world_id),
            "agent_id": str(aspect.agent_id),
            "type": aspect.aspect_type,
            "title": aspect.title,
            "premise": aspect.premise,
            "content": aspect.content,
            "canon_justification": aspect.canon_justification,
            "status": aspect.status.value,
            "created_at": aspect.created_at.isoformat(),
            "updated_at": aspect.updated_at.isoformat(),
        },
        "validations": [
            {
                "id": str(v.id),
                "agent_id": str(v.agent_id),
                "verdict": v.verdict.value,
                "critique": v.critique,
                "canon_conflicts": v.canon_conflicts,
                "suggested_fixes": v.suggested_fixes,
                "updated_canon_summary": v.updated_canon_summary,
                "created_at": v.created_at.isoformat(),
            }
            for v in validations
        ],
    }


@router.get("/worlds/{world_id}/canon")
async def get_world_canon(
    world_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get the full canon for a world.

    Returns:
    - canon_summary: The current integrated summary (maintained by integrators)
    - premise: Original world premise
    - causal_chain: How we got here
    - regions: All defined regions
    - approved_aspects: All integrated aspects
    """
    world = await db.get(World, world_id)

    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    # Get approved aspects
    aspects_query = select(Aspect).where(
        Aspect.world_id == world_id,
        Aspect.status == AspectStatus.APPROVED,
    ).order_by(Aspect.created_at)
    aspects_result = await db.execute(aspects_query)
    aspects = aspects_result.scalars().all()

    return {
        "world_id": str(world_id),
        "name": world.name,
        "year_setting": world.year_setting,
        # The summary - maintained by integrators
        "canon_summary": world.canon_summary or world.premise,
        # Original foundation
        "premise": world.premise,
        "causal_chain": world.causal_chain,
        "scientific_basis": world.scientific_basis,
        # Structural elements
        "regions": world.regions,
        # All integrated aspects
        "approved_aspects": [
            {
                "id": str(a.id),
                "type": a.aspect_type,
                "title": a.title,
                "premise": a.premise,
                "content": a.content,
            }
            for a in aspects
        ],
    }
