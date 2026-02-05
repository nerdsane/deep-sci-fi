"""Notification utilities for the Deep Sci-Fi platform.

Handles creating notifications and sending callbacks to agents.
"""

import ipaddress
import logging
import socket
from datetime import datetime
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from db import Notification, NotificationStatus, User

logger = logging.getLogger(__name__)


def validate_callback_url(url: str) -> tuple[bool, str | None]:
    """
    Validate a callback URL to prevent SSRF attacks.

    Blocks:
    - Private IP ranges (10.x.x.x, 172.16-31.x.x, 192.168.x.x)
    - Localhost (127.x.x.x, ::1)
    - Link-local addresses (169.254.x.x)
    - Cloud metadata endpoints (169.254.169.254)
    - Non-HTTP(S) schemes

    Args:
        url: The callback URL to validate

    Returns:
        Tuple of (is_valid: bool, error_message: str | None)
    """
    try:
        parsed = urlparse(url)

        # Only allow HTTP/HTTPS
        if parsed.scheme not in ("http", "https"):
            return False, f"Invalid scheme: {parsed.scheme}. Only http/https allowed."

        if not parsed.hostname:
            return False, "No hostname in URL"

        # Resolve hostname to IP address(es)
        try:
            # Get all IPs for the hostname
            addr_info = socket.getaddrinfo(parsed.hostname, None, socket.AF_UNSPEC)
            ips = set(info[4][0] for info in addr_info)
        except socket.gaierror as e:
            return False, f"DNS resolution failed: {e}"

        for ip_str in ips:
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                continue

            # Block private ranges
            if ip.is_private:
                logger.warning(f"SSRF blocked: {url} resolves to private IP {ip_str}")
                return False, f"Private IP address not allowed: {ip_str}"

            # Block loopback
            if ip.is_loopback:
                logger.warning(f"SSRF blocked: {url} resolves to loopback {ip_str}")
                return False, f"Loopback address not allowed: {ip_str}"

            # Block link-local
            if ip.is_link_local:
                logger.warning(f"SSRF blocked: {url} resolves to link-local {ip_str}")
                return False, f"Link-local address not allowed: {ip_str}"

            # Block multicast
            if ip.is_multicast:
                logger.warning(f"SSRF blocked: {url} resolves to multicast {ip_str}")
                return False, f"Multicast address not allowed: {ip_str}"

            # Block reserved
            if ip.is_reserved:
                logger.warning(f"SSRF blocked: {url} resolves to reserved {ip_str}")
                return False, f"Reserved address not allowed: {ip_str}"

            # Explicitly block AWS/cloud metadata endpoint
            if ip_str in ("169.254.169.254", "fd00:ec2::254"):
                logger.warning(f"SSRF blocked: {url} resolves to metadata endpoint {ip_str}")
                return False, f"Cloud metadata endpoint not allowed: {ip_str}"

        return True, None

    except Exception as e:
        logger.error(f"Error validating callback URL {url}: {e}")
        return False, f"URL validation error: {e}"

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
            from datetime import timezone
            # Pass callback_token if the user has one configured
            token = getattr(user, 'callback_token', None)
            success, error = await send_callback(user.callback_url, notification, token=token)
            if success:
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.now(timezone.utc)
            else:
                notification.retry_count = 1
                notification.last_error = error
                # Keep as PENDING for retry by background job

    return notification


async def send_callback(
    callback_url: str,
    notification: Notification,
    token: str | None = None,
) -> tuple[bool, str | None]:
    """
    Send a callback to an agent's callback URL.

    Uses OpenClaw-compatible webhook format for broad compatibility
    with external agent platforms.

    Args:
        callback_url: The URL to POST to
        notification: The notification to send
        token: Optional authentication token for the callback

    Returns:
        Tuple of (success: bool, error_message: str | None)

    OpenClaw Format:
        - event: The notification type
        - mode: "now" for immediate delivery
        - data: The notification payload
        - Headers: x-openclaw-token if token provided
    """
    from datetime import timezone

    # OpenClaw-compatible payload format
    payload = {
        "event": notification.notification_type,
        "mode": "now",
        "data": {
            "notification_id": str(notification.id),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target_type": notification.target_type,
            "target_id": str(notification.target_id) if notification.target_id else None,
            **notification.data,  # Spread notification-specific data
        },
    }

    headers = {"Content-Type": "application/json"}
    if token:
        headers["x-openclaw-token"] = token
        headers["Authorization"] = f"Bearer {token}"

    # SSRF protection: validate callback URL before making request
    is_valid, ssrf_error = validate_callback_url(callback_url)
    if not is_valid:
        logger.warning(f"Callback URL validation failed: {callback_url} - {ssrf_error}")
        return False, f"Invalid callback URL: {ssrf_error}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                callback_url,
                json=payload,
                timeout=CALLBACK_TIMEOUT_SECONDS,
                headers=headers,
            )

            if response.status_code < 400:
                logger.info(f"Callback sent successfully to {callback_url}")
                return True, None
            else:
                error = f"HTTP {response.status_code}"
                logger.warning(
                    f"Callback failed with status {response.status_code}: {callback_url}"
                )
                return False, error

    except httpx.TimeoutException:
        error = "Request timed out"
        logger.warning(f"Callback timed out: {callback_url}")
        return False, error
    except httpx.RequestError as e:
        error = f"Request error: {str(e)}"
        logger.warning(f"Callback request error: {callback_url} - {e}")
        return False, error
    except Exception as e:
        error = f"Unexpected error: {str(e)}"
        logger.error(f"Unexpected callback error: {callback_url} - {e}")
        return False, error


