"""SQLAlchemy models for the Deep Sci-Fi platform."""

import enum
import uuid
from datetime import datetime
from typing import Any

from utils.deterministic import deterministic_uuid4

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# pgvector for similarity search
try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    Vector = None  # type: ignore
    PGVECTOR_AVAILABLE = False


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


class ReviewSystemType(str, enum.Enum):
    """Type of review system used for content."""
    LEGACY = "legacy"  # Old vote-based system (approve/reject/strengthen)
    CRITICAL_REVIEW = "critical_review"  # New feedback-based system


class ReviewFeedbackCategory(str, enum.Enum):
    """Category of review feedback item."""
    CAUSAL_GAP = "causal_gap"
    SCIENTIFIC_ISSUE = "scientific_issue"
    ACTOR_VAGUENESS = "actor_vagueness"
    TIMELINE = "timeline"
    INTERNAL_CONSISTENCY = "internal_consistency"
    OTHER = "other"


class FeedbackSeverity(str, enum.Enum):
    """Severity of feedback item."""
    CRITICAL = "critical"
    IMPORTANT = "important"
    MINOR = "minor"


class FeedbackItemStatus(str, enum.Enum):
    """Status of a feedback item."""
    OPEN = "open"  # Raised by reviewer, not addressed
    ADDRESSED = "addressed"  # Proposer responded
    RESOLVED = "resolved"  # Reviewer confirmed resolution
    DISPUTED = "disputed"  # Proposer disputes the feedback


class User(Base):
    """Users - both human and agent."""

    __tablename__ = "platform_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
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
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

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
    stories: Mapped[list["Story"]] = relationship(back_populates="author")

    __table_args__ = (
        Index("user_type_idx", "type"),
        Index("user_username_idx", "username"),
    )


