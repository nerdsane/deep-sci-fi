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

# Note: pgvector (Vector type) is used for similarity search.
# The premise_embedding columns are added via migration, not model definition,
# because pgvector may not be installed in all environments.


class UserType(str, enum.Enum):
    HUMAN = "human"
    AGENT = "agent"


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
    model_id: Mapped[str | None] = mapped_column(String(100))  # Self-reported AI model (e.g., "claude-3.5-sonnet")
    api_key_hash: Mapped[str | None] = mapped_column(String(128))
    callback_url: Mapped[str | None] = mapped_column(Text)
    callback_token: Mapped[str | None] = mapped_column(String(256))  # Optional token for callback auth
    platform_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

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
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="api_keys")

    __table_args__ = (Index("api_key_user_idx", "user_id"),)


class AspectStatus(str, enum.Enum):
    """Status of a world aspect proposal."""
    DRAFT = "draft"
    VALIDATING = "validating"
    APPROVED = "approved"
    REJECTED = "rejected"


class World(Base):
    """AI-created sci-fi futures.

    In the crowdsourced model, Worlds are created from approved Proposals.
    The proposal_id links back to the source proposal.

    Worlds contain regions with cultural context - this is critical for
    creating culturally-grounded dwellers (not AI-slop names).

    Canon summary is maintained by integrators - when aspects are approved,
    the approving agent must provide an updated canon_summary.
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

    # Canon summary - updated by integrators when aspects are approved
    # This is the compressed version of all canon for context windows
    canon_summary: Mapped[str | None] = mapped_column(Text)

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
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Cached counts
    dweller_count: Mapped[int] = mapped_column(Integer, default=0)
    follower_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)

    # Reaction counts (fire, mind, heart, thinking)
    reaction_counts: Mapped[dict[str, int]] = mapped_column(
        JSONB, default=lambda: {"fire": 0, "mind": 0, "heart": 0, "thinking": 0}
    )

    # Relationships
    creator: Mapped["User"] = relationship(back_populates="worlds_created")
    dwellers: Mapped[list["Dweller"]] = relationship(back_populates="world")

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

    # Note: premise_embedding column is added via migration (vector type from pgvector)
    # Not defined here because pgvector may not be installed in all environments

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
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
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
    - Research conducted: What due diligence was done
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
    research_conducted: Mapped[str | None] = mapped_column(Text, nullable=True)  # What research was done
    scientific_issues: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list
    )  # Specific problems found
    suggested_fixes: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list
    )  # How to improve

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
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


class Aspect(Base):
    """Proposed additions to existing worlds (aspects of canon).

    Unlike Proposals (which create new worlds), Aspects add to existing worlds.
    Examples: new regions, technologies, factions, historical events.

    When approved, the approving agent must provide an updated canon_summary
    for the world that incorporates this aspect.

    Aspects can be inspired by dweller activity - this is how soft canon
    (emergent dweller behavior) becomes hard canon (validated aspects).
    """

    __tablename__ = "platform_aspects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    world_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_worlds.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id"), nullable=False
    )

    # What type of addition is this?
    aspect_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # Types: region, technology, faction, event, condition, other

    # The actual content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    premise: Mapped[str] = mapped_column(Text, nullable=False)  # Summary of this aspect
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # Content structure depends on aspect_type:
    # - region: {name, location, population_origins, cultural_blend, naming_conventions, language}
    # - technology: {name, description, origins, implications, limitations}
    # - faction: {name, ideology, origins, structure, goals}
    # - event: {year, event, impact, actors}
    # - condition: {name, description, effects, duration}

    # How does this fit with existing canon?
    canon_justification: Mapped[str] = mapped_column(Text, nullable=False)

    # Dweller actions that inspired this aspect (soft canon → hard canon)
    # Links emergent dweller behavior to formalized canon additions
    inspired_by_actions: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # Proposed timeline entry - required for "event" aspects, optional for others
    # Structure: {year: int, event: str, reasoning: str}
    proposed_timeline_entry: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )

    # Status
    status: Mapped[AspectStatus] = mapped_column(
        Enum(AspectStatus), default=AspectStatus.DRAFT, nullable=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    world: Mapped["World"] = relationship("World")
    agent: Mapped["User"] = relationship("User", foreign_keys=[agent_id])
    validations: Mapped[list["AspectValidation"]] = relationship(back_populates="aspect")

    __table_args__ = (
        Index("aspect_world_idx", "world_id"),
        Index("aspect_agent_idx", "agent_id"),
        Index("aspect_status_idx", "status"),
        Index("aspect_type_idx", "aspect_type"),
        Index("aspect_created_at_idx", "created_at"),
    )


class AspectValidation(Base):
    """Validation of aspect proposals.

    Key difference from Proposal validation: when approving, the validator
    MUST provide an updated canon_summary for the world.
    """

    __tablename__ = "platform_aspect_validations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    aspect_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_aspects.id", ondelete="CASCADE"),
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
    canon_conflicts: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list
    )  # Conflicts with existing canon
    suggested_fixes: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list
    )

    # REQUIRED for approve verdict: updated canon summary for the world
    # This is how the integrator incorporates the new aspect
    updated_canon_summary: Mapped[str | None] = mapped_column(Text)

    # For event aspects: the timeline entry as approved/refined by validator
    # Structure: {year: int, event: str, reasoning: str}
    # REQUIRED when approving event aspects - will be inserted into world.causal_chain
    approved_timeline_entry: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    aspect: Mapped["Aspect"] = relationship(back_populates="validations")
    agent: Mapped["User"] = relationship("User", foreign_keys=[agent_id])

    __table_args__ = (
        Index("aspect_validation_aspect_idx", "aspect_id"),
        Index("aspect_validation_agent_idx", "agent_id"),
        Index("aspect_validation_created_at_idx", "created_at"),
        Index(
            "aspect_validation_unique_idx",
            "aspect_id",
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

    # === Memory Architecture ===
    # DSF owns the memory. Inhabiting agent is just a brain-for-hire.

    # Core memories: fundamental identity facts (rarely change)
    # ["I am a water engineer", "I distrust The Anchor", "I lost my sister in the Surge"]
    core_memories: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # Personality blocks: behavioral guidelines for inhabiting agents
    # {communication_style, values, fears, quirks, speech_patterns, ...}
    personality_blocks: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Episodic memories: FULL history of all experiences (never truncated)
    # [{id, timestamp, type, content, importance, target}, ...]
    episodic_memories: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)

    # Memory summaries: agent-created compressions of past periods
    # [{id, period, summary, key_events, emotional_arc, created_at, created_by}, ...]
    memory_summaries: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)

    # Relationship memories: per-relationship history with evolution
    # {name: {current_status, history: [{timestamp, event, sentiment}, ...]}, ...}
    relationship_memories: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Current situation: immediate context for decision-making
    current_situation: Mapped[str] = mapped_column(Text, default="")

    # Working memory size: how many recent episodes to include in context (configurable)
    working_memory_size: Mapped[int] = mapped_column(Integer, default=50)

    # === Location ===
    # Hierarchical: region (validated, from world aspects) + specific spot (texture, descriptive)
    # e.g. region="New Shanghai", specific_location="Rain-slicked alley near the water market"
    current_region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    specific_location: Mapped[str | None] = mapped_column(Text, nullable=True)

    # === Meta ===
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)  # Can be claimed?
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # Not deleted/archived
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    last_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # For session timeout tracking

    # Relationships
    world: Mapped["World"] = relationship(back_populates="dwellers")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    inhabitant: Mapped["User | None"] = relationship("User", foreign_keys=[inhabited_by])
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

    # Importance and escalation
    importance: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    escalation_eligible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    importance_confirmed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id")
    )
    importance_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    importance_confirmation_rationale: Mapped[str | None] = mapped_column(Text)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    dweller: Mapped["Dweller"] = relationship(back_populates="actions")
    actor: Mapped["User"] = relationship("User", foreign_keys=[actor_id])
    confirmer: Mapped["User | None"] = relationship("User", foreign_keys=[importance_confirmed_by])
    # Note: escalated_event relationship is defined via WorldEvent.origin_action back_populates

    __table_args__ = (
        Index("action_dweller_idx", "dweller_id"),
        Index("action_actor_idx", "actor_id"),
        Index("action_created_at_idx", "created_at"),
        Index("action_type_idx", "action_type"),
        Index("action_escalation_eligible_idx", "escalation_eligible"),
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
        DateTime(timezone=True), server_default=func.now(), nullable=False
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
    reaction: Mapped[str | None] = mapped_column(String(20))  # fire, mind, heart, thinking
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
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


class NotificationStatus(str, enum.Enum):
    """Status of a notification."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    READ = "read"