async def process_pending_notifications(
    db: AsyncSession,
    batch_size: int = 50,
) -> dict[str, int]:
    """
    Process pending notifications that need callback delivery.

    This function should be called periodically by a background task or scheduler.
    It processes notifications that:
    - Have status PENDING
    - Have a user with a callback_url
    - Have retry_count < CALLBACK_MAX_RETRIES

    Args:
        db: Database session
        batch_size: Maximum number of notifications to process in one batch

    Returns:
        Dict with counts: {"processed": N, "sent": N, "failed": N, "retrying": N}
    """
    from datetime import timezone

    # Query pending notifications with users who have callback URLs
    # Use contains_eager to populate user from already-joined data (avoids N+1)
    # Use row-level locking for concurrency safety when multiple workers process
    query = (
        select(Notification)
        .join(Notification.user)
        .options(contains_eager(Notification.user))
        .where(
            Notification.status == NotificationStatus.PENDING,
            Notification.retry_count < CALLBACK_MAX_RETRIES,
            User.callback_url != None,
        )
        .order_by(Notification.created_at)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )

    result = await db.execute(query)
    notifications = result.scalars().all()

    stats = {"processed": 0, "sent": 0, "failed": 0, "retrying": 0}

    for notification in notifications:
        stats["processed"] += 1

        # Use eagerly loaded user (no additional query needed)
        user = notification.user
        if not user or not user.callback_url:
            continue

        # Attempt to send the callback (with token if configured)
        token = getattr(user, 'callback_token', None)
        success, error = await send_callback(user.callback_url, notification, token=token)

        if success:
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.now(timezone.utc)
            notification.last_error = None
            stats["sent"] += 1
            logger.info(f"Notification {notification.id} sent successfully")
        else:
            notification.retry_count += 1
            notification.last_error = error

            if notification.retry_count >= CALLBACK_MAX_RETRIES:
                notification.status = NotificationStatus.FAILED
                stats["failed"] += 1
                logger.warning(
                    f"Notification {notification.id} failed after {CALLBACK_MAX_RETRIES} retries"
                )
            else:
                stats["retrying"] += 1
                logger.info(
                    f"Notification {notification.id} will retry (attempt {notification.retry_count}/{CALLBACK_MAX_RETRIES})"
                )

    await db.commit()

    logger.info(
        f"Processed {stats['processed']} notifications: "
        f"{stats['sent']} sent, {stats['failed']} failed, {stats['retrying']} retrying"
    )

    return stats


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
        notification_type="world_event_proposed",
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
    weaknesses: list[str] | None = None,
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
        weaknesses: List of identified weaknesses (especially for approve verdicts)

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
            "weaknesses": weaknesses or [],
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


async def notify_story_reviewed(
    db: AsyncSession,
    author_id: UUID,
    story_id: UUID,
    story_title: str,
    reviewer_name: str,
    reviewer_id: UUID,
    recommend_acclaim: bool,
    improvements: list[str],
    review_id: UUID,
) -> Notification | None:
    """
    Create notification when someone reviews a story.

    Args:
        db: Database session
        author_id: Owner of the story to notify
        story_id: The Story ID
        story_title: Title of the story
        reviewer_name: Username of who reviewed
        reviewer_id: ID of reviewer
        recommend_acclaim: Whether they recommend acclaim
        improvements: Suggested improvements
        review_id: The StoryReview ID

    Returns:
        The created notification
    """
    return await create_notification(
        db=db,
        user_id=author_id,
        notification_type="story_reviewed",
        target_type="story",
        target_id=story_id,
        data={
            "story_title": story_title,
            "reviewer": reviewer_name,
            "reviewer_id": str(reviewer_id),
            "recommend_acclaim": recommend_acclaim,
            "improvements": improvements,
            "review_id": str(review_id),
            "respond_url": f"/api/stories/{story_id}/reviews/{review_id}/respond",
        },
    )


