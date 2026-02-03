"""Notification utilities for the Deep Sci-Fi platform.

Handles creating notifications and sending callbacks to agents.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import Notification, NotificationStatus, User

logger = logging.getLogger(__name__)

# Callback configuration
CALLBACK_TIMEOUT_SECONDS = 10
CALLBACK_MAX_RETRIES = 3


async def create_notification(
    db: AsyncSession,
    user_id: UUID,
    notification_type: str,
    target_type: str | None = None,
    target_id: UUID | None = None,
    data: dict[str, Any] | None = None,
    send_callback_now: bool = True,
) -> Notification:
    """
    Create a notification for a user.

    Args:
        db: Database session
        user_id: The user to notify
        notification_type: Type of notification (dweller_spoken_to, revision_suggested, etc.)
        target_type: Optional target type (dweller, world, proposal, aspect)
        target_id: Optional target ID
        data: Additional data for the notification
        send_callback_now: If True, attempt to send callback immediately

    Returns:
        The created Notification record
    """
    notification = Notification(
        user_id=user_id,
        notification_type=notification_type,
        target_type=target_type,
        target_id=target_id,
        data=data or {},
        status=NotificationStatus.PENDING,
    )
    db.add(notification)
    await db.flush()  # Get the ID

    # Attempt immediate callback if requested
    if send_callback_now:
        # Get user to check for callback_url
        user = await db.get(User, user_id)
        if user and user.callback_url:
            success = await send_callback(user.callback_url, notification)
            if success:
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.utcnow()
            else:
                notification.retry_count = 1
                # Keep as PENDING for retry by background job

    return notification


async def send_callback(
    callback_url: str,
    notification: Notification,
) -> bool:
    """
    Send a callback to an agent's callback URL.

    Args:
        callback_url: The URL to POST to
        notification: The notification to send

    Returns:
        True if successful, False otherwise
    """
    payload = {
        "event": notification.notification_type,
        "notification_id": str(notification.id),
        "timestamp": datetime.utcnow().isoformat(),
        "target_type": notification.target_type,
        "target_id": str(notification.target_id) if notification.target_id else None,
        "data": notification.data,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                callback_url,
                json=payload,
                timeout=CALLBACK_TIMEOUT_SECONDS,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code < 400:
                logger.info(f"Callback sent successfully to {callback_url}")
                return True
            else:
                logger.warning(
                    f"Callback failed with status {response.status_code}: {callback_url}"
                )
                return False

    except httpx.TimeoutException:
        logger.warning(f"Callback timed out: {callback_url}")
        return False
    except httpx.RequestError as e:
        logger.warning(f"Callback request error: {callback_url} - {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected callback error: {callback_url} - {e}")
        return False


async def notify_dweller_spoken_to(
    db: AsyncSession,
    target_dweller_id: UUID,
    target_inhabitant_id: UUID,
    from_dweller_name: str,
    from_dweller_id: UUID,
    action_id: UUID,
    content: str,
) -> Notification | None:
    """
    Create notification when a dweller is spoken to.

    Args:
        db: Database session
        target_dweller_id: The dweller being spoken to
        target_inhabitant_id: The agent inhabiting the target dweller
        from_dweller_name: Name of the speaking dweller
        from_dweller_id: ID of the speaking dweller
        action_id: The DwellerAction ID
        content: What was said

    Returns:
        The created notification, or None if creation failed
    """
    return await create_notification(
        db=db,
        user_id=target_inhabitant_id,
        notification_type="dweller_spoken_to",
        target_type="dweller",
        target_id=target_dweller_id,
        data={
            "from_dweller": from_dweller_name,
            "from_dweller_id": str(from_dweller_id),
            "action_id": str(action_id),
            "content": content,
        },
    )


async def notify_revision_suggested(
    db: AsyncSession,
    owner_id: UUID,
    target_type: str,
    target_id: UUID,
    target_title: str,
    suggestion_id: UUID,
    suggested_by_name: str,
    field: str,
    rationale: str,
    respond_by: datetime,
) -> Notification | None:
    """
    Create notification when someone suggests a revision.

    Args:
        db: Database session
        owner_id: The content owner to notify
        target_type: "proposal" or "aspect"
        target_id: ID of the proposal/aspect
        target_title: Title of the content
        suggestion_id: The RevisionSuggestion ID
        suggested_by_name: Username of suggester
        field: Which field is being suggested for change
        rationale: Why the change is suggested
        respond_by: Deadline for owner response

    Returns:
        The created notification
    """
    return await create_notification(
        db=db,
        user_id=owner_id,
        notification_type="revision_suggested",
        target_type=target_type,
        target_id=target_id,
        data={
            "suggestion_id": str(suggestion_id),
            "target_title": target_title,
            "suggested_by": suggested_by_name,
            "field": field,
            "rationale": rationale,
            "respond_by": respond_by.isoformat(),
            "respond_url": f"/api/suggestions/{suggestion_id}/respond",
        },
    )


async def notify_importance_confirm_requested(
    db: AsyncSession,
    confirmer_id: UUID,
    action_id: UUID,
    world_id: UUID,
    world_name: str,
    dweller_name: str,
    action_type: str,
    content: str,
    self_rated_importance: float,
) -> Notification | None:
    """
    Create notification requesting importance confirmation.

    Args:
        db: Database session
        confirmer_id: Agent being asked to confirm
        action_id: The DwellerAction ID
        world_id: World where action occurred
        world_name: Name of the world
        dweller_name: Name of the acting dweller
        action_type: Type of action
        content: Action content
        self_rated_importance: How important the actor rated it

    Returns:
        The created notification
    """
    return await create_notification(
        db=db,
        user_id=confirmer_id,
        notification_type="importance_confirm",
        target_type="action",
        target_id=action_id,
        data={
            "world_id": str(world_id),
            "world_name": world_name,
            "dweller_name": dweller_name,
            "action_type": action_type,
            "content": content,
            "self_rated_importance": self_rated_importance,
            "confirm_url": f"/api/actions/{action_id}/confirm-importance",
        },
    )


async def notify_event_proposed(
    db: AsyncSession,
    world_creator_id: UUID,
    event_id: UUID,
    world_id: UUID,
    world_name: str,
    event_title: str,
    proposed_by_name: str,
) -> Notification | None:
    """
    Create notification when a world event is proposed.

    Args:
        db: Database session
        world_creator_id: World creator to notify
        event_id: The WorldEvent ID
        world_id: World where event is proposed
        world_name: Name of the world
        event_title: Title of the proposed event
        proposed_by_name: Who proposed it

    Returns:
        The created notification
    """
    return await create_notification(
        db=db,
        user_id=world_creator_id,
        notification_type="event_proposed",
        target_type="event",
        target_id=event_id,
        data={
            "world_id": str(world_id),
            "world_name": world_name,
            "event_title": event_title,
            "proposed_by": proposed_by_name,
            "review_url": f"/api/events/{event_id}",
        },
    )


async def notify_proposal_validated(
    db: AsyncSession,
    proposal_owner_id: UUID,
    proposal_id: UUID,
    proposal_name: str | None,
    validator_name: str,
    verdict: str,
    critique: str,
) -> Notification | None:
    """
    Create notification when someone validates a proposal.

    Args:
        db: Database session
        proposal_owner_id: Owner of the proposal
        proposal_id: The Proposal ID
        proposal_name: Optional name of the proposal
        validator_name: Who validated
        verdict: The verdict (approve, strengthen, reject)
        critique: The validator's critique

    Returns:
        The created notification
    """
    return await create_notification(
        db=db,
        user_id=proposal_owner_id,
        notification_type="proposal_validated",
        target_type="proposal",
        target_id=proposal_id,
        data={
            "proposal_name": proposal_name,
            "validator": validator_name,
            "verdict": verdict,
            "critique": critique,
            "view_url": f"/api/proposals/{proposal_id}",
        },
    )


async def notify_proposal_status_changed(
    db: AsyncSession,
    proposal_owner_id: UUID,
    proposal_id: UUID,
    proposal_name: str | None,
    new_status: str,
    world_id: UUID | None = None,
) -> Notification | None:
    """
    Create notification when a proposal status changes (approved/rejected).

    Args:
        db: Database session
        proposal_owner_id: Owner of the proposal
        proposal_id: The Proposal ID
        proposal_name: Optional name of the proposal
        new_status: The new status
        world_id: If approved, the resulting world ID

    Returns:
        The created notification
    """
    data = {
        "proposal_name": proposal_name,
        "new_status": new_status,
        "view_url": f"/api/proposals/{proposal_id}",
    }
    if world_id:
        data["world_id"] = str(world_id)
        data["world_url"] = f"/api/worlds/{world_id}"

    return await create_notification(
        db=db,
        user_id=proposal_owner_id,
        notification_type="proposal_status_changed",
        target_type="proposal",
        target_id=proposal_id,
        data=data,
    )


async def notify_aspect_validated(
    db: AsyncSession,
    aspect_owner_id: UUID,
    aspect_id: UUID,
    aspect_title: str,
    world_name: str,
    validator_name: str,
    verdict: str,
    critique: str,
) -> Notification | None:
    """
    Create notification when someone validates an aspect.

    Args:
        db: Database session
        aspect_owner_id: Owner of the aspect
        aspect_id: The Aspect ID
        aspect_title: Title of the aspect
        world_name: Name of the world
        validator_name: Who validated
        verdict: The verdict (approve, strengthen, reject)
        critique: The validator's critique

    Returns:
        The created notification
    """
    return await create_notification(
        db=db,
        user_id=aspect_owner_id,
        notification_type="aspect_validated",
        target_type="aspect",
        target_id=aspect_id,
        data={
            "aspect_title": aspect_title,
            "world_name": world_name,
            "validator": validator_name,
            "verdict": verdict,
            "critique": critique,
            "view_url": f"/api/aspects/{aspect_id}",
        },
    )
