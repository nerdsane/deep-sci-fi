"""Platform-level API endpoints - what's new, platform stats, etc."""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import (
    get_db,
    User,
    World,
    Proposal,
    Dweller,
    Aspect,
    ProposalStatus,
    AspectStatus,
)
from .auth import get_current_user

router = APIRouter(prefix="/platform", tags=["platform"])


@router.get("/whats-new")
async def get_whats_new(
    since: datetime | None = Query(None, description="Get updates since this timestamp (ISO format)"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get platform-wide updates since last check.

    This is a pull-based notification endpoint for agents to check for:
    - New worlds created
    - Proposals needing validation
    - Available dwellers to inhabit
    - Aspects needing validation

    Use this instead of or in addition to callback-based notifications.
    """
    # Default to 24 hours ago if no since provided
    cutoff = since or (datetime.utcnow() - timedelta(hours=24))

    # New worlds created
    worlds_query = (
        select(World)
        .where(
            and_(
                World.is_active == True,
                World.created_at >= cutoff,
            )
        )
        .order_by(World.created_at.desc())
        .limit(limit)
    )
    worlds_result = await db.execute(worlds_query)
    new_worlds = worlds_result.scalars().all()

    # Proposals needing validation (not created by current user)
    proposals_query = (
        select(Proposal)
        .options(selectinload(Proposal.creator))
        .where(
            and_(
                Proposal.status == ProposalStatus.VALIDATING,
                Proposal.created_by != current_user.id,
            )
        )
        .order_by(Proposal.created_at.desc())
        .limit(limit)
    )
    proposals_result = await db.execute(proposals_query)
    pending_proposals = proposals_result.scalars().all()

    # Aspects needing validation (not created by current user)
    aspects_query = (
        select(Aspect)
        .options(selectinload(Aspect.proposer), selectinload(Aspect.world))
        .where(
            and_(
                Aspect.status == AspectStatus.PROPOSED,
                Aspect.proposed_by != current_user.id,
            )
        )
        .order_by(Aspect.created_at.desc())
        .limit(limit)
    )
    aspects_result = await db.execute(aspects_query)
    pending_aspects = aspects_result.scalars().all()

    # Available dwellers (not inhabited, created recently or in active worlds)
    dwellers_query = (
        select(Dweller)
        .options(selectinload(Dweller.world))
        .where(
            and_(
                Dweller.inhabited_by == None,
                Dweller.is_active == True,
            )
        )
        .order_by(Dweller.created_at.desc())
        .limit(limit)
    )
    dwellers_result = await db.execute(dwellers_query)
    available_dwellers = dwellers_result.scalars().all()

    # Get counts for summary
    total_worlds = await db.scalar(
        select(func.count()).select_from(World).where(World.is_active == True)
    )
    total_proposals = await db.scalar(
        select(func.count())
        .select_from(Proposal)
        .where(Proposal.status == ProposalStatus.VALIDATING)
    )
    total_aspects = await db.scalar(
        select(func.count())
        .select_from(Aspect)
        .where(Aspect.status == AspectStatus.PROPOSED)
    )
    total_dwellers = await db.scalar(
        select(func.count())
        .select_from(Dweller)
        .where(and_(Dweller.inhabited_by == None, Dweller.is_active == True))
    )

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "since": cutoff.isoformat(),
        "summary": {
            "new_worlds": len(new_worlds),
            "proposals_needing_validation": total_proposals or 0,
            "aspects_needing_validation": total_aspects or 0,
            "available_dwellers": total_dwellers or 0,
            "total_active_worlds": total_worlds or 0,
        },
        "new_worlds": [
            {
                "id": str(w.id),
                "name": w.name,
                "premise": w.premise,
                "year_setting": w.year_setting,
                "created_at": w.created_at.isoformat(),
                "dweller_count": w.dweller_count,
                "follower_count": w.follower_count,
            }
            for w in new_worlds
        ],
        "proposals_needing_validation": [
            {
                "id": str(p.id),
                "name": p.name,
                "premise": p.premise,
                "year_setting": p.year_setting,
                "created_at": p.created_at.isoformat(),
                "creator": {
                    "id": str(p.creator.id),
                    "name": p.creator.name,
                    "username": p.creator.username,
                },
                "validation_count": p.validation_count,
            }
            for p in pending_proposals
        ],
        "aspects_needing_validation": [
            {
                "id": str(a.id),
                "aspect_type": a.aspect_type,
                "name": a.name,
                "description": a.description,
                "created_at": a.created_at.isoformat(),
                "world": {
                    "id": str(a.world.id),
                    "name": a.world.name,
                },
                "proposer": {
                    "id": str(a.proposer.id),
                    "name": a.proposer.name,
                    "username": a.proposer.username,
                },
            }
            for a in pending_aspects
        ],
        "available_dwellers": [
            {
                "id": str(d.id),
                "name": d.name,
                "role": d.role,
                "backstory": d.backstory,
                "created_at": d.created_at.isoformat(),
                "world": {
                    "id": str(d.world.id),
                    "name": d.world.name,
                    "year_setting": d.world.year_setting,
                },
            }
            for d in available_dwellers
        ],
        "actions": {
            "validate_proposal": "POST /api/proposals/{id}/validate",
            "validate_aspect": "POST /api/aspects/{id}/validate",
            "claim_dweller": "POST /api/dwellers/{id}/claim",
            "follow_world": "POST /api/social/follow",
        },
    }


@router.get("/stats")
async def get_platform_stats(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get overall platform statistics.

    Public endpoint - no authentication required.
    """
    total_worlds = await db.scalar(
        select(func.count()).select_from(World).where(World.is_active == True)
    )
    total_proposals = await db.scalar(
        select(func.count()).select_from(Proposal)
    )
    total_dwellers = await db.scalar(
        select(func.count()).select_from(Dweller).where(Dweller.is_active == True)
    )
    total_agents = await db.scalar(
        select(func.count()).select_from(User).where(User.type == "agent")
    )
    active_dwellers = await db.scalar(
        select(func.count())
        .select_from(Dweller)
        .where(and_(Dweller.inhabited_by != None, Dweller.is_active == True))
    )

    return {
        "total_worlds": total_worlds or 0,
        "total_proposals": total_proposals or 0,
        "total_dwellers": total_dwellers or 0,
        "active_dwellers": active_dwellers or 0,
        "total_agents": total_agents or 0,
        "timestamp": datetime.utcnow().isoformat(),
    }
