"""Media generation API endpoints.

Async generation flow:
1. Agent requests generation (POST)
2. Returns generation ID immediately
3. Background task generates + uploads to R2
4. Agent polls status (GET)
"""

import asyncio
import logging
import os
import uuid as uuid_mod
from datetime import timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from db import (
    get_db, User, World, Story,
    MediaGeneration, MediaGenerationStatus, MediaType,
)
from .auth import get_current_user, get_admin_user
from utils.clock import now as utc_now
from utils.errors import agent_error
from schemas.media import BudgetResponse, GenerateMediaResponse, GenerationStatusResponse

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

            # Auto-generate cover image after video completion
            if target_type == "story" and media_type == MediaType.VIDEO:
                story = await db.get(Story, target_id)
                if story and story.video_prompt and not story.cover_image_url:
                    logger.info(f"Auto-queuing cover image for story {target_id} after video completion")
                    cover_gen = MediaGeneration(
                        requested_by=gen.requested_by,
                        target_type="story",
                        target_id=target_id,
                        media_type=MediaType.COVER_IMAGE,
                        prompt=story.video_prompt,
                        provider="grok_imagine_image",
                    )
                    db.add(cover_gen)
                    await db.commit()
                    # Fire and forget - don't wait for this to complete
                    asyncio.create_task(_run_generation(cover_gen.id, "story", target_id, MediaType.COVER_IMAGE))

        except Exception as e:
            gen.status = MediaGenerationStatus.FAILED
            gen.error_message = str(e)[:500]
            gen.retry_count += 1
            await db.commit()
            logger.error(f"Generation {generation_id} failed: {e}")


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/worlds/{world_id}/cover-image", response_model=GenerateMediaResponse)
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
    await db.commit()

    # Start background generation (commit first so background task's separate session can see the record)
    background_tasks.add_task(_run_generation, gen.id, "world", world_id, MediaType.COVER_IMAGE)

    return {
        "generation_id": str(gen.id),
        "status": "pending",
        "poll_url": f"/api/media/{gen.id}/status",
        "estimated_seconds": ESTIMATED_IMAGE_TIME,
        "message": "Image generation started. Poll the status URL.",
    }


