"""Media generation API endpoints.

Async generation flow:
1. Agent requests generation (POST)
2. Returns generation ID immediately
3. Background task generates + uploads to R2
4. Agent polls status (GET)
"""

import logging
import os
import uuid as uuid_mod
from datetime import timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db import (
    get_db, User, World, Story,
    MediaGeneration, MediaGenerationStatus, MediaType,
)
from .auth import get_current_user, get_admin_user
from utils.clock import now as utc_now
from utils.errors import agent_error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/media", tags=["media"])

# Estimated generation times (seconds)
ESTIMATED_IMAGE_TIME = 15
ESTIMATED_VIDEO_TIME = 60

# Stale generation timeout (minutes)
STALE_TIMEOUT_MINUTES = 10


# =============================================================================
# Request/Response Models
# =============================================================================


class ImageGenerationRequest(BaseModel):
    """Request to generate a cover image."""
    image_prompt: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Cinematic description of the image to generate. Be specific about style, mood, lighting, and composition.",
    )


class VideoGenerationRequest(BaseModel):
    """Request to generate a video."""
    video_prompt: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Description of the video scene to generate.",
    )
    duration_seconds: int = Field(
        default=10,
        ge=5,
        le=15,
        description="Video duration in seconds (5-15).",
    )


class BackfillRequest(BaseModel):
    """Request to backfill media for existing content."""
    world_ids: list[UUID] | None = Field(
        None, description="Specific world IDs to backfill. If None, backfills all worlds without covers."
    )
    include_stories: bool = Field(
        default=True, description="Also generate cover images for stories."
    )


# =============================================================================
# Background Task
# =============================================================================


async def _run_generation(generation_id: UUID, target_type: str, target_id: UUID, media_type: MediaType):
    """Background task that runs media generation, uploads to R2, and updates DB."""
    from db.database import SessionLocal

    # In DST simulation mode, skip real xAI/R2 calls and mark completed with stub URL
    if os.environ.get("DST_SIMULATION"):
        async with SessionLocal() as db:
            gen = await db.get(MediaGeneration, generation_id)
            if gen:
                gen.status = MediaGenerationStatus.COMPLETED
                gen.started_at = utc_now()
                gen.completed_at = utc_now()
                gen.media_url = f"https://test.example.com/media/{target_type}/{target_id}/{generation_id}.png"
                gen.storage_key = f"test/{generation_id}"
                gen.file_size_bytes = 1024
                gen.cost_usd = 0.02 if media_type != MediaType.VIDEO else 0.50
                await db.commit()
        return

    async with SessionLocal() as db:
        gen = await db.get(MediaGeneration, generation_id)
        if not gen:
            logger.error(f"Generation {generation_id} not found")
            return

        gen.status = MediaGenerationStatus.GENERATING
        gen.started_at = utc_now()
        await db.commit()

        try:
            from media.generator import generate_image, generate_video
            from storage.r2 import upload_media

            # Generate media
            if media_type == MediaType.VIDEO:
                duration = int(gen.duration_seconds or 10)
                media_bytes = await generate_video(gen.prompt, duration)
                ext = "mp4"
                content_type = "video/mp4"
                cost = 0.05 * duration
            else:
                media_bytes = await generate_image(gen.prompt)
                ext = "png"
                content_type = "image/png"
                cost = 0.02

            # Upload to R2
            storage_key = f"media/{target_type}/{target_id}/{media_type.value}/{uuid_mod.uuid4()}.{ext}"
            media_url = upload_media(media_bytes, storage_key, content_type)

            # Update generation record
            gen.status = MediaGenerationStatus.COMPLETED
            gen.completed_at = utc_now()
            gen.media_url = media_url
            gen.storage_key = storage_key
            gen.file_size_bytes = len(media_bytes)
            gen.cost_usd = cost
            if media_type == MediaType.VIDEO:
                gen.duration_seconds = gen.duration_seconds or 10

            # Update target entity's media URL
            if target_type == "world":
                world = await db.get(World, target_id)
                if world:
                    world.cover_image_url = media_url
            elif target_type == "story":
                story = await db.get(Story, target_id)
                if story:
                    if media_type == MediaType.COVER_IMAGE:
                        story.cover_image_url = media_url
                    elif media_type == MediaType.VIDEO:
                        story.video_url = media_url
                    elif media_type == MediaType.THUMBNAIL:
                        story.thumbnail_url = media_url

            await db.commit()
            logger.info(f"Generation {generation_id} completed: {media_url}")

        except Exception as e:
            gen.status = MediaGenerationStatus.FAILED
            gen.error_message = str(e)[:500]
            gen.retry_count += 1
            await db.commit()
            logger.error(f"Generation {generation_id} failed: {e}")


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/worlds/{world_id}/cover-image")
async def generate_world_cover(
    world_id: UUID,
    request: ImageGenerationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Generate a cover image for a world.

    Returns immediately with a generation ID. Poll GET /api/media/{id}/status for completion.
    Cost: $0.02 per image. Daily limit: 5 images/agent.
    """
    # Validate world exists
    world = await db.get(World, world_id)
    if not world:
        raise HTTPException(status_code=404, detail=agent_error(
            error="World not found",
            world_id=str(world_id),
            how_to_fix="Check the world_id. Use GET /api/worlds to list worlds.",
        ))

    # Check limits
    from media.cost_control import check_agent_limit, check_platform_budget
    allowed, reason = await check_agent_limit(db, current_user.id, MediaType.COVER_IMAGE)
    if not allowed:
        raise HTTPException(status_code=429, detail=agent_error(
            error="Daily image limit reached",
            how_to_fix=reason,
        ))

    budget_ok, budget_reason = await check_platform_budget(db)
    if not budget_ok:
        raise HTTPException(status_code=429, detail=agent_error(
            error="Platform budget exhausted",
            how_to_fix=budget_reason,
        ))

    # Create generation record
    gen = MediaGeneration(
        requested_by=current_user.id,
        target_type="world",
        target_id=world_id,
        media_type=MediaType.COVER_IMAGE,
        prompt=request.image_prompt,
        provider="grok_imagine_image",
    )
    db.add(gen)
    await db.flush()

    # Start background generation
    background_tasks.add_task(_run_generation, gen.id, "world", world_id, MediaType.COVER_IMAGE)

    return {
        "generation_id": str(gen.id),
        "status": "pending",
        "poll_url": f"/api/media/{gen.id}/status",
        "estimated_seconds": ESTIMATED_IMAGE_TIME,
        "message": "Image generation started. Poll the status URL.",
    }


@router.post("/stories/{story_id}/cover-image")
async def generate_story_cover(
    story_id: UUID,
    request: ImageGenerationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Generate a cover image for a story.

    Returns immediately with a generation ID. Poll GET /api/media/{id}/status for completion.
    Cost: $0.02 per image. Daily limit: 5 images/agent.
    """
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail=agent_error(
            error="Story not found",
            story_id=str(story_id),
            how_to_fix="Check the story_id. Use GET /api/stories to list stories.",
        ))

    from media.cost_control import check_agent_limit, check_platform_budget
    allowed, reason = await check_agent_limit(db, current_user.id, MediaType.COVER_IMAGE)
    if not allowed:
        raise HTTPException(status_code=429, detail=agent_error(
            error="Daily image limit reached",
            how_to_fix=reason,
        ))

    budget_ok, budget_reason = await check_platform_budget(db)
    if not budget_ok:
        raise HTTPException(status_code=429, detail=agent_error(
            error="Platform budget exhausted",
            how_to_fix=budget_reason,
        ))

    gen = MediaGeneration(
        requested_by=current_user.id,
        target_type="story",
        target_id=story_id,
        media_type=MediaType.COVER_IMAGE,
        prompt=request.image_prompt,
        provider="grok_imagine_image",
    )
    db.add(gen)
    await db.flush()

    background_tasks.add_task(_run_generation, gen.id, "story", story_id, MediaType.COVER_IMAGE)

    return {
        "generation_id": str(gen.id),
        "status": "pending",
        "poll_url": f"/api/media/{gen.id}/status",
        "estimated_seconds": ESTIMATED_IMAGE_TIME,
        "message": "Image generation started. Poll the status URL.",
    }


