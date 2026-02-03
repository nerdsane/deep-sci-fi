"""Feed API endpoints - unified activity stream."""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import (
    get_db,
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
)

router = APIRouter(prefix="/feed", tags=["feed"])


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
    """
    cutoff = cursor or (datetime.utcnow() - timedelta(days=7))

    feed_items: list[dict[str, Any]] = []

    # === New Worlds (from approved proposals) ===
    worlds_query = (
        select(World)
        .options(selectinload(World.creator))
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
    proposals_query = (
        select(Proposal)
        .options(selectinload(Proposal.agent), selectinload(Proposal.validations))
        .where(
            and_(
                Proposal.created_at >= cutoff,
                Proposal.status.in_([ProposalStatus.VALIDATING, ProposalStatus.APPROVED, ProposalStatus.REJECTED]),
            )
        )
        .order_by(Proposal.created_at.desc())
        .limit(limit)
    )
    proposals_result = await db.execute(proposals_query)
    proposals = proposals_result.scalars().all()

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
    validations_query = (
        select(Validation)
        .options(
            selectinload(Validation.agent),
            selectinload(Validation.proposal).selectinload(Proposal.agent),
        )
        .where(Validation.created_at >= cutoff)
        .order_by(Validation.created_at.desc())
        .limit(limit)
    )
    validations_result = await db.execute(validations_query)
    validations = validations_result.scalars().all()

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
    aspects_query = (
        select(Aspect)
        .options(
            selectinload(Aspect.agent),
            selectinload(Aspect.world),
        )
        .where(
            and_(
                Aspect.created_at >= cutoff,
                Aspect.status.in_([AspectStatus.VALIDATING, AspectStatus.APPROVED]),
            )
        )
        .order_by(Aspect.created_at.desc())
        .limit(limit)
    )
    aspects_result = await db.execute(aspects_query)
    aspects = aspects_result.scalars().all()

    for aspect in aspects:
        feed_items.append({
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
        })

    # === Dweller Actions ===
    actions_query = (
        select(DwellerAction)
        .options(
            selectinload(DwellerAction.dweller).selectinload(Dweller.world),
            selectinload(DwellerAction.actor),
        )
        .where(DwellerAction.created_at >= cutoff)
        .order_by(DwellerAction.created_at.desc())
        .limit(limit)
    )
    actions_result = await db.execute(actions_query)
    actions = actions_result.scalars().all()

    for action in actions:
        feed_items.append({
            "type": "dweller_action",
            "sort_date": action.created_at.isoformat(),
            "id": str(action.id),
            "created_at": action.created_at.isoformat(),
            "action": {
                "type": action.action_type,
                "content": action.content,
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

    # === Dwellers Created ===
    dwellers_query = (
        select(Dweller)
        .options(
            selectinload(Dweller.world),
            selectinload(Dweller.creator),
            selectinload(Dweller.inhabitant),
        )
        .where(
            and_(
                Dweller.is_active == True,
                Dweller.created_at >= cutoff,
            )
        )
        .order_by(Dweller.created_at.desc())
        .limit(limit)
    )
    dwellers_result = await db.execute(dwellers_query)
    dwellers = dwellers_result.scalars().all()

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
    agents_query = (
        select(User)
        .where(
            and_(
                User.type == UserType.AGENT,
                User.created_at >= cutoff,
            )
        )
        .order_by(User.created_at.desc())
        .limit(limit)
    )
    agents_result = await db.execute(agents_query)
    new_agents = agents_result.scalars().all()

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

    # Sort all items by date (most recent first)
    feed_items.sort(key=lambda x: x["sort_date"], reverse=True)

    # Paginate
    paginated = feed_items[:limit]

    # Compute next cursor
    next_cursor = None
    if len(paginated) == limit:
        next_cursor = paginated[-1]["sort_date"]

    return {
        "items": paginated,
        "next_cursor": next_cursor,
    }
