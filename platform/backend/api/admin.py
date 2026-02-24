"""Admin-only endpoints."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db import StoryWritingGuidance, User, get_db
from utils.clock import now as utc_now
from utils.errors import agent_error

from .auth import get_admin_user

router = APIRouter(prefix="/admin", tags=["admin"])


class StoryGuidanceRule(BaseModel):
    """Single rule entry for writing guidance."""

    id: str = Field(..., min_length=1, max_length=100)
    severity: str = Field(..., min_length=1, max_length=20)
    text: str = Field(..., min_length=1)


class StoryGuidanceExample(BaseModel):
    """Example entry for writing guidance."""

    title: str = Field(..., min_length=1, max_length=200)
    excerpt: str = Field(..., min_length=1)
    why: str = Field(..., min_length=1)


class PublishStoryGuidanceRequest(BaseModel):
    """Payload for publishing active story writing guidance."""

    version: str = Field(..., min_length=1, max_length=50)
    rules: list[StoryGuidanceRule] = Field(..., min_length=1)
    examples: list[StoryGuidanceExample] = Field(default_factory=list)
    expires_at: datetime | None = None


@router.post("/guidance/story-writing")
async def publish_story_writing_guidance(
    request: PublishStoryGuidanceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_admin_user),
) -> dict[str, Any]:
    """Publish or update active story writing guidance."""
    if request.expires_at and request.expires_at <= utc_now():
        raise HTTPException(
            status_code=400,
            detail=agent_error(
                error="expires_at must be in the future",
                how_to_fix="Provide a future UTC timestamp for expires_at, or omit it.",
            ),
        )

    await db.execute(
        update(StoryWritingGuidance)
        .where(
            StoryWritingGuidance.is_active.is_(True),
            StoryWritingGuidance.version != request.version,
        )
        .values(is_active=False)
    )

    existing_result = await db.execute(
        select(StoryWritingGuidance)
        .where(StoryWritingGuidance.version == request.version)
        .with_for_update()
    )
    guidance = existing_result.scalar_one_or_none()

    rules_payload = [rule.model_dump() for rule in request.rules]
    examples_payload = [example.model_dump() for example in request.examples]

    if guidance:
        guidance.rules = rules_payload
        guidance.examples = examples_payload
        guidance.expires_at = request.expires_at
        guidance.is_active = True
        guidance.created_by = current_user.username
    else:
        guidance = StoryWritingGuidance(
            version=request.version,
            rules=rules_payload,
            examples=examples_payload,
            expires_at=request.expires_at,
            is_active=True,
            created_by=current_user.username,
        )
        db.add(guidance)

    await db.flush()

    return {
        "success": True,
        "guidance": {
            "version": guidance.version,
            "rules": guidance.rules,
            "examples": guidance.examples or [],
            "expires_at": guidance.expires_at.isoformat() if guidance.expires_at else None,
            "is_active": guidance.is_active,
            "created_at": guidance.created_at.isoformat() if guidance.created_at else None,
            "created_by": guidance.created_by,
        },
    }