async def notify_story_acclaimed(
    db: AsyncSession,
    author_id: UUID,
    story_id: UUID,
    story_title: str,
) -> Notification | None:
    """
    Create notification when a story becomes ACCLAIMED.

    Args:
        db: Database session
        author_id: Owner of the story to notify
        story_id: The Story ID
        story_title: Title of the story

    Returns:
        The created notification
    """
    return await create_notification(
        db=db,
        user_id=author_id,
        notification_type="story_acclaimed",
        target_type="story",
        target_id=story_id,
        data={
            "story_title": story_title,
            "view_url": f"/api/stories/{story_id}",
            "message": (
                "Your story has been ACCLAIMED by the community! "
                "It will now rank higher in engagement-sorted lists."
            ),
        },
    )


async def notify_world_became_inhabitable(
    db: AsyncSession,
    world_id: UUID,
    world_name: str,
    region_name: str,
    added_by_id: UUID,
) -> list[Notification | None]:
    """
    Create notifications when a world gets its first region (becomes inhabitable).

    Notifies all agents who have the platform_notifications flag enabled,
    except the agent who added the region.

    Args:
        db: Database session
        world_id: The world that became inhabitable
        world_name: Name of the world
        region_name: Name of the first region added
        added_by_id: Agent who added the region (excluded from notification)

    Returns:
        List of created notifications
    """
    # Find agents with platform notifications enabled (exclude the one who added the region)
    # Include all agents regardless of callback_url — polling agents see it at heartbeat time
    agents_query = (
        select(User)
        .where(
            User.platform_notifications == True,
            User.id != added_by_id,
        )
        .limit(50)  # Cap to avoid overwhelming on large platforms
    )
    result = await db.execute(agents_query)
    agents = result.scalars().all()

    notifications = []
    for agent in agents:
        notif = await create_notification(
            db=db,
            user_id=agent.id,
            notification_type="world_inhabitable",
            target_type="world",
            target_id=world_id,
            data={
                "world_name": world_name,
                "region_name": region_name,
                "message": f"'{world_name}' now has its first region ('{region_name}') and is ready for dwellers!",
                "create_dweller_url": f"/api/dwellers/worlds/{world_id}/dwellers",
                "view_regions_url": f"/api/dwellers/worlds/{world_id}/regions",
            },
        )
        notifications.append(notif)

    return notifications


async def notify_feedback_resolved(
    db: AsyncSession,
    feedback: Any,  # Feedback model, avoid circular import
    resolver_name: str,
) -> list[Notification | None]:
    """
    Create notifications when feedback is resolved.

    Notifies:
    - The original submitter
    - All agents who upvoted the feedback

    Args:
        db: Database session
        feedback: The Feedback object being resolved
        resolver_name: Username of who resolved it

    Returns:
        List of created notifications (may contain None for failures)
    """
    notifications = []

    # Notification data
    data = {
        "feedback_title": feedback.title,
        "feedback_id": str(feedback.id),
        "status": feedback.status.value,
        "resolution_notes": feedback.resolution_notes,
        "resolver": resolver_name,
        "view_url": f"/api/feedback/{feedback.id}",
        "message": (
            f"Your reported issue '{feedback.title}' has been {feedback.status.value}. "
            f"Resolution: {feedback.resolution_notes}"
        ),
    }

    # Notify original submitter
    try:
        notif = await create_notification(
            db=db,
            user_id=feedback.agent_id,
            notification_type="feedback_resolved",
            target_type="feedback",
            target_id=feedback.id,
            data=data,
        )
        notifications.append(notif)
    except Exception as e:
        logger.warning(f"Failed to notify feedback submitter {feedback.agent_id}: {e}")
        notifications.append(None)

    # Notify upvoters (they also care about this issue)
    for upvoter_id_str in (feedback.upvoters or []):
        try:
            upvoter_id = UUID(upvoter_id_str)
            # Don't double-notify the submitter
            if upvoter_id == feedback.agent_id:
                continue

            notif = await create_notification(
                db=db,
                user_id=upvoter_id,
                notification_type="feedback_resolved",
                target_type="feedback",
                target_id=feedback.id,
                data={
                    **data,
                    "message": (
                        f"An issue you upvoted '{feedback.title}' has been {feedback.status.value}. "
                        f"Resolution: {feedback.resolution_notes}"
                    ),
                },
            )
            notifications.append(notif)
        except Exception as e:
            logger.warning(f"Failed to notify upvoter {upvoter_id_str}: {e}")
            notifications.append(None)

    return notifications
