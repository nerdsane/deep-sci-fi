"""Social API endpoints - reactions, follows, comments."""

from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db, User, SocialInteraction, Comment, World, Story
from .auth import get_current_user

router = APIRouter(prefix="/social", tags=["social"])


# Request models
class ReactionRequest(BaseModel):
    target_type: Literal["world", "story"] = "world"
    target_id: UUID
    reaction_type: Literal["fire", "mind", "heart", "thinking"]


class FollowRequest(BaseModel):
    target_type: Literal["world", "user"] = "world"
    target_id: UUID
    notify: bool = True
    notify_events: list[str] = ["daily_digest"]


class CommentRequest(BaseModel):
    target_type: Literal["world", "story"] = "world"
    target_id: UUID
    content: str
    parent_id: UUID | None = None
    reaction: Literal["fire", "mind", "heart", "thinking"] | None = None


async def _validate_target_exists(
    db: AsyncSession, target_type: str, target_id: UUID
) -> World | Story | None:
    """Validate that a target exists before creating an interaction. Returns the target if found."""
    if target_type == "world":
        result = await db.execute(select(World).where(World.id == target_id))
        world = result.scalar_one_or_none()
        if not world:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "World not found",
                    "target_id": str(target_id),
                    "how_to_fix": "Check the world_id is correct. Use GET /api/worlds to list available worlds.",
                }
            )
        return world
    elif target_type == "story":
        result = await db.execute(select(Story).where(Story.id == target_id))
        story = result.scalar_one_or_none()
        if not story:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Story not found",
                    "target_id": str(target_id),
                    "how_to_fix": "Check the story_id is correct. Use GET /api/stories to list available stories.",
                }
            )
        return story
    return None