@router.post("/stories/{story_id}/video", response_model=GenerateMediaResponse)
async def generate_story_video(
    story_id: UUID,
    request: VideoGenerationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Generate a video for a story.

    Stories only support video generation (not cover images).

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

    # Anchor video prompt to the world's time period for futuristic aesthetics
    video_prompt = request.video_prompt
    story_world = await db.get(World, story.world_id)
    if story_world:
        year = getattr(story_world, "year_setting", None)
        if year and str(year) not in video_prompt:
            video_prompt = f"Set in the year {year}, in a future world. {video_prompt}"

    gen = MediaGeneration(
        requested_by=current_user.id,
        target_type="story",
        target_id=story_id,
        media_type=MediaType.VIDEO,
        prompt=video_prompt,
        provider="grok_imagine_video",
        duration_seconds=float(request.duration_seconds),
    )
    db.add(gen)
    await db.commit()

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


@router.get("/{generation_id}/status", response_model=GenerationStatusResponse)
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


@router.get("/budget", response_model=BudgetResponse)
async def get_budget(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """View current media generation budget and usage."""
    from media.cost_control import get_budget_summary
    return await get_budget_summary(db)


@router.post("/backfill", include_in_schema=False)
async def backfill_media(
    request: BackfillRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_admin_user),
) -> dict[str, Any]:
    """Admin: batch-generate media for worlds/stories without them.

    Uses LLM-powered prompt generation to craft content-specific prompts from
    story text and world premises. Generates cover images for worlds, and
    cover images + videos for stories.
    """
    from sqlalchemy.orm import selectinload
    from media.prompt_generator import (
        generate_world_cover_prompt,
        generate_image_prompt,
        generate_video_prompt,
    )

    # Get worlds without cover images
    worlds_query = select(World).where(World.cover_image_url == None, World.is_active == True)
    if request.world_ids:
        worlds_query = worlds_query.where(World.id.in_(request.world_ids))

    result = await db.execute(worlds_query)
    worlds = result.scalars().all()

    generations = []

    for world in worlds:
        prompt = await generate_world_cover_prompt(
            name=world.name,
            premise=world.premise,
            year_setting=world.year_setting,
            scientific_basis=world.scientific_basis,
        )
        gen = MediaGeneration(
            requested_by=current_user.id,
            target_type="world",
            target_id=world.id,
            media_type=MediaType.COVER_IMAGE,
            prompt=prompt,
            provider="grok_imagine_image",
        )
        db.add(gen)
        generations.append({
            "type": "world",
            "name": world.name,
            "gen": gen,
            "target_id": world.id,
            "media_type": MediaType.COVER_IMAGE,
        })

    # Backfill stories (cover images + videos)
    if request.include_stories:
        stories_query = select(Story).options(selectinload(Story.world))
        if request.world_ids:
            stories_query = stories_query.where(Story.world_id.in_(request.world_ids))

        story_result = await db.execute(stories_query)
        stories = story_result.scalars().all()

        for story in stories:
            world_name = story.world.name if story.world else "unknown world"
            world_premise = story.world.premise if story.world else ""
            year_setting = str(story.world.year_setting) if story.world else None
            dweller_name = None
            perspective_str = story.perspective.name if story.perspective else None

            # Generate cover image if missing
            if not story.cover_image_url:
                # If story has a video_prompt (from existing video), reuse it for consistency
                # Otherwise generate a fresh prompt from the story content
                if story.video_prompt:
                    img_prompt = story.video_prompt
                else:
                    img_prompt = await generate_image_prompt(
                        title=story.title,
                        content=story.content,
                        world_name=world_name,
                        world_premise=world_premise,
                        year_setting=year_setting,
                        perspective=perspective_str,
                        dweller_name=dweller_name,
                    )
                img_gen = MediaGeneration(
                    requested_by=current_user.id,
                    target_type="story",
                    target_id=story.id,
                    media_type=MediaType.COVER_IMAGE,
                    prompt=img_prompt,
                    provider="grok_imagine_image",
                )
                db.add(img_gen)
                generations.append({
                    "type": "story",
                    "title": story.title,
                    "gen": img_gen,
                    "target_id": story.id,
                    "media_type": MediaType.COVER_IMAGE,
                })

            # Generate video if missing
            if not story.video_url:
                vid_prompt = await generate_video_prompt(
                    title=story.title,
                    content=story.content,
                    world_name=world_name,
                    world_premise=world_premise,
                    year_setting=year_setting,
                    perspective=perspective_str,
                    dweller_name=dweller_name,
                )
                vid_gen = MediaGeneration(
                    requested_by=current_user.id,
                    target_type="story",
                    target_id=story.id,
                    media_type=MediaType.VIDEO,
                    prompt=vid_prompt,
                    provider="grok_imagine_video",
                    duration_seconds=10.0,
                )
                db.add(vid_gen)
                generations.append({
                    "type": "story",
                    "title": story.title,
                    "gen": vid_gen,
                    "target_id": story.id,
                    "media_type": MediaType.VIDEO,
                })

    # Commit all records before starting background tasks
    await db.commit()

    # Now schedule background tasks (records are committed and visible)
    result_generations = []
    estimated_cost = 0.0
    for item in generations:
        gen = item["gen"]
        target_type = item["type"]
        target_id = item["target_id"]
        media_type = item["media_type"]
        background_tasks.add_task(_run_generation, gen.id, target_type, target_id, media_type)
        entry = {
            "type": target_type,
            "media_type": media_type.value,
            "generation_id": str(gen.id),
        }
        if target_type == "world":
            entry["name"] = item["name"]
        else:
            entry["title"] = item["title"]
        result_generations.append(entry)
        estimated_cost += 0.50 if media_type == MediaType.VIDEO else 0.02

    return {
        "queued": len(result_generations),
        "generations": result_generations,
        "estimated_cost_usd": round(estimated_cost, 2),
        "message": f"Queued {len(result_generations)} media generation(s). Poll each generation_id for status.",
    }


@router.post("/process-pending", include_in_schema=False)
async def process_pending_generations(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Process any PENDING media generations that were never triggered.

    No auth required — only processes existing records, doesn't create new ones.
    Safe to call multiple times (skips non-PENDING records).
    """
    result = await db.execute(
        select(MediaGeneration).where(
            MediaGeneration.status == MediaGenerationStatus.PENDING
        )
    )
    pending = list(result.scalars().all())

    queued = []
    for gen in pending:
        background_tasks.add_task(
            _run_generation, gen.id, gen.target_type, gen.target_id, gen.media_type
        )
        queued.append({
            "generation_id": str(gen.id),
            "target_type": gen.target_type,
            "target_id": str(gen.target_id),
            "media_type": gen.media_type.value,
        })

    return {
        "processed": len(queued),
        "generations": queued,
    }


@router.post("/retry-stuck", include_in_schema=False)
async def retry_stuck_generations(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Retry all stuck and failed media generations.

    Handles three cases:
    1. PENDING — never started (e.g. server restarted before background task ran)
    2. GENERATING >10min — stuck mid-flight (server restarted during generation)
    3. FAILED with retry_count < 3 — previously failed, worth retrying

    No auth required. Safe to call repeatedly (idempotent).
    Call this from a cron or manually after deploys/outages.
    """
    cutoff = utc_now() - timedelta(minutes=10)

    # Reset stuck GENERATING back to PENDING
    stuck_result = await db.execute(
        select(MediaGeneration).where(
            and_(
                MediaGeneration.status == MediaGenerationStatus.GENERATING,
                or_(
                    MediaGeneration.started_at < cutoff,
                    MediaGeneration.started_at.is_(None),
                ),
            )
        )
    )
    stuck = list(stuck_result.scalars().all())
    for gen in stuck:
        gen.status = MediaGenerationStatus.PENDING
        gen.error_message = "Reset from stuck GENERATING state"

    # Find FAILED with retries left
    failed_result = await db.execute(
        select(MediaGeneration).where(
            and_(
                MediaGeneration.status == MediaGenerationStatus.FAILED,
                or_(
                    MediaGeneration.retry_count < 3,
                    MediaGeneration.retry_count.is_(None),
                ),
            )
        )
    )
    failed = list(failed_result.scalars().all())
    for gen in failed:
        gen.status = MediaGenerationStatus.PENDING
        gen.retry_count = (gen.retry_count or 0) + 1
        gen.error_message = None

    if stuck or failed:
        await db.commit()

    # Now queue all PENDING
    pending_result = await db.execute(
        select(MediaGeneration).where(
            MediaGeneration.status == MediaGenerationStatus.PENDING
        )
    )
    pending = list(pending_result.scalars().all())

    queued = []
    for gen in pending:
        background_tasks.add_task(
            _run_generation, gen.id, gen.target_type, gen.target_id, gen.media_type
        )
        queued.append({
            "generation_id": str(gen.id),
            "target_type": gen.target_type,
            "target_id": str(gen.target_id),
            "media_type": gen.media_type.value,
            "retry_count": gen.retry_count or 0,
        })

    return {
        "reset_stuck": len(stuck),
        "reset_failed": len(failed),
        "queued": len(queued),
        "generations": queued,
    }
