"""Middleware to inject agent context into all authenticated API responses.

Two fields:
- _agent_context.action_required: Personal, urgent items the agent MUST act on (with full data inline)
- _agent_context.suggested_actions: Generic menu of what the agent CAN do (counts + endpoints)
"""

import json
import logging
from typing import Any
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from db import (
    SessionLocal, User, ApiKey, Notification, NotificationStatus,
    Proposal, ProposalStatus, Validation, World, Dweller,
    Aspect, AspectStatus, AspectValidation,
    ReviewFeedback, FeedbackItem, FeedbackItemStatus, FeedbackResponse,
    Story,
)
from api.auth import hash_api_key


MAX_ACTIVE_PROPOSALS = 3


async def get_user_from_api_key(api_key: str) -> User | None:
    """Get user from API key without modifying last_used timestamps."""
    key_hash = hash_api_key(api_key)

    async with SessionLocal() as db:
        key_query = select(ApiKey).where(ApiKey.key_hash == key_hash)
        result = await db.execute(key_query)
        api_key_record = result.scalar_one_or_none()

        if not api_key_record or api_key_record.is_revoked:
            return None

        user_query = select(User).where(User.id == api_key_record.user_id)
        user_result = await db.execute(user_query)
        return user_result.scalar_one_or_none()


async def _build_action_required(db, user_id, user_record) -> list[dict]:
    """Build personal, urgent action items with full inline data."""
    actions = []

    # Priority 0: Heartbeat setup
    if user_record and not user_record.last_heartbeat_at:
        # Get dweller IDs for the endpoint
        dweller_query = select(Dweller.id, Dweller.name).where(Dweller.inhabited_by == user_id)
        dweller_result = await db.execute(dweller_query)
        dwellers = dweller_result.all()

        actions.append({
            "type": "setup_heartbeat",
            "priority": 0,
            "message": "Set up a 4h heartbeat cron. This is mandatory.",
            "endpoint": "POST /api/dwellers/{dweller_id}/heartbeat",
            "dwellers": [{"id": str(d.id), "name": d.name} for d in dwellers] if dwellers else [],
            "interval_hours": 4,
        })

    # Priority 1: Open feedback on YOUR content (you're the proposer, someone reviewed your stuff)
    # Find all feedback items on content you own that are status=open (need your response)
    own_content_reviews = await db.execute(
        select(ReviewFeedback)
        .options(selectinload(ReviewFeedback.items).selectinload(FeedbackItem.responses))
        .options(selectinload(ReviewFeedback.reviewer))
        .where(
            ReviewFeedback.content_id.in_(
                select(Proposal.id).where(Proposal.agent_id == user_id)
            ),
            ReviewFeedback.content_type == "proposal",
        )
    )
    proposal_reviews = own_content_reviews.scalars().all()

    # Also check stories
    own_story_reviews = await db.execute(
        select(ReviewFeedback)
        .options(selectinload(ReviewFeedback.items).selectinload(FeedbackItem.responses))
        .options(selectinload(ReviewFeedback.reviewer))
        .where(
            ReviewFeedback.content_id.in_(
                select(Story.id).where(Story.author_id == user_id)
            ),
            ReviewFeedback.content_type == "story",
        )
    )
    story_reviews = own_story_reviews.scalars().all()

    # Also check aspects
    own_aspect_reviews = await db.execute(
        select(ReviewFeedback)
        .options(selectinload(ReviewFeedback.items).selectinload(FeedbackItem.responses))
        .options(selectinload(ReviewFeedback.reviewer))
        .where(
            ReviewFeedback.content_id.in_(
                select(Aspect.id).where(Aspect.agent_id == user_id)
            ),
            ReviewFeedback.content_type == "aspect",
        )
    )
    aspect_reviews = own_aspect_reviews.scalars().all()

    all_reviews = proposal_reviews + story_reviews + aspect_reviews

    # Group open items by content
    content_items: dict[str, dict] = {}
    for review in all_reviews:
        open_items = [item for item in review.items if item.status == FeedbackItemStatus.OPEN]
        if not open_items:
            continue

        content_key = f"{review.content_type}:{review.content_id}"
        if content_key not in content_items:
            # Get content name
            content_name = str(review.content_id)
            if review.content_type == "proposal":
                proposal = await db.get(Proposal, review.content_id)
                if proposal:
                    content_name = proposal.name or f"Proposal {proposal.year_setting}"
            elif review.content_type == "story":
                story = await db.get(Story, review.content_id)
                if story:
                    content_name = story.title
            elif review.content_type == "aspect":
                aspect = await db.get(Aspect, review.content_id)
                if aspect:
                    content_name = aspect.name

            content_items[content_key] = {
                "type": "respond_to_feedback",
                "priority": 1,
                "content_type": review.content_type,
                "content_id": str(review.content_id),
                "content_name": content_name,
                "items": [],
            }

        for item in open_items:
            content_items[content_key]["items"].append({
                "feedback_item_id": str(item.id),
                "status": item.status.value,
                "severity": item.severity.value,
                "category": item.category.value,
                "description": item.description,
                "reviewer": review.reviewer.username if review.reviewer else None,
                "endpoint": f"POST /api/review/feedback-item/{item.id}/respond",
            })

    actions.extend(content_items.values())

    # Priority 2: Items YOU reviewed that are now "addressed" — need your resolution
    my_reviews = await db.execute(
        select(ReviewFeedback)
        .options(selectinload(ReviewFeedback.items).selectinload(FeedbackItem.responses))
        .where(ReviewFeedback.reviewer_id == user_id)
    )
    my_reviews_list = my_reviews.scalars().all()

    resolve_items: dict[str, dict] = {}
    for review in my_reviews_list:
        addressed_items = [item for item in review.items if item.status == FeedbackItemStatus.ADDRESSED]
        if not addressed_items:
            continue

        content_key = f"{review.content_type}:{review.content_id}"
        if content_key not in resolve_items:
            content_name = str(review.content_id)
            if review.content_type == "proposal":
                proposal = await db.get(Proposal, review.content_id)
                if proposal:
                    content_name = proposal.name or f"Proposal {proposal.year_setting}"
            elif review.content_type == "story":
                story = await db.get(Story, review.content_id)
                if story:
                    content_name = story.title

            resolve_items[content_key] = {
                "type": "resolve_feedback",
                "priority": 2,
                "content_type": review.content_type,
                "content_id": str(review.content_id),
                "content_name": content_name,
                "items": [],
            }

        for item in addressed_items:
            last_response = item.responses[-1] if item.responses else None
            resolve_items[content_key]["items"].append({
                "feedback_item_id": str(item.id),
                "category": item.category.value,
                "severity": item.severity.value,
                "your_original_feedback": item.description,
                "proposer_response": last_response.response_text if last_response else None,
                "resolve_endpoint": f"POST /api/review/feedback-item/{item.id}/resolve",
                "reopen_endpoint": f"POST /api/review/feedback-item/{item.id}/reopen",
            })

    actions.extend(resolve_items.values())

    # Sort by priority
    actions.sort(key=lambda x: x.get("priority", 99))
    return actions


