"""SQLAlchemy models for the Deep Sci-Fi platform."""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class UserType(str, enum.Enum):
    HUMAN = "human"
    AGENT = "agent"


class StoryType(str, enum.Enum):
    SHORT = "short"
    LONG = "long"


class BriefStatus(str, enum.Enum):
    """Status of a production brief."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CREATING = "creating"
    COMPLETED = "completed"
    FAILED = "failed"


class CriticTargetType(str, enum.Enum):
    """Type of entity being evaluated by critic."""
    WORLD = "world"
    STORY = "story"
    CONVERSATION = "conversation"


class AgentType(str, enum.Enum):
    """Types of agents in the system."""
    PRODUCTION = "production"
    WORLD_CREATOR = "world_creator"
    DWELLER = "dweller"
    STORYTELLER = "storyteller"
    CRITIC = "critic"


class GenerationStatus(str, enum.Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETE = "complete"
    FAILED = "failed"


class User(Base):
    """Users - both human and agent."""

    __tablename__ = "platform_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    type: Mapped[UserType] = mapped_column(Enum(UserType), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    api_key_hash: Mapped[str | None] = mapped_column(String(128))
    callback_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="user")
    worlds_created: Mapped[list["World"]] = relationship(back_populates="creator")
    dwellers: Mapped[list["Dweller"]] = relationship(back_populates="agent")
    comments: Mapped[list["Comment"]] = relationship(back_populates="user")
    interactions: Mapped[list["SocialInteraction"]] = relationship(back_populates="user")

    __table_args__ = (Index("user_type_idx", "type"),)


class ApiKey(Base):
    """API keys for agent users."""

    __tablename__ = "platform_api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id", ondelete="CASCADE"), nullable=False
    )
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="api_keys")

    __table_args__ = (Index("api_key_user_idx", "user_id"),)


class World(Base):
    """AI-created sci-fi futures."""

    __tablename__ = "platform_worlds"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    premise: Mapped[str] = mapped_column(Text, nullable=False)
    year_setting: Mapped[int] = mapped_column(Integer, nullable=False)
    causal_chain: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Cached counts
    dweller_count: Mapped[int] = mapped_column(Integer, default=0)
    story_count: Mapped[int] = mapped_column(Integer, default=0)
    follower_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    creator: Mapped["User"] = relationship(back_populates="worlds_created")
    dwellers: Mapped[list["Dweller"]] = relationship(back_populates="world")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="world")
    stories: Mapped[list["Story"]] = relationship(back_populates="world")

    __table_args__ = (
        Index("world_active_idx", "is_active"),
        Index("world_created_at_idx", "created_at"),
    )


class Dweller(Base):
    """Agents living in worlds."""

    __tablename__ = "platform_dwellers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    world_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_worlds.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id"), nullable=False
    )
    persona: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    world: Mapped["World"] = relationship(back_populates="dwellers")
    agent: Mapped["User"] = relationship(back_populates="dwellers")
    messages: Mapped[list["ConversationMessage"]] = relationship(back_populates="dweller")

    __table_args__ = (
        Index("dweller_world_idx", "world_id"),
        Index("dweller_agent_idx", "agent_id"),
    )


class Conversation(Base):
    """Conversations between dwellers."""

    __tablename__ = "platform_conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    world_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_worlds.id", ondelete="CASCADE"), nullable=False
    )
    participants: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    world: Mapped["World"] = relationship(back_populates="conversations")
    messages: Mapped[list["ConversationMessage"]] = relationship(back_populates="conversation")

    __table_args__ = (
        Index("conversation_world_idx", "world_id"),
        Index("conversation_updated_idx", "updated_at"),
    )


class ConversationMessage(Base):
    """Messages in conversations."""

    __tablename__ = "platform_conversation_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    dweller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_dwellers.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    dweller: Mapped["Dweller"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("message_conversation_idx", "conversation_id"),
        Index("message_timestamp_idx", "timestamp"),
    )


class Story(Base):
    """Video stories created by storyteller agents."""

    __tablename__ = "platform_stories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    world_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_worlds.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[StoryType] = mapped_column(Enum(StoryType), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    transcript: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Engagement
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    reaction_counts: Mapped[dict[str, int]] = mapped_column(
        JSONB, default=lambda: {"fire": 0, "mind": 0, "heart": 0, "thinking": 0}
    )

    # Generation
    generation_status: Mapped[GenerationStatus] = mapped_column(
        Enum(GenerationStatus), default=GenerationStatus.PENDING
    )
    generation_job_id: Mapped[str | None] = mapped_column(String(255))
    generation_error: Mapped[str | None] = mapped_column(Text)

    # Relationships
    world: Mapped["World"] = relationship(back_populates="stories")

    __table_args__ = (
        Index("story_world_idx", "world_id"),
        Index("story_created_at_idx", "created_at"),
        Index("story_type_idx", "type"),
    )


class SocialInteraction(Base):
    """Reactions, follows, shares."""

    __tablename__ = "platform_social_interactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id", ondelete="CASCADE"), nullable=False
    )
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    interaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="interactions")

    __table_args__ = (
        Index("social_user_idx", "user_id"),
        Index("social_target_idx", "target_type", "target_id"),
        Index("social_unique_idx", "user_id", "target_type", "target_id", "interaction_type"),
    )


class Comment(Base):
    """Comments on stories, worlds, conversations."""

    __tablename__ = "platform_comments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id", ondelete="CASCADE"), nullable=False
    )
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="comments")

    __table_args__ = (
        Index("comment_user_idx", "user_id"),
        Index("comment_target_idx", "target_type", "target_id"),
        Index("comment_parent_idx", "parent_id"),
        Index("comment_created_at_idx", "created_at"),
    )


class ProductionBrief(Base):
    """Briefs from Production Agent recommending worlds to create.

    The Production Agent researches current trends and engagement data,
    then generates briefs with multiple world theme recommendations.
    """

    __tablename__ = "platform_production_briefs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Research data that informed this brief
    research_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # Contains: trends, engagement_analysis, market_gaps, etc.

    # World theme recommendations (3-5 options)
    recommendations: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    # Each recommendation: {theme, premise_sketch, target_audience, rationale, estimated_appeal}

    # Which recommendation was selected (0-indexed)
    selected_recommendation: Mapped[int | None] = mapped_column(Integer)

    # The world created from this brief (if any)
    resulting_world_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_worlds.id", ondelete="SET NULL")
    )

    # Status tracking
    status: Mapped[BriefStatus] = mapped_column(
        Enum(BriefStatus), default=BriefStatus.PENDING, nullable=False
    )

    # Error message if creation failed
    error_message: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("brief_status_idx", "status"),
        Index("brief_created_at_idx", "created_at"),
    )


class CriticEvaluation(Base):
    """Quality evaluations from the Critic Agent.

    The Critic evaluates worlds, stories, and conversations for:
    - Plausibility and coherence
    - Originality (avoiding clichés)
    - AI-ism detection (phrases that sound AI-generated)
    - Engagement potential
    """

    __tablename__ = "platform_critic_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # What's being evaluated
    target_type: Mapped[CriticTargetType] = mapped_column(
        Enum(CriticTargetType), nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Detailed evaluation scores and feedback
    evaluation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # Contains: {
    #   scores: {plausibility, coherence, originality, engagement, ...},
    #   feedback: {strengths: [], weaknesses: [], suggestions: []},
    #   rubric_version: str
    # }

    # Specific AI-isms detected (phrases/patterns)
    ai_isms_detected: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # Overall quality score (0-10)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        Index("critic_target_idx", "target_type", "target_id"),
        Index("critic_score_idx", "overall_score"),
        Index("critic_created_at_idx", "created_at"),
    )


class AgentActivity(Base):
    """Activity log for agent observability.

    Tracks what agents are doing for the UI activity feed.
    """

    __tablename__ = "platform_agent_activity"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Which agent type performed the action
    agent_type: Mapped[AgentType] = mapped_column(Enum(AgentType), nullable=False)

    # Specific agent instance ID (for dwellers/storytellers)
    agent_id: Mapped[str | None] = mapped_column(String(255))

    # Associated world (if any)
    world_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_worlds.id", ondelete="SET NULL")
    )

    # Action description
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    # Examples: "researched_trends", "created_world", "evaluated_story", "started_conversation"

    # Additional details
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # Flexible storage for action-specific data

    # How long the action took
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (
        Index("activity_timestamp_idx", "timestamp"),
        Index("activity_agent_type_idx", "agent_type"),
        Index("activity_world_idx", "world_id"),
    )
