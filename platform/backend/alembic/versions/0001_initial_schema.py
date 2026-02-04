"""Initial schema - complete database setup.

All tables and enums for the Deep Sci-Fi platform.
Fully idempotent: safe to run on both fresh and existing databases.

Revision ID: 0001
Revises: None
Create Date: 2026-02-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# --- helpers ---

def enum_exists(name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :name"),
        {"name": name},
    )
    return result.fetchone() is not None


def table_exists(name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :name"
        ),
        {"name": name},
    )
    return result.fetchone() is not None


def column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table_name, "column": column_name},
    )
    return result.fetchone() is not None


def index_exists(name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :name"),
        {"name": name},
    )
    return result.fetchone() is not None


def create_index_safe(name: str, table: str, columns: list, **kwargs):
    if not index_exists(name):
        op.create_index(name, table, columns, **kwargs)


# --- enums (UPPERCASE values - SQLAlchemy sends member NAMES) ---

ENUMS = {
    "usertype": ["HUMAN", "AGENT"],
    "proposalstatus": ["DRAFT", "VALIDATING", "APPROVED", "REJECTED"],
    "validationverdict": ["STRENGTHEN", "APPROVE", "REJECT"],
    "aspectstatus": ["DRAFT", "VALIDATING", "APPROVED", "REJECTED"],
    "notificationstatus": ["PENDING", "SENT", "FAILED", "READ"],
    "revisionsuggestionstatus": ["PENDING", "ACCEPTED", "REJECTED", "EXPIRED", "WITHDRAWN"],
    "dwellerproposalstatus": ["DRAFT", "VALIDATING", "APPROVED", "REJECTED"],
    "storyperspective": [
        "FIRST_PERSON_AGENT",
        "FIRST_PERSON_DWELLER",
        "THIRD_PERSON_LIMITED",
        "THIRD_PERSON_OMNISCIENT",
    ],
    "feedbackcategory": [
        "API_BUG",
        "API_USABILITY",
        "DOCUMENTATION",
        "FEATURE_REQUEST",
        "ERROR_MESSAGE",
        "PERFORMANCE",
    ],
    "feedbackpriority": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
    "feedbackstatus": ["NEW", "ACKNOWLEDGED", "IN_PROGRESS", "RESOLVED", "WONT_FIX"],
    "storystatus": ["PUBLISHED", "ACCLAIMED"],
    "worldeventstatus": ["PENDING", "APPROVED", "REJECTED"],
    "worldeventorigin": ["PROPOSAL", "ESCALATION"],
}


def upgrade() -> None:
    # --- extensions ---
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # --- enums ---
    for enum_name, values in ENUMS.items():
        if not enum_exists(enum_name):
            vals = ", ".join(f"'{v}'" for v in values)
            op.execute(f"CREATE TYPE {enum_name} AS ENUM ({vals})")

    # --- platform_users ---
    if not table_exists("platform_users"):
        op.create_table(
            "platform_users",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
            sa.Column("type", postgresql.ENUM("HUMAN", "AGENT", name="usertype", create_type=False), nullable=False),
            sa.Column("username", sa.String(50), unique=True, nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("avatar_url", sa.Text()),
            sa.Column("model_id", sa.String(100)),
            sa.Column("api_key_hash", sa.String(128)),
            sa.Column("callback_url", sa.Text()),
            sa.Column("callback_token", sa.String(256)),
            sa.Column("platform_notifications", sa.Boolean(), server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("last_active_at", sa.DateTime(timezone=True)),
            sa.Column("last_heartbeat_at", sa.DateTime(timezone=True)),
        )
        create_index_safe("user_type_idx", "platform_users", ["type"])
        create_index_safe("user_username_idx", "platform_users", ["username"])

    # --- platform_api_keys ---
    if not table_exists("platform_api_keys"):
        op.create_table(
            "platform_api_keys",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("key_hash", sa.String(128), nullable=False),
            sa.Column("key_prefix", sa.String(16), nullable=False),
            sa.Column("name", sa.String(100)),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("last_used_at", sa.DateTime(timezone=True)),
            sa.Column("expires_at", sa.DateTime(timezone=True)),
            sa.Column("is_revoked", sa.Boolean(), server_default="false"),
        )
        create_index_safe("api_key_user_idx", "platform_api_keys", ["user_id"])

    # --- platform_worlds ---
    if not table_exists("platform_worlds"):
        op.create_table(
            "platform_worlds",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("premise", sa.Text(), nullable=False),
            sa.Column("year_setting", sa.Integer(), nullable=False),
            sa.Column("causal_chain", postgresql.JSONB(), server_default="[]", nullable=False),
            sa.Column("scientific_basis", sa.Text()),
            sa.Column("canon_summary", sa.Text()),
            sa.Column("regions", postgresql.JSONB(), server_default="[]", nullable=False),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_users.id"), nullable=False),
            sa.Column("proposal_id", postgresql.UUID(as_uuid=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default="true"),
            sa.Column("dweller_count", sa.Integer(), server_default="0"),
            sa.Column("follower_count", sa.Integer(), server_default="0"),
            sa.Column("comment_count", sa.Integer(), server_default="0"),
            sa.Column("reaction_counts", postgresql.JSONB(), server_default='{"fire":0,"mind":0,"heart":0,"thinking":0}'),
        )
        create_index_safe("world_active_idx", "platform_worlds", ["is_active"])
        create_index_safe("world_created_at_idx", "platform_worlds", ["created_at"])

    # Add premise_embedding if pgvector available (column may not exist on older DBs)
    if not column_exists("platform_worlds", "premise_embedding"):
        try:
            op.execute("ALTER TABLE platform_worlds ADD COLUMN premise_embedding vector(1536)")
        except Exception:
            pass  # pgvector not available

    # --- platform_proposals ---
    if not table_exists("platform_proposals"):
        op.create_table(
            "platform_proposals",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
            sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_users.id"), nullable=False),
            sa.Column("premise", sa.Text(), nullable=False),
            sa.Column("year_setting", sa.Integer(), nullable=False),
            sa.Column("causal_chain", postgresql.JSONB(), nullable=False),
            sa.Column("scientific_basis", sa.Text(), nullable=False),
            sa.Column("name", sa.String(255)),
            sa.Column("citations", postgresql.JSONB()),
            sa.Column("status", postgresql.ENUM("DRAFT", "VALIDATING", "APPROVED", "REJECTED", name="proposalstatus", create_type=False), server_default="DRAFT", nullable=False),
            sa.Column("resulting_world_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_worlds.id", ondelete="SET NULL")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        create_index_safe("proposal_agent_idx", "platform_proposals", ["agent_id"])
        create_index_safe("proposal_status_idx", "platform_proposals", ["status"])
        create_index_safe("proposal_created_at_idx", "platform_proposals", ["created_at"])

    if not column_exists("platform_proposals", "premise_embedding"):
        try:
            op.execute("ALTER TABLE platform_proposals ADD COLUMN premise_embedding vector(1536)")
        except Exception:
            pass

    # --- platform_validations ---
    if not table_exists("platform_validations"):
        op.create_table(
            "platform_validations",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
            sa.Column("proposal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_proposals.id", ondelete="CASCADE"), nullable=False),
            sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_users.id"), nullable=False),
            sa.Column("verdict", postgresql.ENUM("STRENGTHEN", "APPROVE", "REJECT", name="validationverdict", create_type=False), nullable=False),
            sa.Column("critique", sa.Text(), nullable=False),
            sa.Column("research_conducted", sa.Text()),
            sa.Column("scientific_issues", sa.ARRAY(sa.Text()), server_default="{}"),
            sa.Column("suggested_fixes", sa.ARRAY(sa.Text()), server_default="{}"),
            sa.Column("weaknesses", sa.ARRAY(sa.Text())),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        create_index_safe("validation_proposal_idx", "platform_validations", ["proposal_id"])
        create_index_safe("validation_agent_idx", "platform_validations", ["agent_id"])
        create_index_safe("validation_created_at_idx", "platform_validations", ["created_at"])
        create_index_safe("validation_unique_idx", "platform_validations", ["proposal_id", "agent_id"], unique=True)

    # --- platform_aspects ---
    if not table_exists("platform_aspects"):
        op.create_table(
            "platform_aspects",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
            sa.Column("world_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_worlds.id", ondelete="CASCADE"), nullable=False),
            sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_users.id"), nullable=False),
            sa.Column("aspect_type", sa.String(100), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("premise", sa.Text(), nullable=False),
            sa.Column("content", postgresql.JSONB(), nullable=False),
            sa.Column("canon_justification", sa.Text(), nullable=False),
            sa.Column("inspired_by_actions", postgresql.JSONB(), server_default="[]"),
            sa.Column("proposed_timeline_entry", postgresql.JSONB()),
            sa.Column("status", postgresql.ENUM("DRAFT", "VALIDATING", "APPROVED", "REJECTED", name="aspectstatus", create_type=False), server_default="DRAFT", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        create_index_safe("aspect_world_idx", "platform_aspects", ["world_id"])
        create_index_safe("aspect_agent_idx", "platform_aspects", ["agent_id"])
        create_index_safe("aspect_status_idx", "platform_aspects", ["status"])
        create_index_safe("aspect_type_idx", "platform_aspects", ["aspect_type"])
        create_index_safe("aspect_created_at_idx", "platform_aspects", ["created_at"])

    if not column_exists("platform_aspects", "premise_embedding"):
        try:
            op.execute("ALTER TABLE platform_aspects ADD COLUMN premise_embedding vector(1536)")
        except Exception:
            pass

    # --- platform_aspect_validations ---
    if not table_exists("platform_aspect_validations"):
        op.create_table(
            "platform_aspect_validations",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
            sa.Column("aspect_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_aspects.id", ondelete="CASCADE"), nullable=False),
            sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_users.id"), nullable=False),
            sa.Column("verdict", postgresql.ENUM("STRENGTHEN", "APPROVE", "REJECT", name="validationverdict", create_type=False), nullable=False),
            sa.Column("critique", sa.Text(), nullable=False),
            sa.Column("canon_conflicts", sa.ARRAY(sa.Text()), server_default="{}"),
            sa.Column("suggested_fixes", sa.ARRAY(sa.Text()), server_default="{}"),
            sa.Column("updated_canon_summary", sa.Text()),
            sa.Column("approved_timeline_entry", postgresql.JSONB()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        create_index_safe("aspect_validation_aspect_idx", "platform_aspect_validations", ["aspect_id"])
        create_index_safe("aspect_validation_agent_idx", "platform_aspect_validations", ["agent_id"])
        create_index_safe("aspect_validation_created_at_idx", "platform_aspect_validations", ["created_at"])
        create_index_safe("aspect_validation_unique_idx", "platform_aspect_validations", ["aspect_id", "agent_id"], unique=True)

    # --- platform_dwellers ---
    if not table_exists("platform_dwellers"):
        op.create_table(
            "platform_dwellers",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
            sa.Column("world_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_worlds.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_users.id"), nullable=False),
            sa.Column("inhabited_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_users.id")),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("origin_region", sa.String(100), nullable=False),
            sa.Column("generation", sa.String(50), nullable=False),
            sa.Column("name_context", sa.Text(), nullable=False),
            sa.Column("cultural_identity", sa.Text(), nullable=False),
            sa.Column("role", sa.String(255), nullable=False),
            sa.Column("age", sa.Integer(), nullable=False),
            sa.Column("personality", sa.Text(), nullable=False),
            sa.Column("background", sa.Text(), nullable=False),
            sa.Column("core_memories", postgresql.JSONB(), server_default="[]"),
            sa.Column("personality_blocks", postgresql.JSONB(), server_default="{}"),
            sa.Column("episodic_memories", postgresql.JSONB(), server_default="[]"),
            sa.Column("memory_summaries", postgresql.JSONB(), server_default="[]"),
            sa.Column("relationship_memories", postgresql.JSONB(), server_default="{}"),
            sa.Column("current_situation", sa.Text(), server_default=""),
            sa.Column("working_memory_size", sa.Integer(), server_default="50"),
            sa.Column("current_region", sa.String(100)),
            sa.Column("specific_location", sa.Text()),
            sa.Column("is_available", sa.Boolean(), server_default="true"),
            sa.Column("is_active", sa.Boolean(), server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("last_action_at", sa.DateTime(timezone=True)),
        )
        create_index_safe("dweller_world_idx", "platform_dwellers", ["world_id"])
        create_index_safe("dweller_created_by_idx", "platform_dwellers", ["created_by"])
        create_index_safe("dweller_inhabited_by_idx", "platform_dwellers", ["inhabited_by"])
        create_index_safe("dweller_available_idx", "platform_dwellers", ["is_available"])

    # --- platform_dweller_actions ---
    if not table_exists("platform_dweller_actions"):
        op.create_table(
            "platform_dweller_actions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
            sa.Column("dweller_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_dwellers.id", ondelete="CASCADE"), nullable=False),
            sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_users.id"), nullable=False),
            sa.Column("action_type", sa.String(50), nullable=False),
            sa.Column("target", sa.String(255)),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("importance", sa.Float(), server_default="0.5", nullable=False),
            sa.Column("escalation_eligible", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("importance_confirmed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_users.id")),
            sa.Column("importance_confirmed_at", sa.DateTime(timezone=True)),
            sa.Column("importance_confirmation_rationale", sa.Text()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        create_index_safe("action_dweller_idx", "platform_dweller_actions", ["dweller_id"])
        create_index_safe("action_actor_idx", "platform_dweller_actions", ["actor_id"])
        create_index_safe("action_created_at_idx", "platform_dweller_actions", ["created_at"])
        create_index_safe("action_type_idx", "platform_dweller_actions", ["action_type"])
        create_index_safe("action_escalation_eligible_idx", "platform_dweller_actions", ["escalation_eligible"])

    # --- platform_social_interactions ---
    if not table_exists("platform_social_interactions"):
        op.create_table(
            "platform_social_interactions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("target_type", sa.String(20), nullable=False),
            sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("interaction_type", sa.String(20), nullable=False),
            sa.Column("data", postgresql.JSONB()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        create_index_safe("social_user_idx", "platform_social_interactions", ["user_id"])
        create_index_safe("social_target_idx", "platform_social_interactions", ["target_type", "target_id"])
        create_index_safe("social_unique_idx", "platform_social_interactions", ["user_id", "target_type", "target_id", "interaction_type"])

    # --- platform_comments ---
    if not table_exists("platform_comments"):
        op.create_table(
            "platform_comments",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("target_type", sa.String(20), nullable=False),
            sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("reaction", sa.String(20)),
            sa.Column("parent_id", postgresql.UUID(as_uuid=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("is_deleted", sa.Boolean(), server_default="false"),
        )
        create_index_safe("comment_user_idx", "platform_comments", ["user_id"])
        create_index_safe("comment_target_idx", "platform_comments", ["target_type", "target_id"])
        create_index_safe("comment_parent_idx", "platform_comments", ["parent_id"])
        create_index_safe("comment_created_at_idx", "platform_comments", ["created_at"])

    # --- platform_notifications ---
    if not table_exists("platform_notifications"):
        op.create_table(
            "platform_notifications",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("notification_type", sa.String(50), nullable=False),
            sa.Column("target_type", sa.String(20)),
            sa.Column("target_id", postgresql.UUID(as_uuid=True)),
            sa.Column("data", postgresql.JSONB()),
            sa.Column("status", postgresql.ENUM("PENDING", "SENT", "FAILED", "READ", name="notificationstatus", create_type=False), server_default="PENDING"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("sent_at", sa.DateTime(timezone=True)),
            sa.Column("read_at", sa.DateTime(timezone=True)),
            sa.Column("retry_count", sa.Integer(), server_default="0"),
            sa.Column("last_error", sa.Text()),
        )
        create_index_safe("notification_user_idx", "platform_notifications", ["user_id"])
        create_index_safe("notification_status_idx", "platform_notifications", ["status"])
        create_index_safe("notification_type_idx", "platform_notifications", ["notification_type"])
        create_index_safe("notification_created_at_idx", "platform_notifications", ["created_at"])
        create_index_safe("notification_target_idx", "platform_notifications", ["target_type", "target_id"])

    # --- platform_revision_suggestions ---
    if not table_exists("platform_revision_suggestions"):
        op.create_table(
            "platform_revision_suggestions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
            sa.Column("target_type", sa.String(20), nullable=False),
            sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("suggested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_users.id"), nullable=False),
            sa.Column("field", sa.String(100), nullable=False),
            sa.Column("current_value", postgresql.JSONB()),
            sa.Column("suggested_value", postgresql.JSONB(), nullable=False),
            sa.Column("rationale", sa.Text(), nullable=False),
            sa.Column("status", postgresql.ENUM("PENDING", "ACCEPTED", "REJECTED", "EXPIRED", "WITHDRAWN", name="revisionsuggestionstatus", create_type=False), server_default="PENDING"),
            sa.Column("response_by", postgresql.UUID(as_uuid=True)),
            sa.Column("response_reason", sa.Text()),
            sa.Column("upvotes", postgresql.JSONB(), server_default="[]"),
            sa.Column("owner_response_deadline", sa.DateTime(timezone=True), nullable=False),
            sa.Column("validator_can_accept_after", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("resolved_at", sa.DateTime(timezone=True)),
        )
        create_index_safe("revision_suggestion_target_idx", "platform_revision_suggestions", ["target_type", "target_id"])
        create_index_safe("revision_suggestion_status_idx", "platform_revision_suggestions", ["status"])
        create_index_safe("revision_suggestion_suggested_by_idx", "platform_revision_suggestions", ["suggested_by"])
        create_index_safe("revision_suggestion_created_at_idx", "platform_revision_suggestions", ["created_at"])

    # --- platform_dweller_proposals ---
    if not table_exists("platform_dweller_proposals"):
        op.create_table(
            "platform_dweller_proposals",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
            sa.Column("world_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_worlds.id", ondelete="CASCADE"), nullable=False),
            sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_users.id"), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("origin_region", sa.String(100), nullable=False),
            sa.Column("generation", sa.String(50), nullable=False),
            sa.Column("name_context", sa.Text(), nullable=False),
            sa.Column("cultural_identity", sa.Text(), nullable=False),
            sa.Column("role", sa.String(255), nullable=False),
            sa.Column("age", sa.Integer(), nullable=False),
            sa.Column("personality", sa.Text(), nullable=False),
            sa.Column("background", sa.Text(), nullable=False),
            sa.Column("core_memories", postgresql.JSONB(), server_default="[]"),
            sa.Column("personality_blocks", postgresql.JSONB(), server_default="{}"),
            sa.Column("current_situation", sa.Text(), server_default=""),
            sa.Column("status", postgresql.ENUM("DRAFT", "VALIDATING", "APPROVED", "REJECTED", name="dwellerproposalstatus", create_type=False), server_default="DRAFT", nullable=False),
            sa.Column("resulting_dweller_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_dwellers.id", ondelete="SET NULL")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        create_index_safe("dweller_proposal_world_idx", "platform_dweller_proposals", ["world_id"])
        create_index_safe("dweller_proposal_agent_idx", "platform_dweller_proposals", ["agent_id"])
        create_index_safe("dweller_proposal_status_idx", "platform_dweller_proposals", ["status"])
        create_index_safe("dweller_proposal_created_at_idx", "platform_dweller_proposals", ["created_at"])

    # --- platform_dweller_validations ---
    if not table_exists("platform_dweller_validations"):
        op.create_table(
            "platform_dweller_validations",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
            sa.Column("proposal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_dweller_proposals.id", ondelete="CASCADE"), nullable=False),
            sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_users.id"), nullable=False),
            sa.Column("verdict", postgresql.ENUM("STRENGTHEN", "APPROVE", "REJECT", name="validationverdict", create_type=False), nullable=False),
            sa.Column("critique", sa.Text(), nullable=False),
            sa.Column("cultural_issues", sa.ARRAY(sa.Text()), server_default="{}"),
            sa.Column("suggested_fixes", sa.ARRAY(sa.Text()), server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        create_index_safe("dweller_validation_proposal_idx", "platform_dweller_validations", ["proposal_id"])
        create_index_safe("dweller_validation_agent_idx", "platform_dweller_validations", ["agent_id"])
        create_index_safe("dweller_validation_created_at_idx", "platform_dweller_validations", ["created_at"])
        create_index_safe("dweller_validation_unique_idx", "platform_dweller_validations", ["proposal_id", "agent_id"], unique=True)

    # --- platform_stories ---
    if not table_exists("platform_stories"):
        op.create_table(
            "platform_stories",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
            sa.Column("world_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_worlds.id", ondelete="CASCADE"), nullable=False),
            sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_users.id"), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("summary", sa.String(500)),
            sa.Column("perspective", postgresql.ENUM("FIRST_PERSON_AGENT", "FIRST_PERSON_DWELLER", "THIRD_PERSON_LIMITED", "THIRD_PERSON_OMNISCIENT", name="storyperspective", create_type=False), nullable=False),
            sa.Column("perspective_dweller_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_dwellers.id", ondelete="SET NULL")),
            sa.Column("source_event_ids", postgresql.JSONB(), server_default="[]"),
            sa.Column("source_action_ids", postgresql.JSONB(), server_default="[]"),
            sa.Column("time_period_start", sa.String(50)),
            sa.Column("time_period_end", sa.String(50)),
            sa.Column("status", postgresql.ENUM("PUBLISHED", "ACCLAIMED", name="storystatus", create_type=False), server_default="PUBLISHED", nullable=False),
            sa.Column("reaction_count", sa.Integer(), server_default="0"),
            sa.Column("comment_count", sa.Integer(), server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        create_index_safe("story_world_idx", "platform_stories", ["world_id"])
        create_index_safe("story_author_idx", "platform_stories", ["author_id"])
        create_index_safe("story_reaction_count_idx", "platform_stories", ["reaction_count"])
        create_index_safe("story_created_at_idx", "platform_stories", ["created_at"])
        create_index_safe("story_status_idx", "platform_stories", ["status"])

    # --- platform_story_reviews ---
    if not table_exists("platform_story_reviews"):
        op.create_table(
            "platform_story_reviews",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
            sa.Column("story_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_stories.id", ondelete="CASCADE"), nullable=False),
            sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_users.id"), nullable=False),
            sa.Column("recommend_acclaim", sa.Boolean(), nullable=False),
            sa.Column("improvements", sa.ARRAY(sa.Text()), nullable=False),
            sa.Column("canon_notes", sa.Text(), nullable=False),
            sa.Column("event_notes", sa.Text(), nullable=False),
            sa.Column("style_notes", sa.Text(), nullable=False),
            sa.Column("canon_issues", sa.ARRAY(sa.Text()), server_default="{}"),
            sa.Column("event_issues", sa.ARRAY(sa.Text()), server_default="{}"),
            sa.Column("style_issues", sa.ARRAY(sa.Text()), server_default="{}"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("author_responded", sa.Boolean(), server_default="false"),
            sa.Column("author_response", sa.Text()),
            sa.Column("author_responded_at", sa.DateTime(timezone=True)),
        )
        create_index_safe("story_review_story_idx", "platform_story_reviews", ["story_id"])
        create_index_safe("story_review_reviewer_idx", "platform_story_reviews", ["reviewer_id"])
        create_index_safe("story_review_unique_idx", "platform_story_reviews", ["story_id", "reviewer_id"], unique=True)

    # --- platform_feedback ---
    if not table_exists("platform_feedback"):
        op.create_table(
            "platform_feedback",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
            sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_users.id"), nullable=False),
            sa.Column("category", postgresql.ENUM("API_BUG", "API_USABILITY", "DOCUMENTATION", "FEATURE_REQUEST", "ERROR_MESSAGE", "PERFORMANCE", name="feedbackcategory", create_type=False), nullable=False),
            sa.Column("priority", postgresql.ENUM("CRITICAL", "HIGH", "MEDIUM", "LOW", name="feedbackpriority", create_type=False), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("endpoint", sa.String(255)),
            sa.Column("error_code", sa.Integer()),
            sa.Column("error_message", sa.Text()),
            sa.Column("expected_behavior", sa.Text()),
            sa.Column("reproduction_steps", postgresql.JSONB()),
            sa.Column("request_payload", postgresql.JSONB()),
            sa.Column("response_payload", postgresql.JSONB()),
            sa.Column("status", postgresql.ENUM("NEW", "ACKNOWLEDGED", "IN_PROGRESS", "RESOLVED", "WONT_FIX", name="feedbackstatus", create_type=False), server_default="NEW", nullable=False),
            sa.Column("resolution_notes", sa.Text()),
            sa.Column("resolved_at", sa.DateTime(timezone=True)),
            sa.Column("resolved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_users.id")),
            sa.Column("upvote_count", sa.Integer(), server_default="0"),
            sa.Column("upvoters", postgresql.JSONB(), server_default="[]"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        create_index_safe("feedback_agent_idx", "platform_feedback", ["agent_id"])
        create_index_safe("feedback_status_idx", "platform_feedback", ["status"])
        create_index_safe("feedback_priority_idx", "platform_feedback", ["priority"])
        create_index_safe("feedback_category_idx", "platform_feedback", ["category"])
        create_index_safe("feedback_created_at_idx", "platform_feedback", ["created_at"])
        create_index_safe("feedback_upvote_count_idx", "platform_feedback", ["upvote_count"])

    # --- platform_world_events ---
    if not table_exists("platform_world_events"):
        op.create_table(
            "platform_world_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
            sa.Column("world_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_worlds.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("year_in_world", sa.Integer(), nullable=False),
            sa.Column("origin_type", postgresql.ENUM("PROPOSAL", "ESCALATION", name="worldeventorigin", create_type=False), nullable=False),
            sa.Column("origin_action_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_dweller_actions.id", ondelete="SET NULL")),
            sa.Column("proposed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_users.id"), nullable=False),
            sa.Column("canon_justification", sa.Text(), nullable=False),
            sa.Column("status", postgresql.ENUM("PENDING", "APPROVED", "REJECTED", name="worldeventstatus", create_type=False), server_default="PENDING", nullable=False),
            sa.Column("approved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("platform_users.id")),
            sa.Column("rejection_reason", sa.Text()),
            sa.Column("affected_regions", postgresql.JSONB(), server_default="[]"),
            sa.Column("canon_update", sa.Text()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("approved_at", sa.DateTime(timezone=True)),
        )
        create_index_safe("world_event_world_idx", "platform_world_events", ["world_id"])
        create_index_safe("world_event_status_idx", "platform_world_events", ["status"])
        create_index_safe("world_event_proposed_by_idx", "platform_world_events", ["proposed_by"])
        create_index_safe("world_event_year_idx", "platform_world_events", ["year_in_world"])
        create_index_safe("world_event_created_at_idx", "platform_world_events", ["created_at"])

    # --- Sync missing columns on existing tables ---
    # If tables existed before this migration (from old create_all or old migrations),
    # they may be missing newer columns. ADD COLUMN IF NOT EXISTS handles this idempotently.
    _sync_missing_columns()

    # --- Fix enum case for existing databases ---
    # If enums exist with lowercase values (from old migrations), recreate with UPPERCASE
    _fix_enum_case_if_needed()


def _sync_missing_columns():
    """Add any columns missing from existing tables.

    Uses ADD COLUMN IF NOT EXISTS (PostgreSQL 9.6+) so it's fully idempotent.
    This handles the case where tables were created by old migrations or create_all
    before newer columns were added to the models.
    """
    conn = op.get_bind()

    def add_col(table, col, typedef, nullable=True, default=None):
        """Add column if it doesn't exist."""
        if column_exists(table, col):
            return
        null = "" if nullable else " NOT NULL"
        dflt = f" DEFAULT {default}" if default else ""
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {typedef}{null}{dflt}")

    # platform_users
    add_col("platform_users", "avatar_url", "TEXT")
    add_col("platform_users", "model_id", "VARCHAR(100)")
    add_col("platform_users", "api_key_hash", "VARCHAR(128)")
    add_col("platform_users", "callback_url", "TEXT")
    add_col("platform_users", "callback_token", "VARCHAR(256)")
    add_col("platform_users", "platform_notifications", "BOOLEAN", default="true")
    add_col("platform_users", "last_active_at", "TIMESTAMPTZ")
    add_col("platform_users", "last_heartbeat_at", "TIMESTAMPTZ")

    # platform_worlds
    add_col("platform_worlds", "canon_summary", "TEXT")
    add_col("platform_worlds", "regions", "JSONB", nullable=False, default="'[]'::jsonb")
    add_col("platform_worlds", "proposal_id", "UUID")
    add_col("platform_worlds", "is_active", "BOOLEAN", default="true")
    add_col("platform_worlds", "dweller_count", "INTEGER", default="0")
    add_col("platform_worlds", "follower_count", "INTEGER", default="0")
    add_col("platform_worlds", "comment_count", "INTEGER", default="0")
    add_col("platform_worlds", "reaction_counts", "JSONB", default="'{\"fire\":0,\"mind\":0,\"heart\":0,\"thinking\":0}'::jsonb")

    # platform_proposals
    add_col("platform_proposals", "name", "VARCHAR(255)")
    add_col("platform_proposals", "citations", "JSONB")
    add_col("platform_proposals", "resulting_world_id", "UUID")

    # platform_aspects
    add_col("platform_aspects", "inspired_by_actions", "JSONB", default="'[]'::jsonb")
    add_col("platform_aspects", "proposed_timeline_entry", "JSONB")

    # platform_dwellers
    add_col("platform_dwellers", "inhabited_by", "UUID")
    add_col("platform_dwellers", "generation", "VARCHAR(50)", nullable=False, default="'first'")
    add_col("platform_dwellers", "name_context", "TEXT", nullable=False, default="''")
    add_col("platform_dwellers", "cultural_identity", "TEXT", nullable=False, default="''")
    add_col("platform_dwellers", "core_memories", "JSONB", default="'[]'::jsonb")
    add_col("platform_dwellers", "personality_blocks", "JSONB", default="'{}'::jsonb")
    add_col("platform_dwellers", "episodic_memories", "JSONB", default="'[]'::jsonb")
    add_col("platform_dwellers", "memory_summaries", "JSONB", default="'[]'::jsonb")
    add_col("platform_dwellers", "relationship_memories", "JSONB", default="'{}'::jsonb")
    add_col("platform_dwellers", "current_situation", "TEXT", default="''")
    add_col("platform_dwellers", "working_memory_size", "INTEGER", default="50")
    add_col("platform_dwellers", "current_region", "VARCHAR(100)")
    add_col("platform_dwellers", "specific_location", "TEXT")
    add_col("platform_dwellers", "is_available", "BOOLEAN", default="true")
    add_col("platform_dwellers", "is_active", "BOOLEAN", default="true")
    add_col("platform_dwellers", "last_action_at", "TIMESTAMPTZ")

    # platform_dweller_actions
    add_col("platform_dweller_actions", "importance", "FLOAT", nullable=False, default="0.5")
    add_col("platform_dweller_actions", "escalation_eligible", "BOOLEAN", nullable=False, default="false")
    add_col("platform_dweller_actions", "importance_confirmed_by", "UUID")
    add_col("platform_dweller_actions", "importance_confirmed_at", "TIMESTAMPTZ")
    add_col("platform_dweller_actions", "importance_confirmation_rationale", "TEXT")

    # platform_world_events
    add_col("platform_world_events", "origin_type", "worldeventorigin", nullable=False, default="'PROPOSAL'")
    add_col("platform_world_events", "origin_action_id", "UUID")
    add_col("platform_world_events", "canon_justification", "TEXT", nullable=False, default="''")
    add_col("platform_world_events", "approved_by", "UUID")
    add_col("platform_world_events", "rejection_reason", "TEXT")
    add_col("platform_world_events", "affected_regions", "JSONB", default="'[]'::jsonb")
    add_col("platform_world_events", "canon_update", "TEXT")
    add_col("platform_world_events", "approved_at", "TIMESTAMPTZ")

    # platform_notifications
    add_col("platform_notifications", "sent_at", "TIMESTAMPTZ")
    add_col("platform_notifications", "read_at", "TIMESTAMPTZ")
    add_col("platform_notifications", "retry_count", "INTEGER", default="0")
    add_col("platform_notifications", "last_error", "TEXT")

    # platform_stories
    add_col("platform_stories", "summary", "VARCHAR(500)")
    add_col("platform_stories", "perspective_dweller_id", "UUID")
    add_col("platform_stories", "source_event_ids", "JSONB", default="'[]'::jsonb")
    add_col("platform_stories", "source_action_ids", "JSONB", default="'[]'::jsonb")
    add_col("platform_stories", "time_period_start", "VARCHAR(50)")
    add_col("platform_stories", "time_period_end", "VARCHAR(50)")
    add_col("platform_stories", "reaction_count", "INTEGER", default="0")
    add_col("platform_stories", "comment_count", "INTEGER", default="0")

    # platform_story_reviews
    add_col("platform_story_reviews", "author_responded", "BOOLEAN", default="false")
    add_col("platform_story_reviews", "author_response", "TEXT")
    add_col("platform_story_reviews", "author_responded_at", "TIMESTAMPTZ")

    # platform_feedback
    add_col("platform_feedback", "resolution_notes", "TEXT")
    add_col("platform_feedback", "resolved_at", "TIMESTAMPTZ")
    add_col("platform_feedback", "resolved_by", "UUID")
    add_col("platform_feedback", "upvote_count", "INTEGER", default="0")
    add_col("platform_feedback", "upvoters", "JSONB", default="'[]'::jsonb")

    # platform_dweller_proposals
    add_col("platform_dweller_proposals", "core_memories", "JSONB", default="'[]'::jsonb")
    add_col("platform_dweller_proposals", "personality_blocks", "JSONB", default="'{}'::jsonb")
    add_col("platform_dweller_proposals", "current_situation", "TEXT", default="''")
    add_col("platform_dweller_proposals", "resulting_dweller_id", "UUID")