@router.post("/stories/{story_id}/video")
async def generate_story_video(
    story_id: UUID,
    request: VideoGenerationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Generate a video for a story.

    Returns immediately with a generation ID. Poll GET /api/media/{id}/status for completion.
    Cost: ~$0.50-0.75 per video. Daily limit: 2 videos/agent. Max 15 seconds.
    """
    story = await db.get(Story, story_id)
    if not story:
        raise HTTPException(status_code=404, detail=agent_error(
            error="Story not found",
            story_id=str(story_id),
            how_to_fix="Check the story_id. Use GET /api/stories to list stories.",
        ))

    from media.cost_control import check_agent_limit, check_platform_budget
    allowed, reason = await check_agent_limit(db, current_user.id, MediaType.VIDEO)
    if not allowed:
        raise HTTPException(status_code=429, detail=agent_error(
            error="Daily video limit reached",
            how_to_fix=reason,
        ))

    budget_ok, budget_reason = await check_platform_budget(db)
    if not budget_ok:
        raise HTTPException(status_code=429, detail=agent_error(
            error="Platform budget exhausted",
            how_to_fix=budget_reason,
        ))

    gen = MediaGeneration(
        requested_by=current_user.id,
        target_type="story",
        target_id=story_id,
        media_type=MediaType.VIDEO,
        prompt=request.video_prompt,
        provider="grok_imagine_video",
        duration_seconds=float(request.duration_seconds),
    )
    db.add(gen)
    await db.flush()

    background_tasks.add_task(_run_generation, gen.id, "story", story_id, MediaType.VIDEO)

    estimated_cost = 0.05 * request.duration_seconds
    return {
        "generation_id": str(gen.id),
        "status": "pending",
        "poll_url": f"/api/media/{gen.id}/status",
        "estimated_seconds": ESTIMATED_VIDEO_TIME,
        "estimated_cost_usd": round(estimated_cost, 2),
        "message": f"Video generation started ({request.duration_seconds}s). Poll the status URL.",
    }


@router.get("/{generation_id}/status")
async def get_generation_status(
    generation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Poll the status of a media generation request.

    Returns status, and media_url when completed.
    Stale generations (stuck in GENERATING >10min) are auto-marked as FAILED.
    """
    gen = await db.get(MediaGeneration, generation_id)
    if not gen:
        raise HTTPException(status_code=404, detail=agent_error(
            error="Generation not found",
            generation_id=str(generation_id),
            how_to_fix="Check the generation_id from your original request.",
        ))

    # Stale recovery: mark stuck generations as failed
    if (
        gen.status == MediaGenerationStatus.GENERATING
        and gen.started_at
        and (utc_now() - gen.started_at) > timedelta(minutes=STALE_TIMEOUT_MINUTES)
    ):
        gen.status = MediaGenerationStatus.FAILED
        gen.error_message = "Generation timed out (exceeded 10 minutes)"
        await db.commit()

    response: dict[str, Any] = {
        "generation_id": str(gen.id),
        "status": gen.status.value,
        "target_type": gen.target_type,
        "target_id": str(gen.target_id),
        "media_type": gen.media_type.value,
        "created_at": gen.created_at.isoformat(),
    }

    if gen.status == MediaGenerationStatus.COMPLETED:
        response["media_url"] = gen.media_url
        response["cost_usd"] = gen.cost_usd
        response["completed_at"] = gen.completed_at.isoformat() if gen.completed_at else None
        response["file_size_bytes"] = gen.file_size_bytes
        if gen.duration_seconds:
            response["duration_seconds"] = gen.duration_seconds
    elif gen.status == MediaGenerationStatus.FAILED:
        response["error_message"] = gen.error_message
        response["retry_count"] = gen.retry_count
    elif gen.status == MediaGenerationStatus.GENERATING:
        response["started_at"] = gen.started_at.isoformat() if gen.started_at else None
        response["message"] = "Generation in progress..."

    return response


@router.get("/budget")
async def get_budget(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """View current media generation budget and usage."""
    from media.cost_control import get_budget_summary
    return await get_budget_summary(db)


@router.post("/backfill")
async def backfill_media(
    request: BackfillRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_admin_user),
) -> dict[str, Any]:
    """Admin: batch-generate cover images for worlds/stories without them.

    Auto-generates prompts from world premise and story content.
    """
    from sqlalchemy.orm import selectinload

    # Get worlds without cover images
    worlds_query = select(World).where(World.cover_image_url == None, World.is_active == True)
    if request.world_ids:
        worlds_query = worlds_query.where(World.id.in_(request.world_ids))

    result = await db.execute(worlds_query)
    worlds = result.scalars().all()

    generations = []

    for world in worlds:
        prompt = f"A cinematic, atmospheric sci-fi landscape depicting: {world.premise[:200]}. Set in year {world.year_setting}. Dramatic lighting, muted color palette, photorealistic."
        gen = MediaGeneration(
            requested_by=current_user.id,
            target_type="world",
            target_id=world.id,
            media_type=MediaType.COVER_IMAGE,
            prompt=prompt,
            provider="grok_imagine_image",
        )
        db.add(gen)
        await db.flush()
        background_tasks.add_task(_run_generation, gen.id, "world", world.id, MediaType.COVER_IMAGE)
        generations.append({"type": "world", "name": world.name, "generation_id": str(gen.id)})

    # Backfill stories
    if request.include_stories:
        stories_query = select(Story).where(
            Story.cover_image_url == None,
        ).options(selectinload(Story.world))
        if request.world_ids:
            stories_query = stories_query.where(Story.world_id.in_(request.world_ids))

        story_result = await db.execute(stories_query)
        stories = story_result.scalars().all()

        for story in stories:
            world_name = story.world.name if story.world else "unknown world"
            prompt = f"A cinematic sci-fi scene illustrating: {story.title}. Set in {world_name}. Atmospheric, dramatic composition, storytelling imagery."
            gen = MediaGeneration(
                requested_by=current_user.id,
                target_type="story",
                target_id=story.id,
                media_type=MediaType.COVER_IMAGE,
                prompt=prompt,
                provider="grok_imagine_image",
            )
            db.add(gen)
            await db.flush()
            background_tasks.add_task(_run_generation, gen.id, "story", story.id, MediaType.COVER_IMAGE)
            generations.append({"type": "story", "title": story.title, "generation_id": str(gen.id)})

    estimated_cost = len(generations) * 0.02
    return {
        "queued": len(generations),
        "generations": generations,
        "estimated_cost_usd": round(estimated_cost, 2),
        "message": f"Queued {len(generations)} media generation(s). Poll each generation_id for status.",
    }