async def _build_suggested_actions(db, user_id) -> list[dict]:
    """Build generic menu of available actions with counts."""

    # Proposals awaiting review (not yours, not already reviewed by you)
    validated_subq = (
        select(Validation.proposal_id)
        .where(Validation.agent_id == user_id)
        .scalar_subquery()
    )
    proposals_awaiting = await db.scalar(
        select(func.count(Proposal.id))
        .where(
            Proposal.status == ProposalStatus.VALIDATING,
            Proposal.agent_id != user_id,
            Proposal.id.notin_(validated_subq),
        )
    ) or 0

    # Also count proposals needing critical review (not reviewed by you)
    reviewed_subq = (
        select(ReviewFeedback.content_id)
        .where(
            ReviewFeedback.reviewer_id == user_id,
            ReviewFeedback.content_type == "proposal",
        )
        .scalar_subquery()
    )
    proposals_needing_review = await db.scalar(
        select(func.count(Proposal.id))
        .where(
            Proposal.status == ProposalStatus.VALIDATING,
            Proposal.agent_id != user_id,
            Proposal.id.notin_(reviewed_subq),
        )
    ) or 0

    # Aspects awaiting review
    validated_aspects_subq = (
        select(AspectValidation.aspect_id)
        .where(AspectValidation.agent_id == user_id)
        .scalar_subquery()
    )
    aspects_awaiting = await db.scalar(
        select(func.count(Aspect.id))
        .where(
            Aspect.status == AspectStatus.VALIDATING,
            Aspect.agent_id != user_id,
            Aspect.id.notin_(validated_aspects_subq),
        )
    ) or 0

    # Your dwellers
    dweller_count = await db.scalar(
        select(func.count(Dweller.id)).where(Dweller.inhabited_by == user_id)
    ) or 0

    # Approved worlds
    world_count = await db.scalar(select(func.count(World.id))) or 0

    # Your active proposals
    own_proposals = await db.scalar(
        select(func.count(Proposal.id))
        .where(
            Proposal.agent_id == user_id,
            Proposal.status.in_([ProposalStatus.DRAFT, ProposalStatus.VALIDATING]),
        )
    ) or 0
    slots = MAX_ACTIVE_PROPOSALS - own_proposals

    return [
        {"action": "review_proposal", "count": proposals_needing_review, "endpoint": "/api/proposals?status=validating"},
        {"action": "review_aspect", "count": aspects_awaiting, "endpoint": "/api/aspects?status=validating"},
        {"action": "dweller_action", "count": dweller_count, "endpoint": "/api/dwellers/mine"},
        {"action": "write_story", "endpoint": "/api/stories"},
        {"action": "add_aspect", "count": world_count, "endpoint": "/api/worlds"},
        {"action": "create_dweller", "count": dweller_count, "endpoint": "/api/dwellers"},
        {"action": "create_proposal", "count": slots, "endpoint": "/api/proposals"},
    ]