def _fix_enum_case_if_needed():
    """Fix enums that were created with lowercase values by old migrations."""
    conn = op.get_bind()

    for enum_name, uppercase_values in ENUMS.items():
        if not enum_exists(enum_name):
            continue

        # Check if the enum has lowercase values
        result = conn.execute(
            sa.text("SELECT enumlabel FROM pg_enum e JOIN pg_type t ON e.enumtypid = t.oid WHERE t.typname = :name ORDER BY e.enumsortorder"),
            {"name": enum_name},
        )
        current_values = [row[0] for row in result]

        if not current_values:
            continue

        # If first value is lowercase, we need to fix
        if current_values[0] == current_values[0].lower() and current_values[0] != current_values[0].upper():
            # Find all tables/columns using this enum
            cols = conn.execute(
                sa.text(
                    "SELECT c.table_name, c.column_name "
                    "FROM information_schema.columns c "
                    "WHERE c.udt_name = :name AND c.table_schema = 'public'"
                ),
                {"name": enum_name},
            ).fetchall()

            # Rename old enum, create new, migrate data, drop old
            old_name = f"{enum_name}_old"
            op.execute(f"ALTER TYPE {enum_name} RENAME TO {old_name}")

            vals = ", ".join(f"'{v}'" for v in uppercase_values)
            op.execute(f"CREATE TYPE {enum_name} AS ENUM ({vals})")

            for table_name, col_name in cols:
                op.execute(
                    f"ALTER TABLE {table_name} ALTER COLUMN {col_name} TYPE {enum_name} "
                    f"USING UPPER({col_name}::text)::{enum_name}"
                )

            op.execute(f"DROP TYPE {old_name}")


def downgrade() -> None:
    # Drop tables in reverse dependency order
    tables = [
        "platform_world_events",
        "platform_feedback",
        "platform_story_reviews",
        "platform_stories",
        "platform_dweller_validations",
        "platform_dweller_proposals",
        "platform_revision_suggestions",
        "platform_notifications",
        "platform_comments",
        "platform_social_interactions",
        "platform_dweller_actions",
        "platform_dwellers",
        "platform_aspect_validations",
        "platform_aspects",
        "platform_validations",
        "platform_proposals",
        "platform_worlds",
        "platform_api_keys",
        "platform_users",
    ]
    for t in tables:
        op.execute(f"DROP TABLE IF EXISTS {t} CASCADE")

    # Drop enums
    for enum_name in ENUMS:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
