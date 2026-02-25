"""Admin-only endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db import GuidanceComplianceSignal, Story, StoryWritingGuidance, User, get_db
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


def _choose_top_rule(
    entries: list[dict[str, Any]],
    *,
    key: str,
) -> str | None:
    if not entries:
        return None
    ranked = sorted(entries, key=lambda item: item.get(key, 0), reverse=True)
    if not ranked or ranked[0].get(key, 0) <= 0:
        return None
    return str(ranked[0].get("rule_id"))


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


@router.get("/guidance/story-writing/analytics")
async def get_story_writing_guidance_analytics(
    version: str | None = Query(
        None,
        description="Guidance version to analyze. Defaults to active version if omitted.",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_admin_user),
) -> dict[str, Any]:
    """Return aggregate review-compliance analytics for a story writing guidance version."""
    selected_version = version
    guidance: StoryWritingGuidance | None = None

    if selected_version:
        guidance_result = await db.execute(
            select(StoryWritingGuidance).where(StoryWritingGuidance.version == selected_version)
        )
        guidance = guidance_result.scalar_one_or_none()
    else:
        guidance_result = await db.execute(
            select(StoryWritingGuidance)
            .order_by(desc(StoryWritingGuidance.is_active), desc(StoryWritingGuidance.created_at))
            .limit(1)
        )
        guidance = guidance_result.scalar_one_or_none()
        if guidance:
            selected_version = guidance.version

    if not selected_version:
        latest_signal_version = await db.scalar(
            select(GuidanceComplianceSignal.guidance_version)
            .order_by(desc(GuidanceComplianceSignal.created_at))
            .limit(1)
        )
        selected_version = latest_signal_version

    if not selected_version:
        raise HTTPException(
            status_code=404,
            detail=agent_error(
                error="No guidance analytics available",
                how_to_fix="Publish guidance and collect at least one reviewed story first.",
            ),
        )

    if not guidance:
        guidance_result = await db.execute(
            select(StoryWritingGuidance).where(StoryWritingGuidance.version == selected_version)
        )
        guidance = guidance_result.scalar_one_or_none()

    stories_written = await db.scalar(
        select(func.count(Story.id)).where(Story.guidance_version_used == selected_version)
    ) or 0

    signal_rows_result = await db.execute(
        select(GuidanceComplianceSignal)
        .where(GuidanceComplianceSignal.guidance_version == selected_version)
        .order_by(GuidanceComplianceSignal.created_at.asc())
    )
    signal_rows = signal_rows_result.scalars().all()

    reviewed_story_ids: set[UUID] = set()
    review_ids: set[UUID] = set()
    review_scores: list[float] = []
    rule_stats: dict[str, dict[str, Any]] = {}

    if guidance and isinstance(guidance.rules, list):
        for rule in guidance.rules:
            rule_id = str(rule.get("id") or "")
            if not rule_id:
                continue
            rule_stats[rule_id] = {
                "rule_id": rule_id,
                "rule_text": str(rule.get("text") or rule_id),
                "reviewer_mentions": 0,
                "positive_mentions": 0,
                "negative_mentions": 0,
            }

    for row in signal_rows:
        if row.story_id:
            reviewed_story_ids.add(row.story_id)
        if row.review_id:
            review_ids.add(row.review_id)

        signal_data = row.signal_data or {}
        score = signal_data.get("review_score")
        if isinstance(score, (int, float)):
            review_scores.append(float(score))

        for item in signal_data.get("rule_signals", []):
            rule_id = str(item.get("rule_id") or "")
            if not rule_id:
                continue
            stats = rule_stats.setdefault(
                rule_id,
                {
                    "rule_id": rule_id,
                    "rule_text": str(item.get("rule_text") or rule_id),
                    "reviewer_mentions": 0,
                    "positive_mentions": 0,
                    "negative_mentions": 0,
                },
            )
            if item.get("mentioned"):
                stats["reviewer_mentions"] += 1
            if item.get("positive"):
                stats["positive_mentions"] += 1
            if item.get("negative"):
                stats["negative_mentions"] += 1

    rule_entries = sorted(rule_stats.values(), key=lambda entry: entry["rule_id"])
    least_followed_rule = _choose_top_rule(rule_entries, key="negative_mentions")
    most_impactful_rule = _choose_top_rule(rule_entries, key="positive_mentions")

    return {
        "version": selected_version,
        "stories_written": stories_written,
        "reviewed_count": len(reviewed_story_ids),
        "review_count": len(review_ids),
        "avg_review_score": round(sum(review_scores) / len(review_scores), 2) if review_scores else 0.0,
        "rule_compliance_signals": rule_entries,
        "least_followed_rule": least_followed_rule,
        "most_impactful_rule": most_impactful_rule,
    }
