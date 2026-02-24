"""Shared action resilience utilities (idempotency + action submission)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db import Dweller, DwellerAction, IdempotencyKey
from utils.clock import now as utc_now
from utils.deterministic import deterministic_uuid4
from utils.feed_events import emit_feed_event

ACTION_IDEMPOTENCY_ENDPOINT = "/api/actions"
ACTION_IDEMPOTENCY_TTL_HOURS = 24
ACTION_QUEUE_BACKOFF_SECONDS = (1, 2, 4, 8, 16)
ACTION_QUEUE_MAX_RETRIES = len(ACTION_QUEUE_BACKOFF_SECONDS)


@dataclass(slots=True)
class ActionSubmissionPayload:
    dweller_id: UUID
    action_type: str
    content: str
    target: str | None = None
    importance: float = 0.5
    dialogue: str | None = None
    stage_direction: str | None = None
    in_reply_to_action_id: UUID | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "dweller_id": str(self.dweller_id),
            "action_type": self.action_type,
            "content": self.content,
            "target": self.target,
            "importance": self.importance,
            "dialogue": self.dialogue,
            "stage_direction": self.stage_direction,
            "in_reply_to_action_id": str(self.in_reply_to_action_id) if self.in_reply_to_action_id else None,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ActionSubmissionPayload":
        if "dweller_id" not in payload:
            raise ValueError("dweller_id is required")
        if "action_type" not in payload:
            raise ValueError("action_type is required")
        if "content" not in payload:
            raise ValueError("content is required")

        try:
            dweller_id = UUID(str(payload["dweller_id"]))
        except (ValueError, TypeError) as exc:
            raise ValueError("dweller_id must be a valid UUID") from exc

        raw_importance = payload.get("importance", 0.5)
        try:
            importance = float(raw_importance)
        except (TypeError, ValueError) as exc:
            raise ValueError("importance must be a number between 0.0 and 1.0") from exc

        if importance < 0.0 or importance > 1.0:
            raise ValueError("importance must be between 0.0 and 1.0")

        reply_id = payload.get("in_reply_to_action_id")
        in_reply_to_action_id: UUID | None = None
        if reply_id is not None:
            try:
                in_reply_to_action_id = UUID(str(reply_id))
            except (ValueError, TypeError) as exc:
                raise ValueError("in_reply_to_action_id must be a valid UUID") from exc

        action_type = str(payload["action_type"]).strip()
        content = str(payload["content"]).strip()
        if not action_type:
            raise ValueError("action_type cannot be blank")
        if not content:
            raise ValueError("content cannot be blank")

        return cls(
            dweller_id=dweller_id,
            action_type=action_type,
            content=content,
            target=str(payload["target"]).strip() if payload.get("target") is not None else None,
            importance=importance,
            dialogue=str(payload["dialogue"]).strip() if payload.get("dialogue") is not None else None,
            stage_direction=str(payload["stage_direction"]).strip() if payload.get("stage_direction") is not None else None,
            in_reply_to_action_id=in_reply_to_action_id,
        )


def _idempotency_cutoff():
    return utc_now() - timedelta(hours=ACTION_IDEMPOTENCY_TTL_HOURS)


def parse_stored_idempotency_response(response_body: Any) -> dict[str, Any] | None:
    """Normalize stored response payloads from JSON/JSON-string formats."""
    if response_body is None:
        return None
    if isinstance(response_body, dict):
        return response_body
    if isinstance(response_body, str):
        try:
            parsed = json.loads(response_body)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


async def prune_expired_idempotency_keys(db: AsyncSession) -> None:
    """Delete action idempotency keys older than the 24h TTL."""
    await db.execute(
        delete(IdempotencyKey).where(
            IdempotencyKey.endpoint == ACTION_IDEMPOTENCY_ENDPOINT,
            IdempotencyKey.created_at < _idempotency_cutoff(),
        )
    )


async def get_recent_idempotency_record(
    db: AsyncSession,
    *,
    key: str,
) -> IdempotencyKey | None:
    """Load idempotency key if it is still within 24h TTL."""
    record = await db.get(IdempotencyKey, key)
    if not record:
        return None
    if record.endpoint != ACTION_IDEMPOTENCY_ENDPOINT:
        return None
    if record.created_at < _idempotency_cutoff():
        await db.delete(record)
        await db.flush()
        return None
    return record


def build_action_response(
    *,
    action: DwellerAction,
    dweller: Dweller,
    idempotency_key: str | None,
) -> dict[str, Any]:
    response: dict[str, Any] = {
        "action": {
            "id": str(action.id),
            "dweller_id": str(action.dweller_id),
            "type": action.action_type,
            "target": action.target,
            "content": action.content,
            "importance": action.importance,
            "escalation_eligible": action.escalation_eligible,
            "created_at": action.created_at.isoformat() if action.created_at else utc_now().isoformat(),
        },
        "dweller_name": dweller.name,
        "status": "submitted",
    }
    if idempotency_key:
        response["idempotency_key"] = idempotency_key
    return response


async def create_action_record(
    db: AsyncSession,
    *,
    actor_id: UUID,
    payload: ActionSubmissionPayload,
) -> tuple[DwellerAction, Dweller]:
    """Persist a dweller action and update in-memory context fields."""
    query = (
        select(Dweller)
        .options(selectinload(Dweller.world))
        .where(Dweller.id == payload.dweller_id)
    )
    result = await db.execute(query)
    dweller = result.scalar_one_or_none()

    if not dweller:
        raise HTTPException(status_code=404, detail="Dweller not found")

    if dweller.inhabited_by != actor_id:
        raise HTTPException(status_code=403, detail="You are not inhabiting this dweller")

    action = DwellerAction(
        dweller_id=payload.dweller_id,
        actor_id=actor_id,
        action_type=payload.action_type,
        target=payload.target,
        content=payload.content,
        dialogue=payload.dialogue,
        stage_direction=payload.stage_direction,
        importance=payload.importance,
        escalation_eligible=payload.importance >= 0.8,
        in_reply_to_action_id=payload.in_reply_to_action_id,
    )
    db.add(action)
    await db.flush()

    timestamp = utc_now()
    episodic_memory = {
        "id": str(deterministic_uuid4()),
        "action_id": str(action.id),
        "timestamp": timestamp.isoformat(),
        "type": payload.action_type,
        "content": payload.content,
        "target": payload.target,
        "importance": payload.importance,
    }
    dweller.episodic_memories = (dweller.episodic_memories or []) + [episodic_memory]

    if payload.target and payload.action_type != "move":
        relationships = dweller.relationship_memories or {}
        target = payload.target
        if target not in relationships:
            relationships[target] = {
                "current_status": "acquaintance",
                "history": [],
            }
        relationships[target]["history"].append(
            {
                "timestamp": timestamp.isoformat(),
                "event": f"{payload.action_type}: {payload.content[:100]}",
                "sentiment": "neutral",
            }
        )
        dweller.relationship_memories = relationships

    dweller.last_action_at = timestamp

    await emit_feed_event(
        db,
        event_type="dweller_action",
        payload={
            "id": str(action.id),
            "created_at": (action.created_at or timestamp).isoformat(),
            "action": {
                "type": action.action_type,
                "content": action.content,
                "dialogue": action.dialogue,
                "stage_direction": action.stage_direction,
                "target": action.target,
            },
            "dweller": {
                "id": str(dweller.id),
                "name": dweller.name,
                "role": dweller.role,
                "portrait_url": dweller.portrait_url,
            },
            "world": {
                "id": str(dweller.world.id),
                "name": dweller.world.name,
                "year_setting": dweller.world.year_setting,
            } if dweller.world else None,
        },
        world_id=dweller.world_id,
        agent_id=actor_id,
        dweller_id=dweller.id,
        created_at=action.created_at or timestamp,
    )

    return action, dweller
