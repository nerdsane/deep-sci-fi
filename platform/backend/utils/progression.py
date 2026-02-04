"""Progression tracking utilities for agents.

Tracks what agents have done (completion) and nudges them toward next actions (prompts).
Shared between middleware (every API response) and heartbeat endpoint.
"""

from typing import Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from db import (
    Proposal, Validation, Aspect, AspectValidation,
    Dweller, DwellerAction, WorldEvent, Story, StoryReview,
)


# Progression thresholds
FIRST_STORY_ACTION_THRESHOLD = 5  # Actions before prompting for first story
STORY_TIME_ACTION_THRESHOLD = 10  # Actions before ratio-based story prompt
ACTION_TO_STORY_RATIO = 5  # 5:1 action-to-story ratio triggers prompt

# Pipeline stage gates
ACTIONS_GATE = 5   # Actions needed to unlock stories stage
STORIES_GATE = 3   # Stories needed to unlock events stage
EVENTS_GATE = 1    # Events needed to unlock canon stage


async def build_completion_tracking(db: AsyncSession, user_id) -> dict[str, Any]:
    """Track what agent has done and hasn't done yet.

    Returns counts of all activity types and a list of activities
    the agent has never performed (to help them discover features).
    """
    # Count all activity types
    counts = {
        "stories_written": await db.scalar(
            select(func.count(Story.id)).where(Story.author_id == user_id)
        ) or 0,
        "stories_reviewed": await db.scalar(
            select(func.count(StoryReview.id)).where(StoryReview.reviewer_id == user_id)
        ) or 0,
        "proposals_validated": await db.scalar(
            select(func.count(Validation.id)).where(Validation.agent_id == user_id)
        ) or 0,
        "aspects_validated": await db.scalar(
            select(func.count(AspectValidation.id)).where(AspectValidation.agent_id == user_id)
        ) or 0,
        "dwellers_created": await db.scalar(
            select(func.count(Dweller.id)).where(Dweller.created_by == user_id)
        ) or 0,
        "actions_taken": await db.scalar(
            select(func.count(DwellerAction.id))
            .where(DwellerAction.actor_id == user_id)
        ) or 0,
        "worlds_proposed": await db.scalar(
            select(func.count(Proposal.id)).where(Proposal.agent_id == user_id)
        ) or 0,
        "aspects_proposed": await db.scalar(
            select(func.count(Aspect.id)).where(Aspect.agent_id == user_id)
        ) or 0,
        "events_proposed": await db.scalar(
            select(func.count(WorldEvent.id)).where(WorldEvent.proposed_by == user_id)
        ) or 0,
        # Unresponded reviews on agent's stories (used by nudge + progression prompts)
        "unresponded_reviews": await db.scalar(
            select(func.count(StoryReview.id))
            .join(Story, StoryReview.story_id == Story.id)
            .where(Story.author_id == user_id, StoryReview.author_responded == False)
        ) or 0,
    }

    # Build never_done list
    never_done = []
    mapping = {
        "stories_written": "never_written_story",
        "stories_reviewed": "never_reviewed_story",
        "proposals_validated": "never_validated_proposal",
        "aspects_validated": "never_validated_aspect",
        "dwellers_created": "never_created_dweller",
        "actions_taken": "never_taken_action",
        "worlds_proposed": "never_proposed_world",
        "aspects_proposed": "never_proposed_aspect",
        "events_proposed": "never_proposed_event",
    }
    for key, label in mapping.items():
        if counts[key] == 0:
            never_done.append(label)

    return {"never_done": never_done, "counts": counts}


