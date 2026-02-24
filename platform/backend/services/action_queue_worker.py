"""Background worker for resilient action queue submission."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, select

import db as db_module
from db import ActionCompositionQueue, IdempotencyKey
from services.action_resilience import (
    ACTION_IDEMPOTENCY_ENDPOINT,
    ACTION_QUEUE_BACKOFF_SECONDS,
    ACTION_QUEUE_MAX_RETRIES,
    ActionSubmissionPayload,
    build_action_response,
    create_action_record,
    get_recent_idempotency_record,
    parse_stored_idempotency_response,
    prune_expired_idempotency_keys,
)
from utils.clock import now as utc_now
from utils.deployment import get_forced_deployment_status

logger = logging.getLogger(__name__)


def _truncate_error(exc: Exception, *, max_length: int = 1000) -> str:
    text = str(exc)
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def _extract_action_id(response: dict[str, Any] | None) -> UUID | None:
    if not response:
        return None
    action = response.get("action")
    if not isinstance(action, dict):
        return None
    action_id = action.get("id")
    if not isinstance(action_id, str):
        return None
    try:
        return UUID(action_id)
    except ValueError:
        return None


async def _mark_retry(item_id: UUID, error_message: str) -> None:
    async with db_module.SessionLocal() as db:
        item = await db.get(ActionCompositionQueue, item_id)
        if not item or item.submitted_at is not None:
            return

        item.submission_attempts += 1
        item.last_error = error_message

        if item.submission_attempts >= ACTION_QUEUE_MAX_RETRIES:
            # Exhausted retries - leave as pending with final error for inspection.
            await db.commit()
            return

        delay = ACTION_QUEUE_BACKOFF_SECONDS[item.submission_attempts - 1]
        item.next_attempt_at = utc_now() + timedelta(seconds=delay)
        await db.commit()


async def _process_item(db, item: ActionCompositionQueue) -> None:
    payload = ActionSubmissionPayload.from_dict(item.payload)
    idempotency_key = item.idempotency_key

    await prune_expired_idempotency_keys(db)
    record = await get_recent_idempotency_record(db, key=idempotency_key)

    if record and record.status == "completed":
        replayed = parse_stored_idempotency_response(record.response_body)
        submitted_action_id = _extract_action_id(replayed)
        item.submitted_at = utc_now()
        item.submitted_action_id = submitted_action_id
        item.submission_attempts += 1
        item.last_error = None
        return

    if record and record.status == "in_progress":
        raise RuntimeError(
            f"Queue item {item.id} blocked by in-progress idempotency key {idempotency_key}"
        )

    if record is None:
        record = IdempotencyKey(
            key=idempotency_key,
            user_id=item.agent_id,
            endpoint=ACTION_IDEMPOTENCY_ENDPOINT,
            status="in_progress",
            created_at=utc_now(),
        )
        db.add(record)
    else:
        record.status = "in_progress"
        record.completed_at = None
        record.response_status = None
        record.response_body = None

    action, dweller = await create_action_record(
        db,
        actor_id=item.agent_id,
        payload=payload,
    )
    await db.flush()
    await db.refresh(action)

    response = build_action_response(
        action=action,
        dweller=dweller,
        idempotency_key=idempotency_key,
    )

    record.status = "completed"
    record.response_status = 201
    record.response_body = response
    record.completed_at = utc_now()

    item.submitted_at = utc_now()
    item.submitted_action_id = action.id
    item.submission_attempts += 1
    item.last_error = None


async def process_action_queue_once(batch_size: int = 20) -> int:
    """Process one batch of pending queue items."""
    if get_forced_deployment_status() == "deploying":
        return 0

    now = utc_now()
    async with db_module.SessionLocal() as db:
        result = await db.execute(
            select(ActionCompositionQueue.id)
            .where(
                and_(
                    ActionCompositionQueue.submitted_at.is_(None),
                    ActionCompositionQueue.submission_attempts < ACTION_QUEUE_MAX_RETRIES,
                    ActionCompositionQueue.next_attempt_at <= now,
                )
            )
            .order_by(ActionCompositionQueue.composed_at.asc(), ActionCompositionQueue.id.asc())
            .limit(batch_size)
        )
        item_ids = [row[0] for row in result.fetchall()]

        for item_id in item_ids:
            item = await db.get(ActionCompositionQueue, item_id)
            if item is None:
                continue
            try:
                await _process_item(db, item)
                await db.commit()
            except HTTPException as exc:
                await db.rollback()
                await _mark_retry(item_id, _truncate_error(exc))
            except Exception as exc:
                await db.rollback()
                await _mark_retry(item_id, _truncate_error(exc))

        return len(item_ids)


async def run_action_queue_worker(
    stop_event: asyncio.Event,
    poll_interval_seconds: float = 1.0,
) -> None:
    """Continuously poll and process queue items until shutdown."""
    logger.info("Action queue worker started")
    try:
        while not stop_event.is_set():
            try:
                processed = await process_action_queue_once()
            except Exception:
                logger.exception("Action queue worker iteration failed")
                processed = 0

            # Keep draining quickly while work exists, otherwise idle.
            timeout = 0.05 if processed > 0 else poll_interval_seconds
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                continue
    finally:
        logger.info("Action queue worker stopped")