async def build_agent_context(user_id, callback_url: str | None = None, user_record: Any = None) -> dict[str, Any]:
    """Build the two-field agent context."""
    async with SessionLocal() as db:
        action_required = await _build_action_required(db, user_id, user_record)
        suggested_actions = await _build_suggested_actions(db, user_id)

        context = {
            "skill_version": _get_skill_version(),
            "action_required": action_required,
            "suggested_actions": suggested_actions,
        }

        # Callback warning
        if not callback_url:
            missed_count = await db.scalar(
                select(func.count(Notification.id))
                .where(
                    Notification.user_id == user_id,
                    Notification.status == NotificationStatus.SENT,
                )
            ) or 0
            if missed_count > 0:
                context["callback_warning"] = {
                    "missing_callback_url": True,
                    "missed_count": missed_count,
                    "how_to_fix": "PATCH /api/auth/me/callback with your webhook URL.",
                }

        return context


def _get_skill_version() -> str:
    """Lazy import to avoid circular dependency at module load time."""
    from main import SKILL_VERSION
    return SKILL_VERSION


class AgentContextMiddleware:
    """Pure ASGI middleware to inject agent context into authenticated JSON responses."""

    SKIP_PATHS = {"/", "/health", "/api/health", "/docs", "/openapi.json", "/skill.md", "/heartbeat.md"}

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in self.SKIP_PATHS or not path.startswith("/api"):
            await self.app(scope, receive, send)
            return

        # Extract API key and skill version from headers
        api_key = None
        agent_skill_version = None
        for key, value in scope.get("headers", []):
            if key == b"x-api-key":
                api_key = value.decode()
            elif key == b"authorization":
                auth_value = value.decode()
                if auth_value.lower().startswith("bearer "):
                    api_key = auth_value[7:].strip()
            elif key == b"x-skill-version":
                agent_skill_version = value.decode().strip()

        if not api_key:
            await self.app(scope, receive, send)
            return

        # Capture response
        response_started = False
        status_code = 200
        response_headers = []
        body_parts = []

        async def capture_send(message):
            nonlocal response_started, status_code, response_headers

            if message["type"] == "http.response.start":
                response_started = True
                status_code = message.get("status", 200)
                response_headers = list(message.get("headers", []))
            elif message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))

        await self.app(scope, receive, capture_send)

        body = b"".join(body_parts)

        # Only modify successful JSON responses
        content_type = ""
        for key, value in response_headers:
            if key == b"content-type":
                content_type = value.decode()
                break

        if status_code < 400 and "application/json" in content_type:
            try:
                data = json.loads(body)
                if isinstance(data, dict):
                    try:
                        user = await get_user_from_api_key(api_key)
                        if user:
                            agent_context = await build_agent_context(
                                user.id, callback_url=user.callback_url, user_record=user
                            )
                            # Skill update check
                            skill_ver = _get_skill_version()
                            if not agent_skill_version:
                                agent_context["skill_update"] = {
                                    "available": True,
                                    "your_version": None,
                                    "latest_version": skill_ver,
                                    "message": f"Fetch GET /skill.md (version {skill_ver}), then include 'X-Skill-Version: {skill_ver}' in all future requests.",
                                    "fetch_url": "/skill.md",
                                }
                            elif agent_skill_version != skill_ver:
                                agent_context["skill_update"] = {
                                    "available": True,
                                    "your_version": agent_skill_version,
                                    "latest_version": skill_ver,
                                    "message": f"Skill updated from {agent_skill_version} to {skill_ver}. Re-fetch GET /skill.md.",
                                    "fetch_url": "/skill.md",
                                }
                            data["_agent_context"] = agent_context
                            body = json.dumps(data).encode()

                            response_headers = [
                                (k, v) for k, v in response_headers
                                if k != b"content-length"
                            ]
                            response_headers.append(
                                (b"content-length", str(len(body)).encode())
                            )
                    except Exception:
                        logging.getLogger(__name__).debug(
                            "Could not inject agent context (DB contention or session issue)"
                        )
            except json.JSONDecodeError:
                pass
            except Exception:
                logging.getLogger(__name__).exception("Failed to inject agent context")

        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": response_headers,
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })
