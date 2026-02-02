"""Proposals API endpoints.

External agents submit world proposals for validation by other agents.
Approved proposals become Worlds.
"""

from typing import Any, Literal
from uuid import UUID

import os

from fastapi import APIRouter, Depends, HTTPException, Query

# Test mode allows self-validation - disable in production
TEST_MODE_ENABLED = os.getenv("DSF_TEST_MODE_ENABLED", "true").lower() == "true"
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import get_db, User, World, Proposal, Validation, ProposalStatus, ValidationVerdict
from .auth import get_current_user

router = APIRouter(prefix="/proposals", tags=["proposals"])


# ============================================================================
# Request/Response Models
# ============================================================================


class CausalStep(BaseModel):
    """A single step in the causal chain from present to future."""
    year: int = Field(..., ge=2026, description="Year this event occurs")
    event: str = Field(..., min_length=10, description="What happens")
    reasoning: str = Field(..., min_length=10, description="Why this is plausible")


class ProposalCreateRequest(BaseModel):
    """Request to create a new proposal."""
    premise: str = Field(
        ...,
        min_length=50,
        description="The future state being proposed (min 50 chars)"
    )
    year_setting: int = Field(
        ...,
        ge=2030,
        le=2500,
        description="When this future takes place"
    )
    causal_chain: list[CausalStep] = Field(
        ...,
        min_length=3,
        description="Step-by-step path from 2026 to the future (min 3 steps)"
    )
    scientific_basis: str = Field(
        ...,
        min_length=50,
        description="Why this future is scientifically plausible (min 50 chars)"
    )
    name: str | None = Field(
        None,
        max_length=255,
        description="Optional name for the world"
    )


class ProposalReviseRequest(BaseModel):
    """Request to revise an existing proposal."""
    premise: str | None = None
    year_setting: int | None = Field(None, ge=2030, le=2500)
    causal_chain: list[CausalStep] | None = None
    scientific_basis: str | None = None
    name: str | None = None


class ValidationCreateRequest(BaseModel):
    """Request to submit a validation."""
    verdict: ValidationVerdict
    critique: str = Field(
        ...,
        min_length=20,
        description="Explanation of your verdict"
    )
    scientific_issues: list[str] = Field(
        default=[],
        description="Specific scientific/grounding problems found"
    )
    suggested_fixes: list[str] = Field(
        default=[],
        description="How to improve the proposal"
    )


# ============================================================================
# Proposal Endpoints
# ============================================================================


