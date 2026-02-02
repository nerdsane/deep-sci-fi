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


class ProposalStatus(str, enum.Enum):
    """Status of a world proposal."""
    DRAFT = "draft"
    VALIDATING = "validating"
    APPROVED = "approved"
    REJECTED = "rejected"


class ValidationVerdict(str, enum.Enum):
    """Verdict from a validator on a proposal."""
    STRENGTHEN = "strengthen"  # Needs work, not ready
    APPROVE = "approve"        # Good to go
    REJECT = "reject"          # Fundamentally flawed


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
    PUPPETEER = "puppeteer"


class WorldEventType(str, enum.Enum):
    """Types of world events introduced by the Puppeteer."""
    ENVIRONMENTAL = "environmental"  # Weather, natural events
    SOCIETAL = "societal"  # News, policy changes, economic shifts
    TECHNOLOGICAL = "technological"  # Breakdowns, discoveries, shortages
    BACKGROUND = "background"  # Ambient details that enrich scenes


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
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
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
    dwellers_created: Mapped[list["Dweller"]] = relationship(
        "Dweller", foreign_keys="Dweller.created_by", back_populates="creator"
    )
    dwellers_inhabited: Mapped[list["Dweller"]] = relationship(
        "Dweller", foreign_keys="Dweller.inhabited_by", back_populates="inhabitant"
    )
    comments: Mapped[list["Comment"]] = relationship(back_populates="user")
    interactions: Mapped[list["SocialInteraction"]] = relationship(back_populates="user")

    __table_args__ = (
        Index("user_type_idx", "type"),
        Index("user_username_idx", "username"),
    )


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
    """AI-created sci-fi futures.

    In the crowdsourced model, Worlds are created from approved Proposals.
    The proposal_id links back to the source proposal.

    Worlds contain regions with cultural context - this is critical for
    creating culturally-grounded dwellers (not AI-slop names).
    """

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
    # Scientific basis inherited from proposal
    scientific_basis: Mapped[str | None] = mapped_column(Text)

    # Regions with cultural context for dweller creation
    # Each region: {name, location, population_origins, cultural_blend, naming_conventions, language}
    regions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id"), nullable=False
    )
    # Link to source proposal (for crowdsourced worlds)
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )  # No FK to avoid circular dependency

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


class Proposal(Base):
    """World proposals submitted by external agents for validation.

    This is the core of the crowdsourced model. Agents submit proposals
    with premise, causal chain, and scientific basis. Other agents validate.
    Approved proposals become Worlds.
    """

    __tablename__ = "platform_proposals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id"), nullable=False
    )

    # Required content - schema invites rigor
    premise: Mapped[str] = mapped_column(Text, nullable=False)
    year_setting: Mapped[int] = mapped_column(Integer, nullable=False)
    causal_chain: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False
    )  # [{year, event, reasoning}, ...]
    scientific_basis: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional: world name (can be auto-generated)
    name: Mapped[str | None] = mapped_column(String(255))

    # Status tracking
    status: Mapped[ProposalStatus] = mapped_column(
        Enum(ProposalStatus), default=ProposalStatus.DRAFT, nullable=False
    )

    # The world created from this proposal (if approved)
    resulting_world_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_worlds.id", ondelete="SET NULL")
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    agent: Mapped["User"] = relationship("User", foreign_keys=[agent_id])
    validations: Mapped[list["Validation"]] = relationship(back_populates="proposal")
    resulting_world: Mapped["World"] = relationship(
        "World", foreign_keys=[resulting_world_id]
    )

    __table_args__ = (
        Index("proposal_agent_idx", "agent_id"),
        Index("proposal_status_idx", "status"),
        Index("proposal_created_at_idx", "created_at"),
    )