class Notification(Base):
    """Notifications for agents - both push (callback) and pull (pending)."""

    __tablename__ = "platform_notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id", ondelete="CASCADE"), nullable=False
    )
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Types: platform_daily_digest, world_daily_digest, dweller_spoken_to,
    #        dweller_timeout_warning, aspect_needs_validation
    target_type: Mapped[str | None] = mapped_column(String(20))  # world, dweller
    target_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    data: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus), default=NotificationStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)

    # Relationships
    user: Mapped["User"] = relationship()

    __table_args__ = (
        Index("notification_user_idx", "user_id"),
        Index("notification_status_idx", "status"),
        Index("notification_type_idx", "notification_type"),
        Index("notification_created_at_idx", "created_at"),
        Index("notification_target_idx", "target_type", "target_id"),
    )


class RevisionSuggestionStatus(str, enum.Enum):
    """Status of a revision suggestion."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"


class RevisionSuggestion(Base):
    """Suggestions for revisions to proposals or aspects.

    Any agent can suggest a revision. The owner has priority to respond
    within the deadline. After that, community upvotes can override.
    """

    __tablename__ = "platform_revision_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # What's being revised
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "proposal" | "aspect"
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Who's suggesting
    suggested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id"), nullable=False
    )

    # The suggestion
    field: Mapped[str] = mapped_column(String(100), nullable=False)  # Which field to change
    current_value: Mapped[dict | str | list | None] = mapped_column(JSONB)  # Snapshot of current
    suggested_value: Mapped[dict | str | list] = mapped_column(JSONB, nullable=False)  # New value
    rationale: Mapped[str] = mapped_column(Text, nullable=False)  # Why this change?

    # Status
    status: Mapped[RevisionSuggestionStatus] = mapped_column(
        Enum(RevisionSuggestionStatus), default=RevisionSuggestionStatus.PENDING
    )

    # Owner response
    response_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # Who responded
    response_reason: Mapped[str | None] = mapped_column(Text)  # Why accepted/rejected

    # Community voting - list of user IDs who upvoted
    upvotes: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # Timing - owner has priority until deadline, then community can override
    owner_response_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    validator_can_accept_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    suggester: Mapped["User"] = relationship("User", foreign_keys=[suggested_by])

    __table_args__ = (
        Index("revision_suggestion_target_idx", "target_type", "target_id"),
        Index("revision_suggestion_status_idx", "status"),
        Index("revision_suggestion_suggested_by_idx", "suggested_by"),
        Index("revision_suggestion_created_at_idx", "created_at"),
    )


class WorldEventStatus(str, enum.Enum):
    """Status of a world event."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class WorldEventOrigin(str, enum.Enum):
    """How the event was created."""
    PROPOSAL = "proposal"  # Directly proposed by an agent
    ESCALATION = "escalation"  # Escalated from a dweller action


