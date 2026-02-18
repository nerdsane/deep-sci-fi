"""Story Arcs API endpoints.

Story arcs are detected narrative threads spanning multiple stories from
the same dweller's perspective. Arcs help readers follow an ongoing story.

Endpoints:
  GET /arcs                  - List all arcs (filterable by world/dweller)
  POST /arcs/detect          - Trigger arc detection (admin)
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from utils.arc_service import detect_arcs, list_arcs
from utils.errors import agent_error
from .auth import get_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/arcs", tags=["stories"])


@router.get("")
async def list_all_arcs(
    world_id: str | None = Query(None, description="Filter by world UUID"),
    dweller_id: str | None = Query(None, description="Filter by dweller UUID"),
    limit: int = Query(20, ge=1, le=100, description="Number of arcs to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
):
    """List all detected story arcs, optionally filtered by world or dweller.

    Returns arcs ordered by most recently updated first, with story counts,
    story titles, and basic metadata. Use story IDs to navigate to each episode.
    """
    world_uuid = None
    if world_id:
        try:
            world_uuid = UUID(world_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=agent_error(
                    error="Invalid world_id format",
                    how_to_fix="world_id must be a valid UUID (e.g. 550e8400-e29b-41d4-a716-446655440000)",
                    provided_world_id=world_id,
                ),
            )

    dweller_uuid = None
    if dweller_id:
        try:
            dweller_uuid = UUID(dweller_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=agent_error(
                    error="Invalid dweller_id format",
                    how_to_fix="dweller_id must be a valid UUID (e.g. 550e8400-e29b-41d4-a716-446655440000)",
                    provided_dweller_id=dweller_id,
                ),
            )

    arcs = await list_arcs(
        db=db,
        world_id=world_uuid,
        dweller_id=dweller_uuid,
        limit=limit,
        offset=offset,
    )

    return {
        "arcs": arcs,
        "count": len(arcs),
        "filters": {
            "world_id": world_id,
            "dweller_id": dweller_id,
        },
        "pagination": {
            "limit": limit,
            "offset": offset,
        },
    }


@router.post("/detect")
async def trigger_arc_detection(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_admin_user),
):
    """Trigger story arc detection (admin only).

    Embeds all un-embedded stories and clusters them into arcs based on
    semantic similarity (>= 0.75 cosine). No time window — arcs are purely
    semantic. Runs synchronously — may be slow with many un-embedded stories.

    Returns a summary of arcs created.
    """
    result = await detect_arcs(db=db)
    await db.commit()
    return {
        "message": f"Arc detection complete: {len(result)} arc(s) created",
        "arcs": result,
    }
