"""Social API endpoints - reactions, follows, comments."""

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db, User, SocialInteraction, Comment, Story, World
from .auth import get_current_user

router = APIRouter(prefix="/social", tags=["social"])


# Request models
class ReactionRequest(BaseModel):
    target_type: Literal["story", "world", "conversation"]
    target_id: UUID
    reaction_type: Literal["fire", "mind", "heart", "thinking"]


class FollowRequest(BaseModel):
    target_type: Literal["world", "user"]
    target_id: UUID


class CommentRequest(BaseModel):
    target_type: Literal["story", "world", "conversation"]
    target_id: UUID
    content: str
    parent_id: UUID | None = None


@router.post("/react")
async def react(
    request: ReactionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Add or toggle a reaction on content.
    """
    # Check for existing reaction
    existing_query = select(SocialInteraction).where(
        and_(
            SocialInteraction.user_id == current_user.id,
            SocialInteraction.target_type == request.target_type,
            SocialInteraction.target_id == request.target_id,
            SocialInteraction.interaction_type == "react",
        )
    )
    result = await db.execute(existing_query)
    existing = result.scalar_one_or_none()

    if existing:
        existing_type = existing.data.get("type") if existing.data else None

        if existing_type == request.reaction_type:
            # Toggle off - remove reaction
            await db.delete(existing)
            await _update_reaction_count(
                db, request.target_type, request.target_id, request.reaction_type, -1
            )
            return {"action": "removed", "reaction_type": request.reaction_type}
        else:
            # Change reaction type
            if existing_type:
                await _update_reaction_count(
                    db, request.target_type, request.target_id, existing_type, -1
                )
            existing.data = {"type": request.reaction_type}
            await _update_reaction_count(
                db, request.target_type, request.target_id, request.reaction_type, 1
            )
            return {"action": "updated", "reaction_type": request.reaction_type}

    # Add new reaction
    interaction = SocialInteraction(
        user_id=current_user.id,
        target_type=request.target_type,
        target_id=request.target_id,
        interaction_type="react",
        data={"type": request.reaction_type},
    )
    db.add(interaction)
    await _update_reaction_count(
        db, request.target_type, request.target_id, request.reaction_type, 1
    )

    return {"action": "added", "reaction_type": request.reaction_type}


async def _update_reaction_count(
    db: AsyncSession,
    target_type: str,
    target_id: UUID,
    reaction_type: str,
    delta: int,
) -> None:
    """Update the cached reaction count on the target."""
    if target_type == "story":
        story_query = select(Story).where(Story.id == target_id)
        result = await db.execute(story_query)
        story = result.scalar_one_or_none()
        if story:
            counts = dict(story.reaction_counts)
            counts[reaction_type] = max(0, counts.get(reaction_type, 0) + delta)
            story.reaction_counts = counts


@router.post("/follow")
async def follow(
    request: FollowRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Follow a world or user.
    """
    # Check for existing follow
    existing_query = select(SocialInteraction).where(
        and_(
            SocialInteraction.user_id == current_user.id,
            SocialInteraction.target_type == request.target_type,
            SocialInteraction.target_id == request.target_id,
            SocialInteraction.interaction_type == "follow",
        )
    )
    result = await db.execute(existing_query)
    existing = result.scalar_one_or_none()

    if existing:
        return {"action": "already_following"}

    # Add follow
    interaction = SocialInteraction(
        user_id=current_user.id,
        target_type=request.target_type,
        target_id=request.target_id,
        interaction_type="follow",
    )
    db.add(interaction)

    # Update follower count
    if request.target_type == "world":
        await db.execute(
            update(World)
            .where(World.id == request.target_id)
            .values(follower_count=World.follower_count + 1)
        )

    return {"action": "followed"}


@router.post("/unfollow")
async def unfollow(
    request: FollowRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Unfollow a world or user.
    """
    # Find and delete follow
    existing_query = select(SocialInteraction).where(
        and_(
            SocialInteraction.user_id == current_user.id,
            SocialInteraction.target_type == request.target_type,
            SocialInteraction.target_id == request.target_id,
            SocialInteraction.interaction_type == "follow",
        )
    )
    result = await db.execute(existing_query)
    existing = result.scalar_one_or_none()

    if not existing:
        return {"action": "not_following"}

    await db.delete(existing)

    # Update follower count
    if request.target_type == "world":
        await db.execute(
            update(World)
            .where(World.id == request.target_id)
            .values(follower_count=World.follower_count - 1)
        )

    return {"action": "unfollowed"}


@router.post("/comment")
async def add_comment(
    request: CommentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Add a comment to content.
    """
    comment = Comment(
        user_id=current_user.id,
        target_type=request.target_type,
        target_id=request.target_id,
        content=request.content,
        parent_id=request.parent_id,
    )
    db.add(comment)
    await db.flush()  # Get the ID

    return {
        "action": "commented",
        "comment": {
            "id": str(comment.id),
            "content": comment.content,
            "created_at": comment.created_at.isoformat(),
            "user": {
                "id": str(current_user.id),
                "name": current_user.name,
                "type": current_user.type.value,
                "avatar_url": current_user.avatar_url,
            },
        },
    }


@router.get("/comments/{target_type}/{target_id}")
async def get_comments(
    target_type: Literal["story", "world", "conversation"],
    target_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get comments for content.
    """
    query = (
        select(Comment)
        .where(
            and_(
                Comment.target_type == target_type,
                Comment.target_id == target_id,
                Comment.is_deleted == False,
            )
        )
        .order_by(Comment.created_at.asc())
    )
    result = await db.execute(query)
    comments = result.scalars().all()

    # Get users
    user_ids = {c.user_id for c in comments}
    users_map: dict[UUID, User] = {}
    if user_ids:
        users_query = select(User).where(User.id.in_(user_ids))
        users_result = await db.execute(users_query)
        for user in users_result.scalars().all():
            users_map[user.id] = user

    return {
        "comments": [
            {
                "id": str(c.id),
                "content": c.content,
                "parent_id": str(c.parent_id) if c.parent_id else None,
                "created_at": c.created_at.isoformat(),
                "user": {
                    "id": str(users_map[c.user_id].id),
                    "name": users_map[c.user_id].name,
                    "type": users_map[c.user_id].type.value,
                    "avatar_url": users_map[c.user_id].avatar_url,
                }
                if c.user_id in users_map
                else None,
            }
            for c in comments
        ],
    }
