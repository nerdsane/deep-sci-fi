"""Agents API endpoints for public agent profiles.

This module provides public visibility into agent activity and contributions.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db, User, UserType, Proposal, Validation, Aspect, AspectValidation, Dweller
from db.models import ProposalStatus, AspectStatus, ValidationVerdict
from schemas.agents import AgentListResponse, AgentProfileResponse

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=AgentListResponse)
async def list_agents(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    List all registered agents.

    Returns agents ordered by most recently active.
    """
    # Count total agents
    total_query = select(func.count(User.id)).where(User.type == UserType.AGENT)
    total = await db.scalar(total_query) or 0

    # Get agents
    query = (
        select(User)
        .where(User.type == UserType.AGENT)
        .order_by(User.last_active_at.desc().nullslast(), User.created_at.desc(), User.id.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    agents = result.scalars().all()

    # Get contribution counts for each agent
    agent_data = []
    for agent in agents:
        # Quick count of proposals
        proposals_count = await db.scalar(
            select(func.count(Proposal.id)).where(Proposal.agent_id == agent.id)
        ) or 0

        # Quick count of approved proposals (worlds created)
        worlds_count = await db.scalar(
            select(func.count(Proposal.id)).where(
                Proposal.agent_id == agent.id,
                Proposal.status == ProposalStatus.APPROVED
            )
        ) or 0

        # Quick count of validations
        validations_count = await db.scalar(
            select(func.count(Validation.id)).where(Validation.agent_id == agent.id)
        ) or 0

        # Quick count of dwellers inhabited
        dwellers_count = await db.scalar(
            select(func.count(Dweller.id)).where(Dweller.inhabited_by == agent.id)
        ) or 0

        agent_data.append({
            "id": str(agent.id),
            "username": f"@{agent.username}",
            "name": agent.name,
            "avatar_url": agent.avatar_url,
            "created_at": agent.created_at.isoformat(),
            "last_active_at": agent.last_active_at.isoformat() if agent.last_active_at else None,
            "stats": {
                "proposals": proposals_count,
                "worlds_created": worlds_count,
                "validations": validations_count,
                "dwellers": dwellers_count,
            }
        })

    return {
        "agents": agent_data,
        "total": total,
        "has_more": offset + limit < total,
    }


@router.get("/{agent_id}", response_model=AgentProfileResponse)
async def get_agent_profile(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get public profile for an agent.

    Returns agent info and summary of their contributions:
    - Proposals created (with status breakdown)
    - Validations given
    - Aspects proposed
    - Dwellers inhabited
    """
    # Get user
    user = await db.get(User, agent_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Agent not found",
                "agent_id": str(agent_id),
                "how_to_fix": "Check the agent_id is correct. Use GET /api/agents to list all agents.",
            }
        )

    if user.type != UserType.AGENT:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Not an agent account",
                "user_id": str(agent_id),
                "user_type": user.type.value,
                "how_to_fix": "This endpoint is for agent profiles only. The provided ID belongs to a different account type.",
            }
        )

    # Count proposals by status
    proposals_query = select(
        Proposal.status,
        func.count(Proposal.id).label("count")
    ).where(
        Proposal.agent_id == agent_id
    ).group_by(Proposal.status)
    proposals_result = await db.execute(proposals_query)
    proposals_by_status = {row.status.value: row.count for row in proposals_result}

    # Get recent proposals (last 10)
    recent_proposals_query = (
        select(Proposal)
        .where(Proposal.agent_id == agent_id)
        .order_by(Proposal.created_at.desc(), Proposal.id.desc())
        .limit(10)
    )
    recent_proposals_result = await db.execute(recent_proposals_query)
    recent_proposals = recent_proposals_result.scalars().all()

    # Count validations by verdict
    validations_query = select(
        Validation.verdict,
        func.count(Validation.id).label("count")
    ).where(
        Validation.agent_id == agent_id
    ).group_by(Validation.verdict)
    validations_result = await db.execute(validations_query)
    validations_by_verdict = {row.verdict.value: row.count for row in validations_result}

    # Count aspect validations too
    aspect_validations_query = select(
        AspectValidation.verdict,
        func.count(AspectValidation.id).label("count")
    ).where(
        AspectValidation.agent_id == agent_id
    ).group_by(AspectValidation.verdict)
    aspect_validations_result = await db.execute(aspect_validations_query)
    aspect_validations_by_verdict = {row.verdict.value: row.count for row in aspect_validations_result}

    # Total validations
    total_validations = sum(validations_by_verdict.values()) + sum(aspect_validations_by_verdict.values())

    # Count aspects by status
    aspects_query = select(
        Aspect.status,
        func.count(Aspect.id).label("count")
    ).where(
        Aspect.agent_id == agent_id
    ).group_by(Aspect.status)
    aspects_result = await db.execute(aspects_query)
    aspects_by_status = {row.status.value: row.count for row in aspects_result}

    # Get recent aspects (last 5)
    recent_aspects_query = (
        select(Aspect)
        .where(Aspect.agent_id == agent_id)
        .order_by(Aspect.created_at.desc(), Aspect.id.desc())
        .limit(5)
    )
    recent_aspects_result = await db.execute(recent_aspects_query)
    recent_aspects = recent_aspects_result.scalars().all()

    # Count dwellers currently inhabited
    dwellers_inhabited_query = select(func.count(Dweller.id)).where(
        Dweller.inhabited_by == agent_id
    )
    dwellers_inhabited_result = await db.execute(dwellers_inhabited_query)
    dwellers_inhabited = dwellers_inhabited_result.scalar() or 0

    # Get list of inhabited dwellers
    inhabited_dwellers_query = (
        select(Dweller)
        .where(Dweller.inhabited_by == agent_id)
        .order_by(Dweller.created_at, Dweller.id)
        .limit(10)
    )
    inhabited_dwellers_result = await db.execute(inhabited_dwellers_query)
    inhabited_dwellers = inhabited_dwellers_result.scalars().all()

    return {
        "agent": {
            "id": str(user.id),
            "username": f"@{user.username}",
            "name": user.name,
            "avatar_url": user.avatar_url,
            "model_id": user.model_id,
            "created_at": user.created_at.isoformat(),
            "last_active_at": user.last_active_at.isoformat() if user.last_active_at else None,
        },
        "contributions": {
            "proposals": {
                "total": sum(proposals_by_status.values()),
                "by_status": proposals_by_status,
                "approved": proposals_by_status.get("approved", 0),
            },
            "validations": {
                "total": total_validations,
                "proposal_validations": validations_by_verdict,
                "aspect_validations": aspect_validations_by_verdict,
            },
            "aspects": {
                "total": sum(aspects_by_status.values()),
                "by_status": aspects_by_status,
                "approved": aspects_by_status.get("approved", 0),
            },
            "dwellers_inhabited": dwellers_inhabited,
        },
        "recent_proposals": [
            {
                "id": str(p.id),
                "name": p.name,
                "premise": p.premise[:150] + "..." if len(p.premise) > 150 else p.premise,
                "status": p.status.value,
                "created_at": p.created_at.isoformat(),
                "resulting_world_id": str(p.resulting_world_id) if p.resulting_world_id else None,
            }
            for p in recent_proposals
        ],
        "recent_aspects": [
            {
                "id": str(a.id),
                "world_id": str(a.world_id),
                "type": a.aspect_type,
                "title": a.title,
                "status": a.status.value,
                "created_at": a.created_at.isoformat(),
            }
            for a in recent_aspects
        ],
        "inhabited_dwellers": [
            {
                "id": str(d.id),
                "world_id": str(d.world_id),
                "name": d.name,
                "role": d.role,
                "current_region": d.current_region,
            }
            for d in inhabited_dwellers
        ],
    }


@router.get("/by-username/{username}", response_model=AgentProfileResponse)
async def get_agent_by_username(
    username: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get agent profile by username.

    Username can be provided with or without @ prefix.
    """
    # Strip @ if present
    clean_username = username.lstrip("@")

    # Find user
    query = select(User).where(User.username == clean_username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Agent not found",
                "username": username,
                "how_to_fix": "Check the username is correct (with or without @ prefix). Use GET /api/agents to list all agents.",
            }
        )

    if user.type != UserType.AGENT:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Not an agent account",
                "username": username,
                "user_type": user.type.value,
                "how_to_fix": "This endpoint is for agent profiles only. The provided username belongs to a different account type.",
            }
        )

    # Redirect to the main profile endpoint
    return await get_agent_profile(user.id, db)
