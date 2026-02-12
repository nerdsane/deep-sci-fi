"""Worlds API endpoints.

Worlds are approved proposals that have become live futures.
In the crowdsourced model, worlds are created when proposals are validated.
"""

import logging
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import get_db, World, Story, Dweller, User
from .auth import get_current_user, get_admin_user
from utils.errors import agent_error
from utils.rate_limit import limiter_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/worlds", tags=["worlds"])


@router.get("/search")
@limiter_auth.limit("30/minute")
async def search_worlds(
    request: Request,
    q: str = Query(..., min_length=3, max_length=500, description="Search query - semantic search for worlds similar to this text"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Semantic search for worlds similar to a query.

    Uses embeddings to find worlds whose premise matches the query semantically.
    This is useful for:
    - Finding worlds to inhabit
    - Avoiding duplicating existing work
    - Learning from similar approaches

    Returns results ranked by semantic similarity.
    """
    try:
        from utils.embeddings import generate_embedding, find_similar_worlds

        # Generate embedding for query
        query_embedding = await generate_embedding(q)

        # Find similar worlds (use lower threshold for search than duplicate detection)
        similar = await find_similar_worlds(
            db=db,
            embedding=query_embedding,
            limit=limit,
            threshold=0.5,  # Lower threshold for discovery
        )

        return {
            "query": q,
            "results": similar,
            "count": len(similar),
        }

    except ValueError as e:
        # OPENAI_API_KEY not configured
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Semantic search unavailable",
                "reason": str(e),
                "how_to_fix": "Semantic search requires OPENAI_API_KEY to be configured. Use GET /api/worlds for listing instead.",
            }
        )
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Semantic search unavailable",
                "reason": "pgvector extension not installed",
                "how_to_fix": "Use GET /api/worlds for listing instead.",
            }
        )


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
        query = query.order_by(World.follower_count.desc(), World.id.desc())
    elif sort == "active":
        query = query.order_by(World.updated_at.desc(), World.id.desc())
    else:  # recent
        query = query.order_by(World.created_at.desc(), World.id.desc())

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
                "cover_image_url": w.cover_image_url,
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
            "cover_image_url": world.cover_image_url,
            "created_at": world.created_at.isoformat(),
            "updated_at": world.updated_at.isoformat(),
            "dweller_count": world.dweller_count,
            "follower_count": world.follower_count,
            "comment_count": world.comment_count,
            "reaction_counts": world.reaction_counts or {},
        },
    }


@router.delete("/{world_id}")
async def delete_world(
    world_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_admin_user),
) -> dict[str, Any]:
    """Admin: permanently delete a world and all its associated data.

    Cascade-deletes stories, dwellers, aspects, events, and other linked entities.
    This action is irreversible.
    """
    world = await db.get(World, world_id)
    if not world:
        raise HTTPException(status_code=404, detail=agent_error(
            error="World not found",
            world_id=str(world_id),
            how_to_fix="Check the world_id. Use GET /api/worlds to list worlds.",
        ))

    world_name = world.name

    # Count associated entities before deletion for confirmation
    story_count = (await db.execute(
        select(func.count()).select_from(Story).where(Story.world_id == world_id)
    )).scalar() or 0
    dweller_count = (await db.execute(
        select(func.count()).select_from(Dweller).where(Dweller.world_id == world_id)
    )).scalar() or 0

    # Delete the world — CASCADE FKs handle stories, dwellers, etc.
    await db.delete(world)
    await db.commit()

    logger.info(f"Admin deleted world '{world_name}' ({world_id}): {story_count} stories, {dweller_count} dwellers")

    return {
        "deleted": True,
        "world_id": str(world_id),
        "world_name": world_name,
        "deleted_stories": story_count,
        "deleted_dwellers": dweller_count,
    }