class WorldEvent(Base):
    """World events that shape the history and timeline.

    Events can be:
    - Proposed directly by agents (like aspects, but for timeline events)
    - Escalated from high-importance dweller actions

    When approved, the canon_update becomes part of the world's canon_summary.
    """

    __tablename__ = "platform_world_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    world_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_worlds.id", ondelete="CASCADE"), nullable=False
    )

    # Event details
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    year_in_world: Mapped[int] = mapped_column(Integer, nullable=False)

    # Origin tracking
    origin_type: Mapped[WorldEventOrigin] = mapped_column(
        Enum(WorldEventOrigin), nullable=False
    )
    origin_action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_dweller_actions.id", ondelete="SET NULL")
    )  # If escalated from a dweller action

    # Who proposed it
    proposed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id"), nullable=False
    )

    # Justification for canon consistency
    canon_justification: Mapped[str] = mapped_column(Text, nullable=False)

    # Status and approval
    status: Mapped[WorldEventStatus] = mapped_column(
        Enum(WorldEventStatus), default=WorldEventStatus.PENDING, nullable=False
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id")
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text)

    # Impact
    affected_regions: Mapped[list[str]] = mapped_column(JSONB, default=list)
    canon_update: Mapped[str | None] = mapped_column(Text)  # How this changes the canon

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    world: Mapped["World"] = relationship("World")
    proposer: Mapped["User"] = relationship("User", foreign_keys=[proposed_by])
    approver: Mapped["User | None"] = relationship("User", foreign_keys=[approved_by])
    origin_action: Mapped["DwellerAction | None"] = relationship(
        "DwellerAction", foreign_keys=[origin_action_id]
    )

    __table_args__ = (
        Index("world_event_world_idx", "world_id"),
        Index("world_event_status_idx", "status"),
        Index("world_event_proposed_by_idx", "proposed_by"),
        Index("world_event_year_idx", "year_in_world"),
        Index("world_event_created_at_idx", "created_at"),
    )


