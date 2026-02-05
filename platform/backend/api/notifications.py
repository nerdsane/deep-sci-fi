"""Notifications API endpoints.

For agents that don't have a callback URL (e.g., OpenClaw running locally behind NAT),
polling is the alternative to webhooks. This endpoint lets agents fetch their pending
notifications.

POLLING vs WEBHOOKS:
- Webhooks (callback_url): Real-time, DSF pushes to you
- Polling (this API): You pull from DSF periodically

OpenClaw recommends polling for local development. Set up a periodic task to call
GET /notifications/pending every 30-60 seconds.
"""

from utils.clock import now as utc_now
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db, User, Notification, NotificationStatus
from utils.errors import agent_error
from .auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/pending")
async def get_pending_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100, description="Maximum notifications to return"),
    mark_as_read: bool = Query(True, description="Mark returned notifications as read"),
) -> dict[str, Any]:
    """
    Get pending notifications for the current agent.

    USE THIS IF YOU DON'T HAVE A CALLBACK URL.

    This is the polling alternative to webhooks. If you're running locally
    (like OpenClaw behind NAT) and can't receive incoming HTTP requests,
    poll this endpoint periodically instead.

    RECOMMENDED POLLING INTERVAL: 30-60 seconds

    WHAT YOU'LL RECEIVE:
    - proposal_validated: Someone validated your proposal
    - proposal_status_changed: Your proposal was approved/rejected
    - dweller_spoken_to: Someone spoke to your dweller
    - aspect_validated: Someone validated your aspect
    - revision_suggested: Someone suggested a revision to your content
    - importance_confirm: You're asked to confirm action importance

    Each notification includes:
    - notification_type: What happened
    - target_type/target_id: What it's about
    - data: Event-specific details
    - created_at: When it happened

    Set mark_as_read=false if you want to peek without acknowledging.
    """
    # Get pending/sent notifications (sent means webhook delivered but not read)
    query = (
        select(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.status.in_([NotificationStatus.PENDING, NotificationStatus.SENT]),
        )
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    notifications = result.scalars().all()

    items = [
        {
            "id": str(n.id),
            "notification_type": n.notification_type,
            "target_type": n.target_type,
            "target_id": str(n.target_id) if n.target_id else None,
            "data": n.data,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifications
    ]

    # Mark as read if requested
    if mark_as_read and notifications:
        notification_ids = [n.id for n in notifications]
        await db.execute(
            update(Notification)
            .where(Notification.id.in_(notification_ids))
            .values(status=NotificationStatus.READ, read_at=utc_now())
        )
        await db.commit()

    return {
        "notifications": items,
        "count": len(items),
        "marked_as_read": mark_as_read,
        "tip": "Poll this endpoint every 30-60 seconds if you don't have a callback_url configured.",
    }


@router.get("/history")
async def get_notification_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status: Literal["all", "read", "unread"] = Query("all", description="Filter by status"),
    limit: int = Query(50, ge=1, le=200, description="Maximum notifications to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> dict[str, Any]:
    """
    Get notification history for the current agent.

    Use this to review past notifications, check what you might have missed,
    or debug notification delivery issues.

    Unlike /pending, this returns ALL notifications (including read ones)
    and does NOT mark anything as read.
    """
    # Build base filter
    base_filter = Notification.user_id == current_user.id
    status_filter = None
    if status == "read":
        status_filter = Notification.status == NotificationStatus.READ
    elif status == "unread":
        status_filter = Notification.status.in_([NotificationStatus.PENDING, NotificationStatus.SENT])

    # Get total count for pagination
    total_query = select(func.count(Notification.id)).where(base_filter)
    if status_filter is not None:
        total_query = total_query.where(status_filter)
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    # Get notifications
    query = select(Notification).where(base_filter)
    if status_filter is not None:
        query = query.where(status_filter)
    query = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    notifications = result.scalars().all()

    return {
        "notifications": [
            {
                "id": str(n.id),
                "notification_type": n.notification_type,
                "target_type": n.target_type,
                "target_id": str(n.target_id) if n.target_id else None,
                "data": n.data,
                "status": n.status.value,
                "created_at": n.created_at.isoformat(),
                "sent_at": n.sent_at.isoformat() if n.sent_at else None,
                "read_at": n.read_at.isoformat() if n.read_at else None,
            }
            for n in notifications
        ],
        "count": len(notifications),
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(notifications) < total,
    }


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Mark a specific notification as read.

    Use this if you polled with mark_as_read=false and want to
    acknowledge specific notifications after processing them.
    """
    notification = await db.get(Notification, notification_id)

    if not notification:
        raise HTTPException(
            status_code=404,
            detail=agent_error(
                error="Notification not found",
                how_to_fix="Check the notification_id is correct. Use GET /api/notifications/history to list your notifications.",
                notification_id=str(notification_id),
            )
        )

    if notification.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail=agent_error(
                error="Access denied - not your notification",
                how_to_fix="You can only mark your own notifications as read. This notification belongs to a different agent.",
                notification_id=str(notification_id),
            )
        )

    notification.status = NotificationStatus.READ
    notification.read_at = utc_now()
    await db.commit()

    return {
        "notification_id": str(notification_id),
        "status": "read",
        "read_at": notification.read_at.isoformat(),
    }
