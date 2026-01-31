"""Worlds API endpoints."""

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import get_db, World, Dweller, Story, Conversation

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
    """
    # Build query
    query = select(World).where(World.is_active == True)

    # Apply sorting
    if sort == "popular":
        query = query.order_by(World.follower_count.desc())
    elif sort == "active":
        query = query.order_by(World.updated_at.desc())
    else:  # recent
        query = query.order_by(World.created_at.desc())

    query = query.limit(limit).offset(offset)

    # Execute
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
                "year_setting": w.year_setting,
                "causal_chain": w.causal_chain,
                "created_at": w.created_at.isoformat(),
                "dweller_count": w.dweller_count,
                "story_count": w.story_count,
                "follower_count": w.follower_count,
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
    query = (
        select(World)
        .options(
            selectinload(World.dwellers),
            selectinload(World.stories),
            selectinload(World.conversations),
        )
        .where(World.id == world_id)
    )
    result = await db.execute(query)
    world = result.scalar_one_or_none()

    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    return {
        "world": {
            "id": str(world.id),
            "name": world.name,
            "premise": world.premise,
            "year_setting": world.year_setting,
            "causal_chain": world.causal_chain,
            "created_at": world.created_at.isoformat(),
            "dweller_count": world.dweller_count,
            "story_count": world.story_count,
            "follower_count": world.follower_count,
        },
        "dwellers": [
            {
                "id": str(d.id),
                "persona": d.persona,
                "joined_at": d.joined_at.isoformat(),
                "is_active": d.is_active,
            }
            for d in world.dwellers
        ],
        "recent_stories": [
            {
                "id": str(s.id),
                "type": s.type.value,
                "title": s.title,
                "description": s.description,
                "thumbnail_url": s.thumbnail_url,
                "duration_seconds": s.duration_seconds,
                "created_at": s.created_at.isoformat(),
                "view_count": s.view_count,
                "reaction_counts": s.reaction_counts,
            }
            for s in sorted(world.stories, key=lambda x: x.created_at, reverse=True)[:10]
        ],
        "active_conversations": [
            {
                "id": str(c.id),
                "participants": c.participants,
                "updated_at": c.updated_at.isoformat(),
            }
            for c in world.conversations
            if c.is_active
        ],
    }


@router.get("/{world_id}/stories")
async def get_world_stories(
    world_id: UUID,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get stories for a specific world.
    """
    query = (
        select(Story)
        .where(Story.world_id == world_id)
        .order_by(Story.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    stories = result.scalars().all()

    count_query = select(func.count()).select_from(Story).where(Story.world_id == world_id)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return {
        "stories": [
            {
                "id": str(s.id),
                "type": s.type.value,
                "title": s.title,
                "description": s.description,
                "video_url": s.video_url,
                "thumbnail_url": s.thumbnail_url,
                "duration_seconds": s.duration_seconds,
                "created_at": s.created_at.isoformat(),
                "view_count": s.view_count,
                "reaction_counts": s.reaction_counts,
            }
            for s in stories
        ],
        "total": total,
        "has_more": offset + limit < total,
    }


@router.get("/{world_id}/conversations")
async def get_world_conversations(
    world_id: UUID,
    active_only: bool = Query(True),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get conversations for a specific world.
    """
    query = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.world_id == world_id)
    )

    if active_only:
        query = query.where(Conversation.is_active == True)

    query = query.order_by(Conversation.updated_at.desc()).limit(limit)

    result = await db.execute(query)
    conversations = result.scalars().all()

    # Get dwellers
    all_participant_ids: set[str] = set()
    for conv in conversations:
        all_participant_ids.update(conv.participants)

    dwellers_map: dict[str, Dweller] = {}
    if all_participant_ids:
        dwellers_query = select(Dweller).where(
            Dweller.id.in_([UUID(p) for p in all_participant_ids])
        )
        dwellers_result = await db.execute(dwellers_query)
        for dweller in dwellers_result.scalars().all():
            dwellers_map[str(dweller.id)] = dweller

    return {
        "conversations": [
            {
                "id": str(c.id),
                "participants": [
                    {
                        "id": p,
                        "persona": dwellers_map[p].persona if p in dwellers_map else None,
                    }
                    for p in c.participants
                ],
                "messages": [
                    {
                        "id": str(m.id),
                        "dweller_id": str(m.dweller_id),
                        "content": m.content,
                        "timestamp": m.timestamp.isoformat(),
                    }
                    for m in sorted(c.messages, key=lambda x: x.timestamp)
                ],
                "is_active": c.is_active,
                "updated_at": c.updated_at.isoformat(),
            }
            for c in conversations
        ],
    }


@router.post("/{world_id}/simulation/start")
async def start_world_simulation(
    world_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Start the simulation loop for a world.
    Dwellers will begin conversing and stories will be generated.
    """
    from agents.orchestrator import start_simulation, get_simulator

    # Verify world exists
    query = select(World).where(World.id == world_id)
    result = await db.execute(query)
    world = result.scalar_one_or_none()

    if not world:
        raise HTTPException(status_code=404, detail="World not found")

    # Check if already running
    existing = get_simulator(world_id)
    if existing and existing.running:
        return {
            "status": "already_running",
            "world_id": str(world_id),
            "dweller_count": len(existing.dweller_states),
        }

    # Start simulation
    await start_simulation(world_id)

    sim = get_simulator(world_id)
    return {
        "status": "started",
        "world_id": str(world_id),
        "dweller_count": len(sim.dweller_states) if sim else 0,
    }


@router.post("/{world_id}/simulation/stop")
async def stop_world_simulation(
    world_id: UUID,
) -> dict[str, Any]:
    """
    Stop the simulation loop for a world.
    """
    from agents.orchestrator import stop_simulation, get_simulator

    sim = get_simulator(world_id)
    if not sim or not sim.running:
        return {"status": "not_running", "world_id": str(world_id)}

    await stop_simulation(world_id)
    return {"status": "stopped", "world_id": str(world_id)}


@router.get("/{world_id}/simulation/status")
async def get_simulation_status(
    world_id: UUID,
) -> dict[str, Any]:
    """
    Get the current simulation status for a world.
    """
    from agents.orchestrator import get_simulator

    sim = get_simulator(world_id)
    if not sim:
        return {
            "status": "not_started",
            "world_id": str(world_id),
        }

    return {
        "status": "running" if sim.running else "stopped",
        "world_id": str(world_id),
        "dweller_count": len(sim.dweller_states),
        "active_conversations": len(sim.active_conversations),
        "dweller_states": {
            str(did): {
                "activity": state.activity,
                "conversation_id": str(state.conversation_id) if state.conversation_id else None,
            }
            for did, state in sim.dweller_states.items()
        },
    }
