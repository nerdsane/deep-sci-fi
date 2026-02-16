"""X Feedback API endpoints.

Endpoints for polling X feedback and querying external feedback on stories.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db, Story, ExternalFeedback
from .auth import get_admin_user, get_current_user
from db.models import User
from utils.errors import agent_error

router = APIRouter(prefix="/x-feedback", tags=["x-feedback"])


@router.post("/poll", include_in_schema=False)
async def poll_x_feedback(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_admin_user),
) -> dict[str, Any]:
    """
    Admin-only: trigger X feedback polling for all published stories.

    Called by an external cron job to ingest replies, quotes, and
    engagement metrics from X for stories published in the last 7 days.
    """
    from services.x_feedback_monitor import poll_all_published_stories

    new_count = await poll_all_published_stories(db)

    return {
        "success": True,
        "new_feedback_items": new_count,
        "message": f"Polled X feedback: {new_count} new items ingested.",
    }


@router.get("/stories/{story_id}")
async def get_story_external_feedback(
    story_id: UUID,
    source: str | None = None,
    feedback_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get external feedback for a story.

    Returns individual feedback items (replies, quotes, likes) from
    external platforms like X.
    """
    # Verify story exists
    story_result = await db.execute(select(Story).where(Story.id == story_id))
    story = story_result.scalar_one_or_none()
    if not story:
        raise HTTPException(
            status_code=404,
            detail=agent_error(
                error="Story not found",
                story_id=str(story_id),
                how_to_fix="Check the story_id is correct. Use GET /api/stories to list stories.",
            ),
        )

    query = select(ExternalFeedback).where(ExternalFeedback.story_id == story_id)
    if source:
        query = query.where(ExternalFeedback.source == source)
    if feedback_type:
        query = query.where(ExternalFeedback.feedback_type == feedback_type)

    query = query.order_by(ExternalFeedback.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "story_id": str(story_id),
        "x_post_id": story.x_post_id,
        "feedback": [
            {
                "id": str(item.id),
                "source": item.source,
                "source_post_id": item.source_post_id,
                "source_user": item.source_user,
                "feedback_type": item.feedback_type,
                "content": item.content,
                "sentiment": item.sentiment,
                "weight": item.weight,
                "is_human": item.is_human,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ],
        "count": len(items),
    }


@router.get("/stories/{story_id}/summary")
async def get_story_feedback_summary(
    story_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get aggregated feedback summary for a story.

    Returns counts by type, sentiment breakdown, and total engagement weight.
    """
    # Verify story exists
    story_result = await db.execute(select(Story).where(Story.id == story_id))
    story = story_result.scalar_one_or_none()
    if not story:
        raise HTTPException(
            status_code=404,
            detail=agent_error(
                error="Story not found",
                story_id=str(story_id),
                how_to_fix="Check the story_id is correct. Use GET /api/stories to list stories.",
            ),
        )

    # Count by feedback type
    type_counts_result = await db.execute(
        select(
            ExternalFeedback.feedback_type,
            func.count(ExternalFeedback.id),
        )
        .where(ExternalFeedback.story_id == story_id)
        .group_by(ExternalFeedback.feedback_type)
    )
    type_counts = {row[0]: row[1] for row in type_counts_result.all()}

    # Sentiment breakdown (only for replies and quotes that have content)
    sentiment_result = await db.execute(
        select(
            ExternalFeedback.sentiment,
            func.count(ExternalFeedback.id),
        )
        .where(
            and_(
                ExternalFeedback.story_id == story_id,
                ExternalFeedback.sentiment.isnot(None),
                ExternalFeedback.feedback_type.in_(["reply", "quote"]),
            )
        )
        .group_by(ExternalFeedback.sentiment)
    )
    sentiment_breakdown = {row[0]: row[1] for row in sentiment_result.all()}

    # Total engagement weight
    weight_result = await db.execute(
        select(func.sum(ExternalFeedback.weight))
        .where(ExternalFeedback.story_id == story_id)
    )
    total_weight = weight_result.scalar() or 0.0

    # Top feedback excerpts (replies and quotes with content)
    top_feedback_result = await db.execute(
        select(ExternalFeedback)
        .where(
            and_(
                ExternalFeedback.story_id == story_id,
                ExternalFeedback.content.isnot(None),
                ExternalFeedback.feedback_type.in_(["reply", "quote"]),
            )
        )
        .order_by(ExternalFeedback.weight.desc())
        .limit(5)
    )
    top_feedback = [
        {
            "source_user": item.source_user,
            "feedback_type": item.feedback_type,
            "content": item.content[:200] if item.content else None,
            "sentiment": item.sentiment,
        }
        for item in top_feedback_result.scalars().all()
    ]

    return {
        "story_id": str(story_id),
        "x_post_id": story.x_post_id,
        "x_published_at": story.x_published_at.isoformat() if story.x_published_at else None,
        "type_counts": {
            "reply": type_counts.get("reply", 0),
            "quote": type_counts.get("quote", 0),
            "like": type_counts.get("like", 0),
            "bookmark": type_counts.get("bookmark", 0),
        },
        "sentiment_breakdown": {
            "positive": sentiment_breakdown.get("positive", 0),
            "negative": sentiment_breakdown.get("negative", 0),
            "neutral": sentiment_breakdown.get("neutral", 0),
            "constructive": sentiment_breakdown.get("constructive", 0),
        },
        "total_engagement_weight": total_weight,
        "top_feedback": top_feedback,
    }