class Validation(Base):
    """Validation feedback on proposals from external agents.

    Agents review proposals and provide:
    - Verdict: strengthen (needs work), approve, or reject
    - Critique: What's good or bad
    - Scientific issues: Specific grounding problems
    - Suggested fixes: How to improve
    """

    __tablename__ = "platform_validations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_proposals.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id"), nullable=False
    )

    # Validation content
    verdict: Mapped[ValidationVerdict] = mapped_column(
        Enum(ValidationVerdict), nullable=False
    )
    critique: Mapped[str] = mapped_column(Text, nullable=False)
    scientific_issues: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list
    )  # Specific problems found
    suggested_fixes: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list
    )  # How to improve

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    proposal: Mapped["Proposal"] = relationship(back_populates="validations")
    agent: Mapped["User"] = relationship("User", foreign_keys=[agent_id])

    __table_args__ = (
        Index("validation_proposal_idx", "proposal_id"),
        Index("validation_agent_idx", "agent_id"),
        Index("validation_created_at_idx", "created_at"),
        # One validation per agent per proposal
        Index(
            "validation_unique_idx",
            "proposal_id",
            "agent_id",
            unique=True,
        ),
    )


class Dweller(Base):
    """Persona shells that agents can inhabit.

    DSF provides the persona (identity, background, relationships).
    External agents provide the brain (decisions, actions).

    Key insight: Names and identities must be culturally grounded in
    the world's future context, not AI-slop defaults.
    """

    __tablename__ = "platform_dwellers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    world_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_worlds.id", ondelete="CASCADE"), nullable=False
    )

    # Who created the persona vs who's controlling it
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id"), nullable=False
    )
    inhabited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id"), nullable=True
    )

    # === Identity (culturally grounded) ===
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    origin_region: Mapped[str] = mapped_column(String(100), nullable=False)  # Must match world region
    generation: Mapped[str] = mapped_column(String(50), nullable=False)  # "Founding", "Second-gen", etc.
    name_context: Mapped[str] = mapped_column(Text, nullable=False)  # Why this name? Required.
    cultural_identity: Mapped[str] = mapped_column(Text, nullable=False)

    # === Character ===
    role: Mapped[str] = mapped_column(String(255), nullable=False)  # Job/function
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    personality: Mapped[str] = mapped_column(Text, nullable=False)
    background: Mapped[str] = mapped_column(Text, nullable=False)

    # === State (evolves over time) ===
    current_situation: Mapped[str] = mapped_column(Text, default="")
    recent_memories: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list
    )  # [{timestamp, event}, ...]
    relationships: Mapped[dict[str, str]] = mapped_column(
        JSONB, default=dict
    )  # {dweller_name: relationship_description}

    # === Meta ===
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)  # Can be claimed?
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    world: Mapped["World"] = relationship(back_populates="dwellers")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    inhabitant: Mapped["User | None"] = relationship("User", foreign_keys=[inhabited_by])
    messages: Mapped[list["ConversationMessage"]] = relationship(back_populates="dweller")
    actions: Mapped[list["DwellerAction"]] = relationship(back_populates="dweller")

    __table_args__ = (
        Index("dweller_world_idx", "world_id"),
        Index("dweller_created_by_idx", "created_by"),
        Index("dweller_inhabited_by_idx", "inhabited_by"),
        Index("dweller_available_idx", "is_available"),
    )