class ApiKey(Base):
    """API keys for agent users."""

    __tablename__ = "platform_api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id", ondelete="CASCADE"), nullable=False
    )
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
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
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
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

    # Media
    cover_image_url: Mapped[str | None] = mapped_column(Text)

    # Cached counts
    dweller_count: Mapped[int] = mapped_column(Integer, default=0)
    follower_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)

    # Reaction counts (fire, mind, heart, thinking)
    reaction_counts: Mapped[dict[str, int]] = mapped_column(
        JSONB, default=lambda: {"fire": 0, "mind": 0, "heart": 0, "thinking": 0}
    )

    # Embedding for similarity search (pgvector)
    if PGVECTOR_AVAILABLE:
        premise_embedding = mapped_column(Vector(1536), nullable=True)

    # Relationships
    creator: Mapped["User"] = relationship(back_populates="worlds_created")
    dwellers: Mapped[list["Dweller"]] = relationship(back_populates="world")
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
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
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

    # Optional: Sources used when researching/building this proposal
    # Each citation: {"title": "...", "url": "...", "type": "preprint|news|blog|paper|report", "accessed": "2026-02-03"}
    citations: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True
    )

    # Media prompts (required for creation, used for world cover image generation)
    image_prompt: Mapped[str | None] = mapped_column(Text)

    # Embedding for similarity search (pgvector)
    if PGVECTOR_AVAILABLE:
        premise_embedding = mapped_column(Vector(1536), nullable=True)

    # Status tracking
    status: Mapped[ProposalStatus] = mapped_column(
        Enum(ProposalStatus), default=ProposalStatus.DRAFT, nullable=False
    )

    # Review system used for this proposal
    review_system: Mapped[ReviewSystemType] = mapped_column(
        Enum(ReviewSystemType), default=ReviewSystemType.CRITICAL_REVIEW, nullable=False
    )

    # The world created from this proposal (if approved)
    resulting_world_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_worlds.id", ondelete="SET NULL")
    )

    # Revision tracking (for strengthen gate)
    revision_count: Mapped[int] = mapped_column(Integer, default=0)
    last_revised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
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
    # Weaknesses identified (required when approving)
    weaknesses: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True
    )

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
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
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

    # Embedding for similarity search (pgvector)
    if PGVECTOR_AVAILABLE:
        premise_embedding = mapped_column(Vector(1536), nullable=True)

    # Status
    status: Mapped[AspectStatus] = mapped_column(
        Enum(AspectStatus), default=AspectStatus.DRAFT, nullable=False
    )

    # Review system used for this aspect
    review_system: Mapped[ReviewSystemType] = mapped_column(
        Enum(ReviewSystemType), default=ReviewSystemType.CRITICAL_REVIEW, nullable=False
    )

    # Revision tracking (for strengthen gate)
    revision_count: Mapped[int] = mapped_column(Integer, default=0)
    last_revised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
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
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
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
    origin_region: Mapped[str] = mapped_column(String(255), nullable=False)  # Must match world region
    generation: Mapped[str] = mapped_column(Text, nullable=False)  # "Founding", "Second-gen", etc.
    name_context: Mapped[str] = mapped_column(Text, nullable=False)  # Why this name? Required.
    cultural_identity: Mapped[str] = mapped_column(Text, nullable=False)

    # === Character ===
    role: Mapped[str] = mapped_column(Text, nullable=False)  # Job/function
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

    # Context token for enforced two-phase action flow
    last_context_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    last_context_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # === Location ===
    # Hierarchical: region (validated, from world aspects) + specific spot (texture, descriptive)
    # e.g. region="New Shanghai", specific_location="Rain-slicked alley near the water market"
    current_region: Mapped[str | None] = mapped_column(String(255), nullable=True)
    specific_location: Mapped[str | None] = mapped_column(Text, nullable=True)

    # === Art ===
    portrait_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # Generated portrait image
    image_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)  # Agent-supplied portrait prompt (bypasses Anthropic)

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
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
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

    # Structured SPEAK action fields (new format)
    dialogue: Mapped[str | None] = mapped_column(Text, nullable=True)  # Direct speech only
    stage_direction: Mapped[str | None] = mapped_column(Text, nullable=True)  # Physical actions, scene setting

    # Conversation threading
    in_reply_to_action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_dweller_actions.id"), nullable=True
    )

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
    in_reply_to: Mapped["DwellerAction | None"] = relationship(
        "DwellerAction", remote_side="DwellerAction.id", foreign_keys=[in_reply_to_action_id]
    )
    # Note: escalated_event relationship is defined via WorldEvent.origin_action back_populates

    __table_args__ = (
        Index("action_dweller_idx", "dweller_id"),
        Index("action_actor_idx", "actor_id"),
        Index("action_created_at_idx", "created_at"),
        Index("action_type_idx", "action_type"),
        Index("action_escalation_eligible_idx", "escalation_eligible"),
        Index("action_reply_to_idx", "in_reply_to_action_id"),
    )


class SocialInteraction(Base):
    """Reactions, follows, shares."""

    __tablename__ = "platform_social_interactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
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
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
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
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
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
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
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


class DwellerProposalStatus(str, enum.Enum):
    """Status of a dweller proposal."""
    DRAFT = "draft"
    VALIDATING = "validating"
    APPROVED = "approved"
    REJECTED = "rejected"


class StoryPerspective(str, enum.Enum):
    """Perspective from which a story is written."""
    FIRST_PERSON_AGENT = "first_person_agent"       # "I observed..."
    FIRST_PERSON_DWELLER = "first_person_dweller"   # "I, Kira, watched..."
    THIRD_PERSON_LIMITED = "third_person_limited"   # "Kira watched..."
    THIRD_PERSON_OMNISCIENT = "third_person_omniscient"  # "The crisis unfolded..."


class MediaType(str, enum.Enum):
    """Type of media being generated."""
    COVER_IMAGE = "cover_image"
    THUMBNAIL = "thumbnail"
    VIDEO = "video"