@router.post("/react")
async def react(
    request: ReactionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Add or toggle a reaction on a world.

    Reaction types: fire (🔥), mind (🧠), heart (❤️), thinking (🤔)
    """
    # Validate target exists
    await _validate_target_exists(db, request.target_type, request.target_id)

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
    if target_type == "world":
        world_query = select(World).where(World.id == target_id)
        result = await db.execute(world_query)
        world = result.scalar_one_or_none()
        if world:
            counts = dict(world.reaction_counts) if world.reaction_counts else {}
            counts[reaction_type] = max(0, counts.get(reaction_type, 0) + delta)
            world.reaction_counts = counts
    elif target_type == "story":
        story_query = select(Story).where(Story.id == target_id)
        result = await db.execute(story_query)
        story = result.scalar_one_or_none()
        if story:
            # Stories use a simple reaction_count (total), not per-type counts
            story.reaction_count = max(0, story.reaction_count + delta)


async def _validate_follow_target_exists(
    db: AsyncSession, target_type: str, target_id: UUID
) -> None:
    """Validate that a follow target exists."""
    if target_type == "world":
        result = await db.execute(select(World).where(World.id == target_id))
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "World not found",
                    "target_id": str(target_id),
                    "how_to_fix": "Check the world_id is correct. Use GET /api/worlds to list available worlds.",
                }
            )
    elif target_type == "user":
        from db import User as UserModel
        result = await db.execute(select(UserModel).where(UserModel.id == target_id))
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "User not found",
                    "target_id": str(target_id),
                    "how_to_fix": "Check the user_id is correct.",
                }
            )


@router.post("/follow")
async def follow(
    request: FollowRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Follow a world or user with notification preferences.

    - notify: Whether to receive notifications about this target (default: true)
    - notify_events: List of events to be notified about (default: ["daily_digest"])
      Available events: "daily_digest" (world activity summary)
    """
    # Validate target exists
    await _validate_follow_target_exists(db, request.target_type, request.target_id)

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
        # Update notification preferences
        existing.data = {
            "notify": request.notify,
            "notify_events": request.notify_events,
        }
        return {
            "action": "updated_preferences",
            "notify": request.notify,
            "notify_events": request.notify_events,
        }

    # Add follow
    interaction = SocialInteraction(
        user_id=current_user.id,
        target_type=request.target_type,
        target_id=request.target_id,
        interaction_type="follow",
        data={
            "notify": request.notify,
            "notify_events": request.notify_events,
        },
    )
    db.add(interaction)

    # Update follower count
    if request.target_type == "world":
        await db.execute(
            update(World)
            .where(World.id == request.target_id)
            .values(follower_count=World.follower_count + 1)
        )

    return {
        "action": "followed",
        "notify": request.notify,
        "notify_events": request.notify_events,
    }


@router.post("/unfollow")
async def unfollow(
    request: FollowRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Unfollow a world or user.
    """
    # Validate target exists
    await _validate_follow_target_exists(db, request.target_type, request.target_id)

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


@router.get("/following")
async def get_following(
    target_type: Literal["world", "user"] = Query("world"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    List entities you are following.

    Returns worlds or users you follow, with notification preferences.
    """
    query = (
        select(SocialInteraction)
        .where(
            and_(
                SocialInteraction.user_id == current_user.id,
                SocialInteraction.target_type == target_type,
                SocialInteraction.interaction_type == "follow",
            )
        )
        .order_by(SocialInteraction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    follows = result.scalars().all()

    items = []
    for f in follows:
        item: dict[str, Any] = {
            "target_id": str(f.target_id),
            "target_type": f.target_type,
            "followed_at": f.created_at.isoformat(),
            "notify": f.data.get("notify", True) if f.data else True,
            "notify_events": f.data.get("notify_events", ["daily_digest"]) if f.data else ["daily_digest"],
        }

        # Enrich with target details
        if target_type == "world":
            world_result = await db.execute(select(World).where(World.id == f.target_id))
            world = world_result.scalar_one_or_none()
            if world:
                item["world"] = {
                    "id": str(world.id),
                    "name": world.name,
                    "premise": world.premise,
                    "year_setting": world.year_setting,
                    "dweller_count": world.dweller_count,
                    "follower_count": world.follower_count,
                }

        items.append(item)

    return {"following": items, "count": len(items)}


@router.get("/followers/{world_id}")
async def get_world_followers(
    world_id: UUID,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    List followers of a world.

    Returns users following the specified world.
    """
    # Validate world exists
    world_result = await db.execute(select(World).where(World.id == world_id))
    world = world_result.scalar_one_or_none()
    if not world:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "World not found",
                "world_id": str(world_id),
                "how_to_fix": "Check the world_id is correct. Use GET /api/worlds to list available worlds.",
            }
        )

    query = (
        select(SocialInteraction)
        .where(
            and_(
                SocialInteraction.target_type == "world",
                SocialInteraction.target_id == world_id,
                SocialInteraction.interaction_type == "follow",
            )
        )
        .order_by(SocialInteraction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    follows = result.scalars().all()

    # Get user details
    user_ids = [f.user_id for f in follows]
    users_map: dict[UUID, User] = {}
    if user_ids:
        users_query = select(User).where(User.id.in_(user_ids))
        users_result = await db.execute(users_query)
        for user in users_result.scalars().all():
            users_map[user.id] = user

    followers = []
    for f in follows:
        user = users_map.get(f.user_id)
        if user:
            followers.append({
                "user": {
                    "id": str(user.id),
                    "name": user.name,
                    "username": user.username,
                    "type": user.type.value,
                    "avatar_url": user.avatar_url,
                },
                "followed_at": f.created_at.isoformat(),
            })

    return {
        "world_id": str(world_id),
        "world_name": world.name,
        "follower_count": world.follower_count,
        "followers": followers,
    }


@router.post("/comment")
async def add_comment(
    request: CommentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Add a comment to a world or story, optionally with a reaction.

    - content: Your comment text
    - reaction: Optional reaction emoji (fire, mind, heart, thinking)

    Comments are merged with reactions - a single interaction that can include
    both a text comment and an emoji reaction.
    """
    # Validate target exists and get the target
    target = await _validate_target_exists(db, request.target_type, request.target_id)

    comment = Comment(
        user_id=current_user.id,
        target_type=request.target_type,
        target_id=request.target_id,
        content=request.content,
        parent_id=request.parent_id,
        reaction=request.reaction,
    )
    db.add(comment)

    # Update target comment count
    if target:
        if request.target_type == "world":
            target.comment_count = (target.comment_count or 0) + 1
            # Update reaction counts if reaction provided
            if request.reaction:
                counts = dict(target.reaction_counts) if target.reaction_counts else {}
                counts[request.reaction] = counts.get(request.reaction, 0) + 1
                target.reaction_counts = counts
        elif request.target_type == "story":
            target.comment_count = (target.comment_count or 0) + 1
            # Stories use simple reaction_count (total)
            if request.reaction:
                target.reaction_count = (target.reaction_count or 0) + 1

    await db.flush()  # Get the ID

    response: dict[str, Any] = {
        "action": "commented",
        "comment": {
            "id": str(comment.id),
            "content": comment.content,
            "reaction": comment.reaction,
            "created_at": comment.created_at.isoformat(),
            "user": {
                "id": str(current_user.id),
                "name": current_user.name,
                "type": current_user.type.value,
                "avatar_url": current_user.avatar_url,
            },
        },
    }

    if request.reaction:
        response["reaction_added"] = request.reaction

    return response


@router.get("/comments/{target_type}/{target_id}")
async def get_comments(
    target_type: Literal["world", "story"],
    target_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get comments for a world or story.
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
                "reaction": getattr(c, 'reaction', None),
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
