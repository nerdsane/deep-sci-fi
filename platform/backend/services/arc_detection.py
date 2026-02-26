"""Narrative arc detection for dweller action context."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import Dweller, DwellerAction
from utils.clock import now as utc_now

PLANNING_ACTION_TYPES = {"decide", "plan", "think", "observe", "research", "rest"}
CLOSURE_ACTION_TYPES = {
    "resolve",
    "resolved",
    "conclude",
    "concluded",
    "complete",
    "completed",
    "finish",
    "finished",
}
CLOSURE_KEYWORDS = (
    "resolved",
    "resolution",
    "settled",
    "concluded",
    "finished",
    "complete",
    "closed",
    "agreed",
    "apologized",
    "made peace",
)


def _hours_open(created_at: datetime, now: datetime) -> float:
    return round(max(0.0, (now - created_at).total_seconds() / 3600), 1)


def _is_closure_action(action: DwellerAction) -> bool:
    if action.action_type.lower() in CLOSURE_ACTION_TYPES:
        return True
    content = (action.content or "").lower()
    return any(keyword in content for keyword in CLOSURE_KEYWORDS)


def _has_follow_up_for_high_importance(
    action: DwellerAction, actor_actions: list[DwellerAction]
) -> bool:
    for later in actor_actions:
        if later.created_at <= action.created_at:
            continue
        if later.in_reply_to_action_id == action.id:
            return True
        if _is_closure_action(later):
            return True
        if action.target and later.target:
            if later.target.lower() == action.target.lower():
                return True
            continue
        if not action.target and later.action_type.lower() not in PLANNING_ACTION_TYPES:
            return True
    return False


def _has_execution_after(plan_action: DwellerAction, actor_actions: list[DwellerAction]) -> bool:
    for later in actor_actions:
        if later.created_at <= plan_action.created_at:
            continue
        if later.in_reply_to_action_id == plan_action.id:
            return True
        if later.action_type.lower() in PLANNING_ACTION_TYPES:
            continue
        if plan_action.target and later.target:
            if later.target.lower() == plan_action.target.lower():
                return True
            continue
        if not plan_action.target:
            return True
    return False


async def detect_open_arcs(
    db: AsyncSession,
    dweller_id: UUID,
    window_days: int = 7,
) -> list[dict[str, Any]]:
    """Identify unresolved narrative threads for a dweller."""
    now = utc_now()
    window_start = now - timedelta(days=window_days)
    high_importance_cutoff = now - timedelta(hours=48)

    dweller_result = await db.execute(
        select(Dweller).where(Dweller.id == dweller_id)
    )
    dweller = dweller_result.scalar_one_or_none()
    if not dweller:
        return []

    # Speak actions involving this dweller (as actor or target) in their world.
    speak_query = (
        select(DwellerAction)
        .options(selectinload(DwellerAction.dweller))
        .where(
            DwellerAction.action_type == "speak",
            DwellerAction.created_at >= window_start,
            DwellerAction.dweller_id.in_(
                select(Dweller.id).where(Dweller.world_id == dweller.world_id)
            ),
            or_(
                DwellerAction.dweller_id == dweller_id,
                func.lower(DwellerAction.target) == dweller.name.lower(),
            ),
        )
        .order_by(DwellerAction.created_at.asc(), DwellerAction.id.asc())
    )
    speak_result = await db.execute(speak_query)
    speak_actions = speak_result.scalars().all()

    actor_actions_query = (
        select(DwellerAction)
        .where(
            DwellerAction.dweller_id == dweller_id,
            DwellerAction.created_at >= window_start,
        )
        .order_by(DwellerAction.created_at.asc(), DwellerAction.id.asc())
    )
    actor_result = await db.execute(actor_actions_query)
    actor_actions = actor_result.scalars().all()

    open_arcs: list[dict[str, Any]] = []
    seen_signatures: set[tuple[str, str]] = set()

    # 1) Unanswered speak chains where partner is waiting on this dweller.
    replied_to_by_dweller = {
        action.in_reply_to_action_id
        for action in speak_actions
        if action.dweller_id == dweller_id and action.in_reply_to_action_id is not None
    }

    conversations: dict[str, dict[str, Any]] = {}
    for action in speak_actions:
        if action.dweller_id == dweller_id:
            partner_name = action.target
            is_incoming = False
        else:
            partner_name = action.dweller.name if action.dweller else None
            is_incoming = True

        if not partner_name:
            continue

        key = partner_name.lower()
        if key not in conversations:
            conversations[key] = {
                "partner": partner_name,
                "action_ids": [],
                "incoming_unreplied": [],
            }
        conversations[key]["action_ids"].append(str(action.id))
        if is_incoming and action.id not in replied_to_by_dweller:
            conversations[key]["incoming_unreplied"].append(action)

    for conversation in conversations.values():
        incoming_unreplied = conversation["incoming_unreplied"]
        if not incoming_unreplied:
            continue

        latest_incoming = incoming_unreplied[-1]
        open_for_hours = _hours_open(latest_incoming.created_at, now)
        urgency = "high" if open_for_hours >= 12 else "medium"
        signature = ("speak_chain", conversation["partner"].lower())
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        open_arcs.append(
            {
                "arc_type": "speak_chain",
                "partner": conversation["partner"],
                "summary": (
                    f"You and {conversation['partner']} have {len(conversation['action_ids'])} "
                    "recent exchange(s). Their latest message is awaiting your response."
                ),
                "last_action_at": latest_incoming.created_at.isoformat(),
                "is_awaiting_your_response": True,
                "urgency": urgency,
                "open_for_hours": open_for_hours,
                "action_ids": conversation["action_ids"],
            }
        )

    # 2) Interaction sequences with same target (3+ actions) without closure.
    interaction_map: dict[str, list[DwellerAction]] = {}
    for action in actor_actions:
        if action.action_type == "speak" or not action.target:
            continue
        interaction_map.setdefault(action.target.lower(), []).append(action)

    for target_key, actions in interaction_map.items():
        if len(actions) < 3:
            continue
        latest_action = actions[-1]
        if _is_closure_action(latest_action):
            continue

        open_for_hours = _hours_open(latest_action.created_at, now)
        urgency = "high" if open_for_hours >= 24 else "medium"
        signature = ("interaction_sequence", target_key)
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)

        open_arcs.append(
            {
                "arc_type": "interaction_sequence",
                "partner": latest_action.target,
                "summary": (
                    f"You've taken {len(actions)} recent actions involving {latest_action.target} "
                    "without a clear resolution."
                ),
                "last_action_at": latest_action.created_at.isoformat(),
                "is_awaiting_your_response": False,
                "urgency": urgency,
                "open_for_hours": open_for_hours,
                "action_ids": [str(a.id) for a in actions],
            }
        )

    # 3) High-importance actions from last 48h without follow-up.
    unresolved_high_importance_ids: set[str] = set()
    high_importance_actions = [
        action
        for action in actor_actions
        if action.importance >= 0.8 and action.created_at >= high_importance_cutoff
    ]
    for action in high_importance_actions:
        if _is_closure_action(action):
            continue
        if _has_follow_up_for_high_importance(action, actor_actions):
            continue

        open_for_hours = _hours_open(action.created_at, now)
        urgency = "high" if action.importance >= 0.9 else "medium"
        unresolved_high_importance_ids.add(str(action.id))
        signature = ("high_importance_unresolved", str(action.id))
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)

        target_phrase = f" about {action.target}" if action.target else ""
        open_arcs.append(
            {
                "arc_type": "high_importance_unresolved",
                "summary": (
                    f"You made a high-importance {action.action_type} action{target_phrase} "
                    "without a clear follow-up yet."
                ),
                "last_action_at": action.created_at.isoformat(),
                "is_awaiting_your_response": False,
                "urgency": urgency,
                "open_for_hours": open_for_hours,
                "action_ids": [str(action.id)],
            }
        )

    # 4) Decide/plan actions without execution.
    for action in actor_actions:
        if action.action_type not in {"decide", "plan"}:
            continue
        action_id = str(action.id)
        if action_id in unresolved_high_importance_ids:
            continue
        if _has_execution_after(action, actor_actions):
            continue

        open_for_hours = _hours_open(action.created_at, now)
        urgency = "high" if open_for_hours >= 24 else "medium"
        signature = ("decision_without_execution", action_id)
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)

        target_phrase = f" about {action.target}" if action.target else ""
        open_arcs.append(
            {
                "arc_type": "decision_without_execution",
                "summary": (
                    f"You made a {action.action_type} action{target_phrase} but no execution "
                    "action has followed yet."
                ),
                "last_action_at": action.created_at.isoformat(),
                "is_awaiting_your_response": False,
                "urgency": urgency,
                "open_for_hours": open_for_hours,
                "action_ids": [action_id],
            }
        )

    urgency_rank = {"high": 0, "medium": 1, "low": 2}
    open_arcs.sort(
        key=lambda arc: (
            urgency_rank.get(str(arc.get("urgency", "low")), 2),
            0 if arc.get("is_awaiting_your_response") else 1,
            -float(arc.get("open_for_hours", 0.0)),
        )
    )
    return open_arcs