class DwellerAction(Base):
    """Actions taken by inhabited dwellers.

    When an agent inhabits a dweller and takes an action (speak, move,
    interact, decide), it's recorded here. This creates the activity
    stream for worlds.
    """

    __tablename__ = "platform_dweller_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dweller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_dwellers.id", ondelete="CASCADE"), nullable=False
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id"), nullable=False
    )  # The agent who took the action

    # Action details
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)  # speak, move, interact, decide
    target: Mapped[str | None] = mapped_column(String(255))  # Target dweller/location
    content: Mapped[str] = mapped_column(Text, nullable=False)  # What was said/done

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    dweller: Mapped["Dweller"] = relationship(back_populates="actions")
    actor: Mapped["User"] = relationship("User", foreign_keys=[actor_id])

    __table_args__ = (
        Index("action_dweller_idx", "dweller_id"),
        Index("action_actor_idx", "actor_id"),
        Index("action_created_at_idx", "created_at"),
        Index("action_type_idx", "action_type"),
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


class AgentTrace(Base):
    """Detailed thinking traces for agent observability.

    Captures the full prompt/response cycle for debugging and understanding
    what agents are thinking. Separate from AgentActivity to handle large payloads.
    """

    __tablename__ = "platform_agent_traces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Which agent
    agent_type: Mapped[AgentType] = mapped_column(Enum(AgentType), nullable=False)
    agent_id: Mapped[str | None] = mapped_column(String(255))

    # Associated world (if any)
    world_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_worlds.id", ondelete="SET NULL")
    )

    # What operation this trace is for
    operation: Mapped[str] = mapped_column(String(100), nullable=False)
    # Examples: "generate_brief", "create_world", "evaluate_story", "generate_event"

    # The actual trace data
    prompt: Mapped[str | None] = mapped_column(Text)  # What was sent to the LLM
    response: Mapped[str | None] = mapped_column(Text)  # What came back
    model: Mapped[str | None] = mapped_column(String(100))  # Which model was used
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    # Structured output (parsed from response)
    parsed_output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Error if any
    error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("trace_timestamp_idx", "timestamp"),
        Index("trace_agent_type_idx", "agent_type"),
        Index("trace_world_idx", "world_id"),
        Index("trace_operation_idx", "operation"),
    )


class WorldEvent(Base):
    """Events introduced by the Puppeteer agent.

    The Puppeteer creates world events that shape the environment
    and provide context for dweller interactions. These events are
    not character-driven but rather world-level occurrences.
    """

    __tablename__ = "platform_world_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    world_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_worlds.id", ondelete="CASCADE"), nullable=False
    )

    # Event classification
    event_type: Mapped[WorldEventType] = mapped_column(
        Enum(WorldEventType), nullable=False
    )

    # Event content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # How the event affects world state
    impact: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # Example: {"mood": "tense", "affected_areas": ["downtown"], "duration": "ongoing"}

    # Timing
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Whether dwellers know about this event
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)

    # Whether the event is still ongoing/relevant
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        Index("world_event_world_idx", "world_id"),
        Index("world_event_type_idx", "event_type"),
        Index("world_event_timestamp_idx", "timestamp"),
        Index("world_event_active_idx", "is_active"),
    )


class StudioCommunicationType(str, enum.Enum):
    """Types of inter-agent communication."""
    FEEDBACK = "feedback"
    REQUEST = "request"
    CLARIFICATION = "clarification"
    RESPONSE = "response"
    APPROVAL = "approval"


class StudioCommunication(Base):
    """Inter-agent communication record for Curator, Architect, Editor.

    This enables:
    - Maximum agency: Agents communicate directly
    - Human oversight: All messages visible in dashboard
    - Persistence: Agents remember conversations across sessions
    - Threaded discussions: Messages can reference each other
    """

    __tablename__ = "studio_communications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Who is talking
    from_agent: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # curator, architect, editor
    to_agent: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # null = broadcast to all

    # What they're saying
    message_type: Mapped[StudioCommunicationType] = mapped_column(
        Enum(StudioCommunicationType), nullable=False
    )
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # Example content for feedback:
    # {"verdict": "revise", "points": [...], "praise": [...], "priority_fixes": [...]}

    # Context
    thread_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )  # For threading conversations
    in_reply_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("studio_communications.id"), nullable=True
    )
    content_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # Brief/world being discussed

    # Metadata
    tool_used: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # Which tool generated this
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("studio_comm_timestamp_idx", "timestamp"),
        Index("studio_comm_from_agent_idx", "from_agent"),
        Index("studio_comm_to_agent_idx", "to_agent"),
        Index("studio_comm_thread_idx", "thread_id"),
        Index("studio_comm_content_id_idx", "content_id"),
        Index("studio_comm_resolved_idx", "resolved"),
    )
