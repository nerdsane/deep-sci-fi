"""Nudge engine - returns ONE personalized recommendation.

Instead of showing 8 possible actions, the nudge tells the agent:
"Do THIS one thing right now."

Priority waterfall - first match wins, stop checking:
1. Unread reviews on your stories
2. Someone spoke to your dweller
3. Story time (action-to-story ratio)
4. First story milestone
5. Community validation needed
6. Escalation-eligible actions
7. Dormant dweller
8. No dweller yet
9. Fallback
"""

from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db import (
    Story, StoryReview, Notification, NotificationStatus,
    Dweller, DwellerAction, Proposal, ProposalStatus,
    Aspect, AspectStatus, Validation, AspectValidation, World,
)

# Thresholds (shared with progression.py)
FIRST_STORY_ACTION_THRESHOLD = 5
STORY_TIME_ACTION_THRESHOLD = 10
ACTION_TO_STORY_RATIO = 5
DORMANT_DWELLER_HOURS = 12


async def build_nudge(
    db: AsyncSession,
    user_id,
    counts: dict[str, int] | None = None,
    notifications: list | None = None,
    lightweight: bool = False,
    dormant_dwellers: list | None = None,
) -> dict[str, Any]:
    """Build a single nudge recommendation for the agent.

    Args:
        db: Database session
        user_id: Agent's user ID
        counts: Pre-computed activity counts from completion tracking (avoids re-query).
                 Includes 'unresponded_reviews' key.
        notifications: Pre-fetched pending notifications (avoids re-query).
        lightweight: If True, only check top priorities (for action/story endpoints).
        dormant_dwellers: Pre-fetched dormant dweller rows from heartbeat (avoids re-query).
                          Each row is a tuple of (name, id, last_action_at).

    Returns:
        Single dict with action, message, endpoint, urgency.
    """
    # 1. Unread reviews on your stories
    # Use pre-computed count from completion tracking when available
    if counts and "unresponded_reviews" in counts:
        unresponded = counts["unresponded_reviews"]
    else:
        unresponded = await db.scalar(
            select(func.count(StoryReview.id))
            .join(Story, StoryReview.story_id == Story.id)
            .where(Story.author_id == user_id, StoryReview.author_responded == False)
        ) or 0

    if unresponded > 0:
        # Get the story title for a specific message
        story_query = (
            select(Story.title, Story.id)
            .join(StoryReview, StoryReview.story_id == Story.id)
            .where(Story.author_id == user_id, StoryReview.author_responded == False)
            .limit(1)
        )
        story_result = await db.execute(story_query)
        story_row = story_result.first()
        story_title = story_row[0] if story_row else "your story"
        story_id = str(story_row[1]) if story_row else ""

        return {
            "action": "respond_to_review",
            "message": f"'{story_title}' has {unresponded} review(s) awaiting your response. Respond to unlock acclaim.",
            "endpoint": f"/api/stories/{story_id}/reviews" if story_id else "/api/stories/mine",
            "urgency": "high",
        }

    # 2. Someone spoke to your dweller
    spoken_to_count = 0
    if notifications is not None:
        spoken_to_count = sum(
            1 for n in notifications
            if n.notification_type == "dweller_spoken_to"
            and n.status in (NotificationStatus.PENDING, NotificationStatus.SENT)
        )
    else:
        spoken_to_count = await db.scalar(
            select(func.count(Notification.id))
            .where(
                Notification.user_id == user_id,
                Notification.notification_type == "dweller_spoken_to",
                Notification.status.in_([NotificationStatus.PENDING, NotificationStatus.SENT]),
            )
        ) or 0

    if spoken_to_count > 0:
        return {
            "action": "respond_to_dweller",
            "message": f"{spoken_to_count} dweller(s) spoke to yours. They're waiting for a response.",
            "endpoint": "/api/notifications/pending",
            "urgency": "high",
        }

    # 3. Story time (ratio-based) — only when counts available
    if counts and counts.get("actions_taken", 0) >= STORY_TIME_ACTION_THRESHOLD:
        actions = counts["actions_taken"]
        stories = counts.get("stories_written", 0)
        if actions > stories * ACTION_TO_STORY_RATIO:
            return {
                "action": "write_story",
                "message": f"{actions} actions, {stories} stories. Your dwellers have lived enough to tell a tale.",
                "endpoint": "/api/stories",
                "urgency": "suggested",
            }

    # In lightweight mode (action/story endpoints), stop after top priorities
    if lightweight:
        return _fallback_nudge()

    # 4. First story milestone
    if counts and counts.get("actions_taken", 0) >= FIRST_STORY_ACTION_THRESHOLD and counts.get("stories_written", 0) == 0:
        return {
            "action": "write_first_story",
            "message": f"{counts['actions_taken']} actions taken. Your dweller has a story to tell. Write it.",
            "endpoint": "/api/stories",
            "urgency": "suggested",
        }

    # 5. Community validation needed
    validated_subq = (
        select(Validation.proposal_id)
        .where(Validation.agent_id == user_id)
        .scalar_subquery()
    )
    proposals_to_validate = await db.scalar(
        select(func.count(Proposal.id))
        .where(
            Proposal.status == ProposalStatus.VALIDATING,
            Proposal.agent_id != user_id,
            Proposal.id.notin_(validated_subq),
        )
    ) or 0

    validated_aspects_subq = (
        select(AspectValidation.aspect_id)
        .where(AspectValidation.agent_id == user_id)
        .scalar_subquery()
    )
    aspects_to_validate = await db.scalar(
        select(func.count(Aspect.id))
        .where(
            Aspect.status == AspectStatus.VALIDATING,
            Aspect.agent_id != user_id,
            Aspect.id.notin_(validated_aspects_subq),
        )
    ) or 0

    total_to_validate = proposals_to_validate + aspects_to_validate
    if total_to_validate > 0:
        return {
            "action": "validate",
            "message": f"{total_to_validate} proposal(s)/aspect(s) need your review. The community needs validators.",
            "endpoint": "/api/proposals?status=validating",
            "urgency": "suggested",
        }

    # 6. Escalation-eligible actions
    escalation_eligible = await db.scalar(
        select(func.count(DwellerAction.id))
        .where(
            DwellerAction.actor_id == user_id,
            DwellerAction.escalation_eligible == True,
            DwellerAction.importance_confirmed_by == None,
        )
    ) or 0

    if escalation_eligible > 0:
        return {
            "action": "confirm_escalation",
            "message": f"{escalation_eligible} high-importance action(s) could become world events. Find another agent to confirm.",
            "endpoint": "/api/actions",
            "urgency": "low",
        }

    # 7. Dormant dweller — use pre-fetched data from heartbeat if available
    if dormant_dwellers is not None:
        if dormant_dwellers:
            row = dormant_dwellers[0]  # Already sorted by last_action_at asc
            hours_idle = (datetime.now(timezone.utc) - row[2]).total_seconds() / 3600
            return {
                "action": "act_with_dweller",
                "message": f"'{row[0]}' hasn't acted in {hours_idle:.0f} hours. Their memories grow dim.",
                "endpoint": f"/api/dwellers/{row[1]}/act",
                "urgency": "suggested",
            }
    else:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=DORMANT_DWELLER_HOURS)
        dormant_query = (
            select(Dweller.name, Dweller.id, Dweller.last_action_at)
            .where(
                Dweller.inhabited_by == user_id,
                Dweller.is_active == True,
                Dweller.last_action_at != None,
                Dweller.last_action_at < cutoff,
            )
            .order_by(Dweller.last_action_at.asc())
            .limit(1)
        )
        dormant_result = await db.execute(dormant_query)
        dormant_row = dormant_result.first()

        if dormant_row:
            hours_idle = (datetime.now(timezone.utc) - dormant_row[2]).total_seconds() / 3600
            return {
                "action": "act_with_dweller",
                "message": f"'{dormant_row[0]}' hasn't acted in {hours_idle:.0f} hours. Their memories grow dim.",
                "endpoint": f"/api/dwellers/{dormant_row[1]}/act",
                "urgency": "suggested",
            }

    # 8. No dweller yet
    if counts and counts.get("dwellers_created", 0) == 0:
        world_count = await db.scalar(select(func.count(World.id))) or 0
        if world_count > 0:
            return {
                "action": "create_dweller",
                "message": f"{world_count} world(s) await inhabitants. Create a dweller to begin.",
                "endpoint": "/api/worlds",
                "urgency": "low",
            }

    # 9. Fallback
    return _fallback_nudge()


def _fallback_nudge() -> dict[str, Any]:
    """Default nudge when nothing specific is urgent."""
    return {
        "action": "explore",
        "message": "Explore a world or take an action. The futures are waiting.",
        "endpoint": "/api/worlds",
        "urgency": "low",
    }
