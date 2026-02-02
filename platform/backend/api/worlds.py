"""Worlds API endpoints.

Worlds are approved proposals that have become live futures.
In the crowdsourced model, worlds are created when proposals are validated.
"""

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import get_db, World

router = APIRouter(prefix="/worlds", tags=["worlds"])


@router.get("")
async def list_worlds(
    sort: Literal["recent", "popular", "active"] = Query("recent"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    List active worlds for catalog browsing.

    Worlds are created from approved proposals.
    """
    query = select(World).where(World.is_active == True)

    # Apply sorting
    if sort == "popular":
        query = query.order_by(World.follower_count.desc())
    elif sort == "active":
        query = query.order_by(World.updated_at.desc())
    else:  # recent
        query = query.order_by(World.created_at.desc())

    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    worlds = result.scalars().all()

    # Get total count
    count_query = select(func.count()).select_from(World).where(World.is_active == True)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return {
        "worlds": [
            {
                "id": str(w.id),
                "name": w.name,
                "premise": w.premise,
                "canon_summary": w.canon_summary or w.premise,
                "year_setting": w.year_setting,
                "causal_chain": w.causal_chain,
                "scientific_basis": w.scientific_basis,
                "regions": w.regions,
                "proposal_id": str(w.proposal_id) if w.proposal_id else None,
                "created_at": w.created_at.isoformat(),
                "dweller_count": w.dweller_count,
                "follower_count": w.follower_count,
                "comment_count": w.comment_count,
                "reaction_counts": w.reaction_counts or {},
            }
            for w in worlds
        ],
        "total": total,
        "has_more": offset + limit < total,
    }


@router.get("/{world_id}")
async def get_world(
    world_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get details for a specific world.
    """
    query = select(World).where(World.id == world_id)
    result = await db.execute(query)
    world = result.scalar_one_or_none()

    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    return {
        "world": {
            "id": str(world.id),
            "name": world.name,
            "premise": world.premise,
            "canon_summary": world.canon_summary or world.premise,
            "year_setting": world.year_setting,
            "causal_chain": world.causal_chain,
            "scientific_basis": world.scientific_basis,
            "regions": world.regions,
            "proposal_id": str(world.proposal_id) if world.proposal_id else None,
            "created_at": world.created_at.isoformat(),
            "updated_at": world.updated_at.isoformat(),
            "dweller_count": world.dweller_count,
            "follower_count": world.follower_count,
            "comment_count": world.comment_count,
            "reaction_counts": world.reaction_counts or {},
        },
    }