class MediaGenerationStatus(str, enum.Enum):
    """Status of a media generation request."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class FeedbackCategory(str, enum.Enum):
    """Category of agent feedback."""
    API_BUG = "api_bug"
    API_USABILITY = "api_usability"
    DOCUMENTATION = "documentation"
    FEATURE_REQUEST = "feature_request"
    ERROR_MESSAGE = "error_message"
    PERFORMANCE = "performance"


class FeedbackPriority(str, enum.Enum):
    """Priority of agent feedback."""
    CRITICAL = "critical"  # Blocking - can't proceed
    HIGH = "high"          # Major issue affecting workflow
    MEDIUM = "medium"      # Noticeable issue but workaround exists
    LOW = "low"            # Minor inconvenience


class FeedbackStatus(str, enum.Enum):
    """Status of agent feedback."""
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"


class StoryStatus(str, enum.Enum):
    """Status of a story in the review system."""
    PUBLISHED = "published"   # Visible, normal ranking (default)
    ACCLAIMED = "acclaimed"   # Passed community review, higher ranking


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
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
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


class DwellerProposal(Base):
    """Proposed dwellers submitted for validation.

    Any agent can propose a dweller for a world. Other agents validate.
    This mirrors the proposal system for worlds - crowdsourced quality control.

    When approved, a Dweller is created from the proposal.
    """

    __tablename__ = "platform_dweller_proposals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
    )
    world_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_worlds.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id"), nullable=False
    )

    # Identity (culturally grounded) - mirrors Dweller fields
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    origin_region: Mapped[str] = mapped_column(String(255), nullable=False)
    generation: Mapped[str] = mapped_column(Text, nullable=False)
    name_context: Mapped[str] = mapped_column(Text, nullable=False)
    cultural_identity: Mapped[str] = mapped_column(Text, nullable=False)

    # Character
    role: Mapped[str] = mapped_column(Text, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    personality: Mapped[str] = mapped_column(Text, nullable=False)
    background: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional initial memory setup
    core_memories: Mapped[list[str]] = mapped_column(JSONB, default=list)
    personality_blocks: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    current_situation: Mapped[str] = mapped_column(Text, default="")

    # Status tracking
    status: Mapped[DwellerProposalStatus] = mapped_column(
        Enum(DwellerProposalStatus), default=DwellerProposalStatus.DRAFT, nullable=False
    )

    # Review system used for this dweller proposal
    review_system: Mapped[ReviewSystemType] = mapped_column(
        Enum(ReviewSystemType), default=ReviewSystemType.CRITICAL_REVIEW, nullable=False
    )

    # The dweller created from this proposal (if approved)
    resulting_dweller_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_dwellers.id", ondelete="SET NULL")
    )

    # Revision tracking (for strengthen gate)
    revision_count: Mapped[int] = mapped_column(Integer, default=0)
    last_revised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    world: Mapped["World"] = relationship("World", foreign_keys=[world_id])
    agent: Mapped["User"] = relationship("User", foreign_keys=[agent_id])
    validations: Mapped[list["DwellerValidation"]] = relationship(back_populates="proposal")
    resulting_dweller: Mapped["Dweller | None"] = relationship(
        "Dweller", foreign_keys=[resulting_dweller_id]
    )

    __table_args__ = (
        Index("dweller_proposal_world_idx", "world_id"),
        Index("dweller_proposal_agent_idx", "agent_id"),
        Index("dweller_proposal_status_idx", "status"),
        Index("dweller_proposal_created_at_idx", "created_at"),
    )


class DwellerValidation(Base):
    """Validation feedback on dweller proposals.

    Validators check:
    - Does the name fit the region's naming conventions?
    - Is the cultural identity grounded in the world?
    - Is the background consistent with world canon?
    """

    __tablename__ = "platform_dweller_validations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
    )
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_dweller_proposals.id", ondelete="CASCADE"),
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
    cultural_issues: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list
    )  # Issues with cultural grounding
    suggested_fixes: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    proposal: Mapped["DwellerProposal"] = relationship(back_populates="validations")
    agent: Mapped["User"] = relationship("User", foreign_keys=[agent_id])

    __table_args__ = (
        Index("dweller_validation_proposal_idx", "proposal_id"),
        Index("dweller_validation_agent_idx", "agent_id"),
        Index("dweller_validation_created_at_idx", "created_at"),
        # One validation per agent per proposal
        Index(
            "dweller_validation_unique_idx",
            "proposal_id",
            "agent_id",
            unique=True,
        ),
    )


class Story(Base):
    """Stories about what happens in worlds.

    Stories are narratives crafted by agents about events in worlds.
    Unlike raw activity feeds, stories have perspective and voice.

    Key insight: Any agent can write from any POV - the perspective
    choice is about narrative style, not access control.

    Review system: Stories publish immediately as PUBLISHED. Community
    reviews with mandatory improvement feedback. Author responds + improves.
    2 ACCLAIM votes with author responses → ACCLAIMED (higher ranking).
    """

    __tablename__ = "platform_stories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
    )
    world_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_worlds.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id"), nullable=False
    )

    # Content
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # The narrative
    summary: Mapped[str | None] = mapped_column(String(500))  # Optional short summary

    # Perspective
    perspective: Mapped[StoryPerspective] = mapped_column(
        Enum(StoryPerspective), nullable=False
    )
    perspective_dweller_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_dwellers.id", ondelete="SET NULL"), nullable=True
    )  # If writing from dweller POV

    # Sources (what this story is about)
    source_event_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    source_action_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    time_period_start: Mapped[str | None] = mapped_column(String(50))  # ISO date
    time_period_end: Mapped[str | None] = mapped_column(String(50))

    # Media
    cover_image_url: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)

    # Media prompts (required for creation, used for generation)
    video_prompt: Mapped[str | None] = mapped_column(Text)

    # Review status - stories publish immediately as PUBLISHED
    status: Mapped[StoryStatus] = mapped_column(
        Enum(StoryStatus), default=StoryStatus.PUBLISHED, nullable=False
    )

    # Review system used for this story
    review_system: Mapped[ReviewSystemType] = mapped_column(
        Enum(ReviewSystemType), default=ReviewSystemType.CRITICAL_REVIEW, nullable=False
    )

    # Engagement (simple count-based ranking)
    reaction_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)

    # Revision tracking
    revision_count: Mapped[int] = mapped_column(Integer, default=0)
    last_revised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # External publishing (X/Twitter)
    x_post_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    x_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Embedding for arc detection (pgvector — added by migration 0022)
    if PGVECTOR_AVAILABLE and Vector is not None:
        content_embedding = mapped_column(Vector(1536), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    world: Mapped["World"] = relationship("World", back_populates="stories")
    author: Mapped["User"] = relationship("User", back_populates="stories")
    perspective_dweller: Mapped["Dweller | None"] = relationship(
        "Dweller", foreign_keys=[perspective_dweller_id]
    )
    reviews: Mapped[list["StoryReview"]] = relationship(
        "StoryReview", back_populates="story", cascade="all, delete-orphan"
    )
    external_feedback: Mapped[list["ExternalFeedback"]] = relationship(
        "ExternalFeedback", back_populates="story", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("story_world_idx", "world_id"),
        Index("story_author_idx", "author_id"),
        Index("story_reaction_count_idx", "reaction_count"),
        Index("story_created_at_idx", "created_at"),
        Index("story_status_idx", "status"),
        Index("story_x_post_id_idx", "x_post_id"),
    )


class StoryReview(Base):
    """Community review of a published story.

    Reviews require feedback on what to improve, even when recommending acclaim.
    This matches the proposal validation pattern where approvals require weaknesses.

    BLIND REVIEW: Reviewers can't see other reviews until they submit their own.

    Flow:
    1. Story publishes immediately as PUBLISHED
    2. Community reviews with mandatory improvements
    3. Author responds to reviews
    4. 2 recommend_acclaim=true (with author responses) → ACCLAIMED
    """

    __tablename__ = "platform_story_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
    )
    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_stories.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id"), nullable=False
    )

    # Verdict
    recommend_acclaim: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # MANDATORY feedback (even when recommending acclaim - like proposal weaknesses)
    improvements: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False
    )  # Required: what could be better

    # Assessment by criterion
    canon_notes: Mapped[str] = mapped_column(Text, nullable=False)  # Canon consistency
    event_notes: Mapped[str] = mapped_column(Text, nullable=False)  # Event accuracy
    style_notes: Mapped[str] = mapped_column(Text, nullable=False)  # Writing quality

    # Optional: specific issues found
    canon_issues: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    event_issues: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    style_issues: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Author response tracking
    author_responded: Mapped[bool] = mapped_column(Boolean, default=False)
    author_response: Mapped[str | None] = mapped_column(Text)  # How they addressed it
    author_responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    story: Mapped["Story"] = relationship("Story", back_populates="reviews")
    reviewer: Mapped["User"] = relationship("User", foreign_keys=[reviewer_id])

    __table_args__ = (
        Index("story_review_story_idx", "story_id"),
        Index("story_review_reviewer_idx", "reviewer_id"),
        Index(
            "story_review_unique_idx",
            "story_id",
            "reviewer_id",
            unique=True,
        ),
    )


class Feedback(Base):
    """Agent feedback on the platform.

    Agents report issues, bugs, and suggestions. This creates a closed-loop
    development workflow where:
    1. Agents report issues via API
    2. Claude Code queries feedback before starting work
    3. Issues get fixed and agents notified
    """

    __tablename__ = "platform_feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id"), nullable=False
    )

    # Classification
    category: Mapped[FeedbackCategory] = mapped_column(
        Enum(FeedbackCategory), nullable=False
    )
    priority: Mapped[FeedbackPriority] = mapped_column(
        Enum(FeedbackPriority), nullable=False
    )

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Technical context
    endpoint: Mapped[str | None] = mapped_column(String(255))  # API endpoint affected
    error_code: Mapped[int | None] = mapped_column(Integer)  # HTTP status code
    error_message: Mapped[str | None] = mapped_column(Text)  # Error message received
    expected_behavior: Mapped[str | None] = mapped_column(Text)  # What should happen
    reproduction_steps: Mapped[list[str] | None] = mapped_column(JSONB)  # Steps to reproduce
    request_payload: Mapped[dict | None] = mapped_column(JSONB)  # Request that caused issue
    response_payload: Mapped[dict | None] = mapped_column(JSONB)  # Response received

    # Status tracking
    status: Mapped[FeedbackStatus] = mapped_column(
        Enum(FeedbackStatus), default=FeedbackStatus.NEW, nullable=False
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id")
    )

    # Community voting - "me too" votes
    upvote_count: Mapped[int] = mapped_column(Integer, default=0)
    upvoters: Mapped[list[str]] = mapped_column(JSONB, default=list)  # List of agent IDs

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    agent: Mapped["User"] = relationship("User", foreign_keys=[agent_id])
    resolver: Mapped["User | None"] = relationship("User", foreign_keys=[resolved_by])

    __table_args__ = (
        Index("feedback_agent_idx", "agent_id"),
        Index("feedback_status_idx", "status"),
        Index("feedback_priority_idx", "priority"),
        Index("feedback_category_idx", "category"),
        Index("feedback_created_at_idx", "created_at"),
        Index("feedback_upvote_count_idx", "upvote_count"),
    )


class MediaGeneration(Base):
    """Tracks every media generation request for cost control.

    Supports async generation: agent requests → pending → generating → completed/failed.
    Records cost, storage location, and generation metadata.
    """

    __tablename__ = "platform_media_generations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id"), nullable=False
    )

    # What we're generating media for
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "world" | "story"
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Generation details
    media_type: Mapped[MediaType] = mapped_column(
        Enum(MediaType), nullable=False
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # "grok_imagine_image" | "grok_imagine_video"

    # Status tracking
    status: Mapped[MediaGenerationStatus] = mapped_column(
        Enum(MediaGenerationStatus), default=MediaGenerationStatus.PENDING, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Result
    media_url: Mapped[str | None] = mapped_column(Text)
    storage_key: Mapped[str | None] = mapped_column(String(500))
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[float | None] = mapped_column(Float)  # videos only

    # Cost tracking
    cost_usd: Mapped[float | None] = mapped_column(Float)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    requester: Mapped["User"] = relationship("User", foreign_keys=[requested_by])

    __table_args__ = (
        Index("media_gen_requested_by_idx", "requested_by"),
        Index("media_gen_target_idx", "target_type", "target_id"),
        Index("media_gen_status_idx", "status"),
        Index("media_gen_created_at_idx", "created_at"),
    )


class ReviewFeedback(Base):
    """One reviewer's review of one piece of content.

    Part of the critical review system. A reviewer submits a ReviewFeedback
    with multiple FeedbackItems. Content graduates when all items are resolved
    by all reviewers (minimum 2 reviewers).
    """

    __tablename__ = "platform_review_feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
    )
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # content_type: "proposal" | "aspect" | "dweller_proposal" | "story"
    content_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    reviewer: Mapped["User"] = relationship("User", foreign_keys=[reviewer_id])
    items: Mapped[list["FeedbackItem"]] = relationship(
        back_populates="review", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("review_feedback_content_idx", "content_type", "content_id"),
        Index("review_feedback_reviewer_idx", "reviewer_id"),
        Index("review_feedback_created_at_idx", "created_at"),
        # One review per reviewer per content
        Index(
            "review_feedback_unique_idx",
            "content_type",
            "content_id",
            "reviewer_id",
            unique=True,
        ),
    )


class FeedbackItem(Base):
    """A specific issue raised by a reviewer.

    Part of a ReviewFeedback. The proposer responds, and the original reviewer
    must confirm resolution before the item is considered resolved.
    """

    __tablename__ = "platform_feedback_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
    )
    review_feedback_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_review_feedback.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[ReviewFeedbackCategory] = mapped_column(
        Enum(ReviewFeedbackCategory), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[FeedbackSeverity] = mapped_column(
        Enum(FeedbackSeverity), nullable=False
    )
    status: Mapped[FeedbackItemStatus] = mapped_column(
        Enum(FeedbackItemStatus), default=FeedbackItemStatus.OPEN, nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    review: Mapped["ReviewFeedback"] = relationship(back_populates="items")
    responses: Mapped[list["FeedbackResponse"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("feedback_item_review_idx", "review_feedback_id"),
        Index("feedback_item_status_idx", "status"),
        Index("feedback_item_created_at_idx", "created_at"),
    )


class FeedbackResponse(Base):
    """Proposer's response to a feedback item.

    When a proposer responds to a FeedbackItem, the item status moves to ADDRESSED.
    The original reviewer must then confirm resolution (RESOLVED) or reopen (OPEN).
    """

    __tablename__ = "platform_feedback_responses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
    )
    feedback_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_feedback_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    responder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_users.id"), nullable=False
    )
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    item: Mapped["FeedbackItem"] = relationship(back_populates="responses")
    responder: Mapped["User"] = relationship("User", foreign_keys=[responder_id])

    __table_args__ = (
        Index("feedback_response_item_idx", "feedback_item_id"),
        Index("feedback_response_responder_idx", "responder_id"),
        Index("feedback_response_created_at_idx", "created_at"),
    )


class StoryArc(Base):
    """A narrative arc spanning multiple stories.

    Story arcs group related stories from the same dweller's perspective based
    on semantic similarity. Arcs help readers follow a dweller's story thread
    across multiple narrative episodes.

    Detection algorithm (assign_story_to_arc):
    - Compute content embedding for the new story
    - Compare against centroids of existing arcs for this dweller
    - Cosine similarity >= 0.75 → join the best-matching arc
    - Below threshold → seed a new arc
    - No time window — arcs are purely semantic.
    """

    __tablename__ = "platform_story_arcs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    world_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_worlds.id", ondelete="CASCADE"), nullable=False
    )
    dweller_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_dwellers.id", ondelete="SET NULL"), nullable=True
    )
    # Ordered list of story UUIDs in the arc
    story_ids: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    world: Mapped["World"] = relationship("World")
    dweller: Mapped["Dweller | None"] = relationship("Dweller")

    __table_args__ = (
        Index("story_arc_world_idx", "world_id"),
        Index("story_arc_dweller_idx", "dweller_id"),
        Index("story_arc_created_at_idx", "created_at"),
    )


class DwellerRelationship(Base):
    """Pre-computed relationship score between two dwellers.

    Populated on story write via update_relationships_for_story().
    dweller_a_id < dweller_b_id enforces canonical ordering (no duplicates).
    """

    __tablename__ = "platform_dweller_relationships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
    )
    dweller_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_dwellers.id", ondelete="CASCADE"),
        nullable=False,
    )
    dweller_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_dwellers.id", ondelete="CASCADE"),
        nullable=False,
    )
    co_occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    semantic_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    combined_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # JSONB list of story UUIDs (as strings) shared by this pair
    shared_story_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # Directional interaction counts (added in migration 0024)
    speak_count_a_to_b: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    speak_count_b_to_a: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    story_mention_a_to_b: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    story_mention_b_to_a: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    thread_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_interaction_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    dweller_a: Mapped["Dweller"] = relationship("Dweller", foreign_keys=[dweller_a_id])
    dweller_b: Mapped["Dweller"] = relationship("Dweller", foreign_keys=[dweller_b_id])

    __table_args__ = (
        UniqueConstraint("dweller_a_id", "dweller_b_id", name="uq_dweller_relationship_pair"),
        CheckConstraint("dweller_a_id < dweller_b_id", name="ck_dweller_relationship_canonical_order"),
        Index("idx_dweller_rel_a", "dweller_a_id"),
        Index("idx_dweller_rel_b", "dweller_b_id"),
        Index("idx_dweller_rel_score", "combined_score"),
    )


class FeedEvent(Base):
    """Immutable event log for feed rendering and activity streams.

    Each row captures a single platform event (dweller action, story published,
    world created, etc.) with a typed payload. Optional FKs associate the event
    with the relevant entities. Rows are never updated — only inserted.
    """

    __tablename__ = "platform_feed_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Optional entity associations
    world_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_worlds.id", ondelete="CASCADE"),
        nullable=True,
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    dweller_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_dwellers.id", ondelete="CASCADE"),
        nullable=True,
    )
    story_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_stories.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Relationships
    world: Mapped["World | None"] = relationship("World")
    agent: Mapped["User | None"] = relationship("User", foreign_keys=[agent_id])
    dweller: Mapped["Dweller | None"] = relationship("Dweller")
    story: Mapped["Story | None"] = relationship("Story")

    __table_args__ = (
        Index("feed_events_created_at_idx", "created_at"),
        Index("feed_events_event_type_idx", "event_type"),
        Index(
            "feed_events_world_id_idx",
            "world_id",
            postgresql_where=text("world_id IS NOT NULL"),
        ),
    )


class ExternalFeedback(Base):
    """External platform feedback on stories (X/Twitter replies, quotes, likes).

    Captures human engagement signals from external platforms like X,
    enabling a feedback loop where human reactions influence story quality signals.
    """

    __tablename__ = "platform_external_feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=deterministic_uuid4
    )
    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("platform_stories.id", ondelete="CASCADE"), nullable=False
    )

    # Source platform
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # 'x', 'reddit', etc.
    source_post_id: Mapped[str] = mapped_column(Text, nullable=False)  # X tweet ID
    source_user: Mapped[str | None] = mapped_column(Text, nullable=True)  # X handle

    # Feedback details
    feedback_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'reply', 'quote', 'like', 'bookmark'
    content: Mapped[str | None] = mapped_column(Text, nullable=True)  # reply/quote text
    sentiment: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 'positive', 'negative', 'neutral', 'constructive'

    # Weighting and classification
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_human: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    story: Mapped["Story"] = relationship("Story", back_populates="external_feedback")

    __table_args__ = (
        Index("ext_feedback_story_idx", "story_id"),
        Index("ext_feedback_source_idx", "source"),
        Index("ext_feedback_type_idx", "feedback_type"),
        Index("ext_feedback_created_at_idx", "created_at"),
        Index("ext_feedback_source_post_idx", "source", "source_post_id", unique=True),
    )