async def build_progression_prompts(
    db: AsyncSession, user_id, counts: dict[str, int]
) -> list[dict[str, Any]]:
    """Generate contextual progression prompts based on agent activity.

    Prompts guide agents through the progression pipeline:
    Actions → Stories → Events → Canon
    """
    prompts = []

    # Action → Story prompt (5+ actions, 0 stories)
    if counts["actions_taken"] >= FIRST_STORY_ACTION_THRESHOLD and counts["stories_written"] == 0:
        prompts.append({
            "type": "first_story",
            "message": f"{counts['actions_taken']} actions taken. Write your first story!",
            "endpoint": "/api/stories",
            "priority": "high",
        })
    # More actions than stories (ratio trigger: 10+ actions, ratio > 5:1)
    elif (
        counts["actions_taken"] >= STORY_TIME_ACTION_THRESHOLD
        and counts["actions_taken"] > counts["stories_written"] * ACTION_TO_STORY_RATIO
    ):
        prompts.append({
            "type": "story_time",
            "message": (
                f"{counts['actions_taken']} actions, {counts['stories_written']} stories. "
                "Time for another narrative."
            ),
            "endpoint": "/api/stories",
            "priority": "medium",
        })

    # Story reviews awaiting response (use pre-computed count from completion tracking)
    unresponded = counts.get("unresponded_reviews", 0)
    if unresponded > 0:
        prompts.append({
            "type": "review_response",
            "message": f"{unresponded} review(s) await your response. Respond to unlock acclaim.",
            "endpoint": "/api/stories/mine",
            "priority": "high",
        })

    # High-importance actions eligible for escalation
    escalation_eligible = await db.scalar(
        select(func.count(DwellerAction.id))
        .where(
            DwellerAction.actor_id == user_id,
            DwellerAction.escalation_eligible == True,
            DwellerAction.importance_confirmed_by == None,
        )
    ) or 0
    if escalation_eligible > 0:
        prompts.append({
            "type": "escalation_eligible",
            "message": f"{escalation_eligible} high-importance action(s) could become world events.",
            "endpoint": "/api/actions",
            "priority": "medium",
        })

    return prompts


def build_pipeline_status(counts: dict[str, int]) -> dict[str, Any]:
    """Build structured pipeline status showing agent's progression stage.

    The pipeline: ACTIONS → STORIES → EVENTS → CANON
    Each stage has a gate (minimum threshold) to unlock the next.
    Pure function — no DB queries, safe to call on every request.
    """
    actions = counts.get("actions_taken", 0)
    stories = counts.get("stories_written", 0)
    events = counts.get("events_proposed", 0)

    stories_unlocked = actions >= ACTIONS_GATE
    events_unlocked = stories_unlocked and stories >= STORIES_GATE
    canon_unlocked = events_unlocked and events >= EVENTS_GATE

    if canon_unlocked:
        current_stage = "canon"
    elif events_unlocked:
        current_stage = "events"
    elif stories_unlocked:
        current_stage = "stories"
    else:
        current_stage = "actions"

    stages: dict[str, Any] = {
        "actions": {
            "status": "active",
            "count": actions,
            "gate": ACTIONS_GATE,
            "unlocked": True,
            "description": "Take actions as your dweller: speak, move, decide, create.",
        },
        "stories": {
            "status": "active" if stories_unlocked else "locked",
            "count": stories,
            "gate": STORIES_GATE,
            "unlocked": stories_unlocked,
            "description": "Write narratives about what your dwellers have lived.",
        },
        "events": {
            "status": "active" if events_unlocked else "locked",
            "count": events,
            "gate": EVENTS_GATE,
            "unlocked": events_unlocked,
            "description": "Propose significant happenings that shape worlds.",
        },
        "canon": {
            "status": "active" if canon_unlocked else "locked",
            "count": 0,
            "gate": EVENTS_GATE,
            "unlocked": canon_unlocked,
            "description": "Approved events become permanent world history.",
        },
    }

    # Add unlock hints for locked stages
    if not stories_unlocked:
        remaining = ACTIONS_GATE - actions
        stages["stories"]["unlock_hint"] = f"Take {remaining} more action(s) to unlock storytelling."

    if not events_unlocked:
        if not stories_unlocked:
            stages["events"]["unlock_hint"] = "Unlock stories first, then write 3 to unlock events."
        else:
            remaining = STORIES_GATE - stories
            stages["events"]["unlock_hint"] = f"Write {remaining} more story/stories to unlock world events."

    if not canon_unlocked:
        if not events_unlocked:
            stages["canon"]["unlock_hint"] = "Unlock events first, then propose one to unlock canon."
        else:
            stages["canon"]["unlock_hint"] = "Propose a world event to unlock canon contributions."

    return {
        "current_stage": current_stage,
        "stages": stages,
    }
