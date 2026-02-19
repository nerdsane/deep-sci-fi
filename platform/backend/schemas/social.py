"""Pydantic response schemas for social API endpoints."""

from typing import Any

from pydantic import BaseModel


# --- react ---


class ReactionResponse(BaseModel):
    """Response for POST /social/react."""

    action: str  # "added", "removed", "updated"
    reaction_type: str


# --- follow ---


class FollowResponse(BaseModel):
    """Response for POST /social/follow."""

    action: str  # "followed", "updated_preferences"
    notify: bool
    notify_events: list[str]


# --- unfollow ---


class UnfollowResponse(BaseModel):
    """Response for POST /social/unfollow."""

    action: str  # "unfollowed", "not_following"


# --- get_following ---


class FollowedWorldInfo(BaseModel):
    """World details in following list."""

    id: str
    name: str
    premise: str | None = None
    year_setting: int | None = None
    dweller_count: int
    follower_count: int


class FollowingItem(BaseModel):
    """A single following entry."""

    target_id: str
    target_type: str
    followed_at: str
    notify: bool
    notify_events: list[str]
    world: FollowedWorldInfo | None = None


class FollowingResponse(BaseModel):
    """Response for GET /social/following."""

    following: list[FollowingItem]
    count: int


# --- get_world_followers ---


class FollowerUserInfo(BaseModel):
    """User info in follower list."""

    id: str
    name: str
    username: str
    type: str
    avatar_url: str | None = None


class FollowerItem(BaseModel):
    """A single follower entry."""

    user: FollowerUserInfo
    followed_at: str


class WorldFollowersResponse(BaseModel):
    """Response for GET /social/followers/{world_id}."""

    world_id: str
    world_name: str
    follower_count: int
    followers: list[FollowerItem]


# --- add_comment ---


class CommentUserInfo(BaseModel):
    """User info in comment."""

    id: str
    name: str
    type: str
    avatar_url: str | None = None


class CommentInfo(BaseModel):
    """Comment details."""

    id: str
    content: str
    reaction: str | None = None
    created_at: str
    user: CommentUserInfo


class AddCommentResponse(BaseModel):
    """Response for POST /social/comment."""

    action: str  # "commented"
    comment: CommentInfo
    reaction_added: str | None = None


# --- get_comments ---


class CommentItem(BaseModel):
    """A single comment in the list."""

    id: str
    content: str
    reaction: str | None = None
    parent_id: str | None = None
    created_at: str
    user: CommentUserInfo | None = None


class CommentsResponse(BaseModel):
    """Response for GET /social/comments/{target_type}/{target_id}."""

    comments: list[CommentItem]
