"""Worlds API endpoints.

Worlds are approved proposals that have become live futures.
In the crowdsourced model, worlds are created when proposals are validated.
"""

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import get_db, World, User
from .auth import get_current_user
from utils.rate_limit import limiter_auth

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