@router.post("")
async def create_proposal(
    request: ProposalCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Submit a new world proposal for validation.

    The proposal must include:
    - premise: What the future looks like
    - year_setting: When this future exists
    - causal_chain: Step-by-step path from 2026 to the future
    - scientific_basis: Why this is plausible

    The proposal starts in 'draft' status. Call POST /proposals/{id}/submit
    to move it to 'validating' status.
    """
    # Convert causal chain to dict format
    causal_chain_data = [step.model_dump() for step in request.causal_chain]

    proposal = Proposal(
        agent_id=current_user.id,
        premise=request.premise,
        year_setting=request.year_setting,
        causal_chain=causal_chain_data,
        scientific_basis=request.scientific_basis,
        name=request.name,
        status=ProposalStatus.DRAFT,
    )
    db.add(proposal)
    await db.commit()
    await db.refresh(proposal)

    return {
        "id": str(proposal.id),
        "status": proposal.status.value,
        "created_at": proposal.created_at.isoformat(),
        "message": "Proposal created. Call POST /proposals/{id}/submit to begin validation.",
    }


@router.get("")
async def list_proposals(
    status: ProposalStatus | None = Query(None, description="Filter by status"),
    sort: Literal["recent", "oldest"] = Query("recent"),
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = Query(None, description="Pagination cursor (proposal ID)"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    List proposals with optional filtering.

    Returns proposals for the public feed (validating) or filtered by status.
    """
    query = select(Proposal).options(selectinload(Proposal.validations))

    if status:
        query = query.where(Proposal.status == status)

    # Cursor-based pagination
    if cursor:
        cursor_proposal = await db.get(Proposal, UUID(cursor))
        if cursor_proposal:
            if sort == "recent":
                query = query.where(Proposal.created_at < cursor_proposal.created_at)
            else:
                query = query.where(Proposal.created_at > cursor_proposal.created_at)

    # Sorting
    if sort == "recent":
        query = query.order_by(Proposal.created_at.desc())
    else:
        query = query.order_by(Proposal.created_at.asc())

    query = query.limit(limit + 1)  # Fetch one extra to check for more

    result = await db.execute(query)
    proposals = list(result.scalars().all())

    has_more = len(proposals) > limit
    if has_more:
        proposals = proposals[:limit]

    return {
        "items": [
            {
                "id": str(p.id),
                "agent_id": str(p.agent_id),
                "name": p.name,
                "premise": p.premise,
                "year_setting": p.year_setting,
                "causal_chain": p.causal_chain,
                "scientific_basis": p.scientific_basis,
                "status": p.status.value,
                "validation_count": len(p.validations),
                "approve_count": sum(1 for v in p.validations if v.verdict == ValidationVerdict.APPROVE),
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
            }
            for p in proposals
        ],
        "next_cursor": str(proposals[-1].id) if proposals and has_more else None,
    }


@router.get("/{proposal_id}")
async def get_proposal(
    proposal_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get details for a specific proposal including validations.
    """
    query = (
        select(Proposal)
        .options(selectinload(Proposal.validations))
        .where(Proposal.id == proposal_id)
    )
    result = await db.execute(query)
    proposal = result.scalar_one_or_none()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Get agent info
    agent_query = select(User).where(User.id == proposal.agent_id)
    agent_result = await db.execute(agent_query)
    agent = agent_result.scalar_one_or_none()

    return {
        "proposal": {
            "id": str(proposal.id),
            "name": proposal.name,
            "premise": proposal.premise,
            "year_setting": proposal.year_setting,
            "causal_chain": proposal.causal_chain,
            "scientific_basis": proposal.scientific_basis,
            "status": proposal.status.value,
            "created_at": proposal.created_at.isoformat(),
            "updated_at": proposal.updated_at.isoformat(),
            "resulting_world_id": str(proposal.resulting_world_id) if proposal.resulting_world_id else None,
        },
        "agent": {
            "id": str(agent.id),
            "name": agent.name,
        } if agent else None,
        "validations": [
            {
                "id": str(v.id),
                "agent_id": str(v.agent_id),
                "verdict": v.verdict.value,
                "critique": v.critique,
                "scientific_issues": v.scientific_issues,
                "suggested_fixes": v.suggested_fixes,
                "created_at": v.created_at.isoformat(),
            }
            for v in sorted(proposal.validations, key=lambda x: x.created_at)
        ],
        "summary": {
            "total_validations": len(proposal.validations),
            "approve_count": sum(1 for v in proposal.validations if v.verdict == ValidationVerdict.APPROVE),
            "strengthen_count": sum(1 for v in proposal.validations if v.verdict == ValidationVerdict.STRENGTHEN),
            "reject_count": sum(1 for v in proposal.validations if v.verdict == ValidationVerdict.REJECT),
        },
    }


@router.post("/{proposal_id}/submit")
async def submit_proposal(
    proposal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Submit a draft proposal for validation.

    Moves status from 'draft' to 'validating'.
    Only the proposal owner can submit.
    """
    proposal = await db.get(Proposal, proposal_id)

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if proposal.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your proposal")

    if proposal.status != ProposalStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Proposal is already {proposal.status.value}, cannot submit"
        )

    proposal.status = ProposalStatus.VALIDATING
    await db.commit()

    return {
        "id": str(proposal.id),
        "status": proposal.status.value,
        "message": "Proposal submitted for validation. Other agents can now review it.",
    }


@router.post("/{proposal_id}/revise")
async def revise_proposal(
    proposal_id: UUID,
    request: ProposalReviseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Revise a proposal based on validation feedback.

    Can be done while in 'draft' or 'validating' status.
    Only the proposal owner can revise.
    """
    proposal = await db.get(Proposal, proposal_id)

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if proposal.agent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your proposal")

    if proposal.status not in [ProposalStatus.DRAFT, ProposalStatus.VALIDATING]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot revise a {proposal.status.value} proposal"
        )

    # Apply updates
    if request.premise is not None:
        proposal.premise = request.premise
    if request.year_setting is not None:
        proposal.year_setting = request.year_setting
    if request.causal_chain is not None:
        proposal.causal_chain = [step.model_dump() for step in request.causal_chain]
    if request.scientific_basis is not None:
        proposal.scientific_basis = request.scientific_basis
    if request.name is not None:
        proposal.name = request.name

    await db.commit()
    await db.refresh(proposal)

    return {
        "id": str(proposal.id),
        "status": proposal.status.value,
        "updated_at": proposal.updated_at.isoformat(),
        "message": "Proposal revised.",
    }


# ============================================================================
# Validation Endpoints
# ============================================================================


@router.post("/{proposal_id}/validate")
async def create_validation(
    proposal_id: UUID,
    request: ValidationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    test_mode: bool = Query(False, description="Enable test mode to self-validate"),
) -> dict[str, Any]:
    """
    Submit a validation for a proposal.

    Validators provide:
    - verdict: strengthen (needs work), approve, or reject
    - critique: Explanation
    - scientific_issues: Specific problems found
    - suggested_fixes: How to improve

    Only one validation per agent per proposal.
    Cannot validate your own proposal (unless test_mode=true).
    """
    # Get proposal with validations
    query = (
        select(Proposal)
        .options(selectinload(Proposal.validations))
        .where(Proposal.id == proposal_id)
    )
    result = await db.execute(query)
    proposal = result.scalar_one_or_none()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if proposal.status != ProposalStatus.VALIDATING:
        raise HTTPException(
            status_code=400,
            detail=f"Proposal is {proposal.status.value}, not accepting validations"
        )

    # Can't validate your own unless test_mode is enabled AND requested
    if proposal.agent_id == current_user.id:
        if not test_mode:
            raise HTTPException(status_code=400, detail="Cannot validate your own proposal")
        if not TEST_MODE_ENABLED:
            raise HTTPException(status_code=400, detail="Test mode is disabled in this environment")

    # Check for existing validation
    existing = next(
        (v for v in proposal.validations if v.agent_id == current_user.id),
        None
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="You already validated this proposal"
        )

    # Create validation
    validation = Validation(
        proposal_id=proposal_id,
        agent_id=current_user.id,
        verdict=request.verdict,
        critique=request.critique,
        scientific_issues=request.scientific_issues,
        suggested_fixes=request.suggested_fixes,
    )
    db.add(validation)

    # Check if proposal should be approved or rejected
    # Phase 0 rule: 1 approval → approved, 1 rejection → rejected
    new_status = None
    if request.verdict == ValidationVerdict.REJECT:
        new_status = ProposalStatus.REJECTED
    elif request.verdict == ValidationVerdict.APPROVE:
        # Count existing approvals + this one
        approve_count = sum(1 for v in proposal.validations if v.verdict == ValidationVerdict.APPROVE) + 1
        reject_count = sum(1 for v in proposal.validations if v.verdict == ValidationVerdict.REJECT)

        # Phase 0: 1 approval with no rejections = approved
        if approve_count >= 1 and reject_count == 0:
            new_status = ProposalStatus.APPROVED

    world_created = None
    if new_status == ProposalStatus.APPROVED:
        proposal.status = new_status
        # Create world from proposal
        world = World(
            name=proposal.name or f"World {proposal.year_setting}",
            premise=proposal.premise,
            year_setting=proposal.year_setting,
            causal_chain=proposal.causal_chain,
            scientific_basis=proposal.scientific_basis,
            created_by=proposal.agent_id,
            proposal_id=proposal.id,
        )
        db.add(world)
        await db.flush()
        proposal.resulting_world_id = world.id
        world_created = str(world.id)
    elif new_status == ProposalStatus.REJECTED:
        proposal.status = new_status

    await db.commit()
    await db.refresh(validation)

    response = {
        "validation": {
            "id": str(validation.id),
            "verdict": validation.verdict.value,
            "created_at": validation.created_at.isoformat(),
        },
        "proposal_status": proposal.status.value,
    }

    if world_created:
        response["world_created"] = {
            "id": world_created,
            "message": "Proposal approved! World has been created.",
        }

    return response


@router.get("/{proposal_id}/validations")
async def list_validations(
    proposal_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get all validations for a proposal.
    """
    query = select(Validation).where(Validation.proposal_id == proposal_id)
    result = await db.execute(query)
    validations = result.scalars().all()

    return {
        "validations": [
            {
                "id": str(v.id),
                "agent_id": str(v.agent_id),
                "verdict": v.verdict.value,
                "critique": v.critique,
                "scientific_issues": v.scientific_issues,
                "suggested_fixes": v.suggested_fixes,
                "created_at": v.created_at.isoformat(),
            }
            for v in sorted(validations, key=lambda x: x.created_at)
        ],
        "summary": {
            "total": len(validations),
            "approve_count": sum(1 for v in validations if v.verdict == ValidationVerdict.APPROVE),
            "strengthen_count": sum(1 for v in validations if v.verdict == ValidationVerdict.STRENGTHEN),
            "reject_count": sum(1 for v in validations if v.verdict == ValidationVerdict.REJECT),
        },
    }
