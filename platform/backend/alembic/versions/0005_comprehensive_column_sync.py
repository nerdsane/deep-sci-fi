"""Comprehensive column sync - ALL columns on ALL tables.

Ensures every column from the current schema exists, including core columns
that the original table creation may have been missing.

Revision ID: 0005
Revises: 0004
Create Date: 2026-02-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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


def add_col(table, col, typedef, nullable=True, default=None):
    if not table_exists(table) or column_exists(table, col):
        return
    null = "" if nullable else " NOT NULL"
    dflt = f" DEFAULT {default}" if default else ""
    sql = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {typedef}{null}{dflt}"
    op.get_bind().exec_driver_sql(sql)


def upgrade() -> None:
    # ===== platform_users =====
    add_col("platform_users", "id", "UUID", nullable=False, default="uuid_generate_v4()")
    add_col("platform_users", "type", "usertype", nullable=False)
    add_col("platform_users", "username", "VARCHAR(50)", nullable=False)
    add_col("platform_users", "name", "VARCHAR(255)", nullable=False)
    add_col("platform_users", "avatar_url", "TEXT")
    add_col("platform_users", "model_id", "VARCHAR(100)")
    add_col("platform_users", "api_key_hash", "VARCHAR(128)")
    add_col("platform_users", "callback_url", "TEXT")
    add_col("platform_users", "callback_token", "VARCHAR(256)")
    add_col("platform_users", "platform_notifications", "BOOLEAN", default="true")
    add_col("platform_users", "created_at", "TIMESTAMPTZ", nullable=False, default="now()")
    add_col("platform_users", "last_active_at", "TIMESTAMPTZ")
    add_col("platform_users", "last_heartbeat_at", "TIMESTAMPTZ")

    # ===== platform_api_keys =====
    add_col("platform_api_keys", "user_id", "UUID", nullable=False)
    add_col("platform_api_keys", "key_hash", "VARCHAR(128)", nullable=False)
    add_col("platform_api_keys", "key_prefix", "VARCHAR(16)", nullable=False)
    add_col("platform_api_keys", "name", "VARCHAR(100)")
    add_col("platform_api_keys", "created_at", "TIMESTAMPTZ", nullable=False, default="now()")
    add_col("platform_api_keys", "last_used_at", "TIMESTAMPTZ")
    add_col("platform_api_keys", "expires_at", "TIMESTAMPTZ")
    add_col("platform_api_keys", "is_revoked", "BOOLEAN", default="false")

    # ===== platform_worlds =====
    add_col("platform_worlds", "name", "VARCHAR(255)", nullable=False)
    add_col("platform_worlds", "premise", "TEXT", nullable=False)
    add_col("platform_worlds", "year_setting", "INTEGER", nullable=False)
    add_col("platform_worlds", "causal_chain", "JSONB", nullable=False, default="'[]'::jsonb")
    add_col("platform_worlds", "scientific_basis", "TEXT")
    add_col("platform_worlds", "canon_summary", "TEXT")
    add_col("platform_worlds", "regions", "JSONB", nullable=False, default="'[]'::jsonb")
    add_col("platform_worlds", "created_by", "UUID", nullable=False)
    add_col("platform_worlds", "proposal_id", "UUID")
    add_col("platform_worlds", "created_at", "TIMESTAMPTZ", nullable=False, default="now()")
    add_col("platform_worlds", "updated_at", "TIMESTAMPTZ", nullable=False, default="now()")
    add_col("platform_worlds", "is_active", "BOOLEAN", default="true")
    add_col("platform_worlds", "dweller_count", "INTEGER", default="0")
    add_col("platform_worlds", "follower_count", "INTEGER", default="0")
    add_col("platform_worlds", "comment_count", "INTEGER", default="0")
    add_col("platform_worlds", "reaction_counts", "JSONB", default="'{}'::jsonb")

    # ===== platform_proposals =====
    add_col("platform_proposals", "agent_id", "UUID", nullable=False)
    add_col("platform_proposals", "premise", "TEXT", nullable=False)
    add_col("platform_proposals", "year_setting", "INTEGER", nullable=False)
    add_col("platform_proposals", "causal_chain", "JSONB", nullable=False)
    add_col("platform_proposals", "scientific_basis", "TEXT", nullable=False)
    add_col("platform_proposals", "name", "VARCHAR(255)")
    add_col("platform_proposals", "citations", "JSONB")
    add_col("platform_proposals", "status", "proposalstatus", nullable=False, default="'DRAFT'")
    add_col("platform_proposals", "resulting_world_id", "UUID")
    add_col("platform_proposals", "created_at", "TIMESTAMPTZ", nullable=False, default="now()")
    add_col("platform_proposals", "updated_at", "TIMESTAMPTZ", nullable=False, default="now()")

    # ===== platform_validations =====
    add_col("platform_validations", "proposal_id", "UUID", nullable=False)
    add_col("platform_validations", "agent_id", "UUID", nullable=False)
    add_col("platform_validations", "verdict", "validationverdict", nullable=False)
    add_col("platform_validations", "critique", "TEXT", nullable=False)
    add_col("platform_validations", "research_conducted", "TEXT")
    add_col("platform_validations", "scientific_issues", "TEXT[]", default="'{}'")
    add_col("platform_validations", "suggested_fixes", "TEXT[]", default="'{}'")
    add_col("platform_validations", "weaknesses", "TEXT[]")
    add_col("platform_validations", "created_at", "TIMESTAMPTZ", nullable=False, default="now()")

    # ===== platform_aspects =====
    add_col("platform_aspects", "world_id", "UUID", nullable=False)
    add_col("platform_aspects", "agent_id", "UUID", nullable=False)
    add_col("platform_aspects", "aspect_type", "VARCHAR(100)", nullable=False)
    add_col("platform_aspects", "title", "VARCHAR(255)", nullable=False)
    add_col("platform_aspects", "premise", "TEXT", nullable=False)
    add_col("platform_aspects", "content", "JSONB", nullable=False)
    add_col("platform_aspects", "canon_justification", "TEXT", nullable=False)
    add_col("platform_aspects", "inspired_by_actions", "JSONB", default="'[]'::jsonb")
    add_col("platform_aspects", "proposed_timeline_entry", "JSONB")
    add_col("platform_aspects", "status", "aspectstatus", nullable=False, default="'DRAFT'")
    add_col("platform_aspects", "created_at", "TIMESTAMPTZ", nullable=False, default="now()")
    add_col("platform_aspects", "updated_at", "TIMESTAMPTZ", nullable=False, default="now()")

    # ===== platform_aspect_validations =====
    add_col("platform_aspect_validations", "aspect_id", "UUID", nullable=False)
    add_col("platform_aspect_validations", "agent_id", "UUID", nullable=False)
    add_col("platform_aspect_validations", "verdict", "validationverdict", nullable=False)
    add_col("platform_aspect_validations", "critique", "TEXT", nullable=False)
    add_col("platform_aspect_validations", "canon_conflicts", "TEXT[]", default="'{}'")
    add_col("platform_aspect_validations", "suggested_fixes", "TEXT[]", default="'{}'")
    add_col("platform_aspect_validations", "updated_canon_summary", "TEXT")
    add_col("platform_aspect_validations", "approved_timeline_entry", "JSONB")
    add_col("platform_aspect_validations", "created_at", "TIMESTAMPTZ", nullable=False, default="now()")

    # ===== platform_dwellers =====
    add_col("platform_dwellers", "world_id", "UUID", nullable=False)
    add_col("platform_dwellers", "created_by", "UUID", nullable=False)
    add_col("platform_dwellers", "inhabited_by", "UUID")
    add_col("platform_dwellers", "name", "VARCHAR(100)", nullable=False)
    add_col("platform_dwellers", "origin_region", "VARCHAR(100)", nullable=False)
    add_col("platform_dwellers", "generation", "VARCHAR(50)", nullable=False, default="'first'")
    add_col("platform_dwellers", "name_context", "TEXT", nullable=False, default="''")
    add_col("platform_dwellers", "cultural_identity", "TEXT", nullable=False, default="''")
    add_col("platform_dwellers", "role", "VARCHAR(255)", nullable=False)
    add_col("platform_dwellers", "age", "INTEGER", nullable=False)
    add_col("platform_dwellers", "personality", "TEXT", nullable=False)
    add_col("platform_dwellers", "background", "TEXT", nullable=False)
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
    add_col("platform_dwellers", "created_at", "TIMESTAMPTZ", nullable=False, default="now()")
    add_col("platform_dwellers", "updated_at", "TIMESTAMPTZ", nullable=False, default="now()")
    add_col("platform_dwellers", "last_action_at", "TIMESTAMPTZ")

    # ===== platform_dweller_actions =====
    add_col("platform_dweller_actions", "dweller_id", "UUID", nullable=False)
    add_col("platform_dweller_actions", "actor_id", "UUID", nullable=False)
    add_col("platform_dweller_actions", "action_type", "VARCHAR(50)", nullable=False)
    add_col("platform_dweller_actions", "target", "VARCHAR(255)")
    add_col("platform_dweller_actions", "content", "TEXT", nullable=False)
    add_col("platform_dweller_actions", "importance", "FLOAT", nullable=False, default="0.5")
    add_col("platform_dweller_actions", "escalation_eligible", "BOOLEAN", nullable=False, default="false")
    add_col("platform_dweller_actions", "importance_confirmed_by", "UUID")
    add_col("platform_dweller_actions", "importance_confirmed_at", "TIMESTAMPTZ")
    add_col("platform_dweller_actions", "importance_confirmation_rationale", "TEXT")
    add_col("platform_dweller_actions", "created_at", "TIMESTAMPTZ", nullable=False, default="now()")

    # ===== platform_social_interactions =====
    add_col("platform_social_interactions", "user_id", "UUID", nullable=False)
    add_col("platform_social_interactions", "target_type", "VARCHAR(20)", nullable=False)
    add_col("platform_social_interactions", "target_id", "UUID", nullable=False)
    add_col("platform_social_interactions", "interaction_type", "VARCHAR(20)", nullable=False)
    add_col("platform_social_interactions", "data", "JSONB")
    add_col("platform_social_interactions", "created_at", "TIMESTAMPTZ", nullable=False, default="now()")

    # ===== platform_comments =====
    add_col("platform_comments", "user_id", "UUID", nullable=False)
    add_col("platform_comments", "target_type", "VARCHAR(20)", nullable=False)
    add_col("platform_comments", "target_id", "UUID", nullable=False)
    add_col("platform_comments", "content", "TEXT", nullable=False)
    add_col("platform_comments", "reaction", "VARCHAR(20)")
    add_col("platform_comments", "parent_id", "UUID")
    add_col("platform_comments", "created_at", "TIMESTAMPTZ", nullable=False, default="now()")
    add_col("platform_comments", "updated_at", "TIMESTAMPTZ", nullable=False, default="now()")
    add_col("platform_comments", "is_deleted", "BOOLEAN", default="false")

    # ===== platform_notifications =====
    add_col("platform_notifications", "user_id", "UUID", nullable=False)
    add_col("platform_notifications", "notification_type", "VARCHAR(50)", nullable=False)
    add_col("platform_notifications", "target_type", "VARCHAR(20)")
    add_col("platform_notifications", "target_id", "UUID")
    add_col("platform_notifications", "data", "JSONB")
    add_col("platform_notifications", "status", "notificationstatus", default="'PENDING'")
    add_col("platform_notifications", "created_at", "TIMESTAMPTZ", nullable=False, default="now()")
    add_col("platform_notifications", "sent_at", "TIMESTAMPTZ")
    add_col("platform_notifications", "read_at", "TIMESTAMPTZ")
    add_col("platform_notifications", "retry_count", "INTEGER", default="0")
    add_col("platform_notifications", "last_error", "TEXT")

    # ===== platform_revision_suggestions =====
    add_col("platform_revision_suggestions", "target_type", "VARCHAR(20)", nullable=False)
    add_col("platform_revision_suggestions", "target_id", "UUID", nullable=False)
    add_col("platform_revision_suggestions", "suggested_by", "UUID", nullable=False)
    add_col("platform_revision_suggestions", "field", "VARCHAR(100)", nullable=False)
    add_col("platform_revision_suggestions", "current_value", "JSONB")
    add_col("platform_revision_suggestions", "suggested_value", "JSONB", nullable=False)
    add_col("platform_revision_suggestions", "rationale", "TEXT", nullable=False)
    add_col("platform_revision_suggestions", "status", "revisionsuggestionstatus", default="'PENDING'")
    add_col("platform_revision_suggestions", "response_by", "UUID")
    add_col("platform_revision_suggestions", "response_reason", "TEXT")
    add_col("platform_revision_suggestions", "upvotes", "JSONB", default="'[]'::jsonb")
    add_col("platform_revision_suggestions", "owner_response_deadline", "TIMESTAMPTZ", nullable=False, default="now()")
    add_col("platform_revision_suggestions", "validator_can_accept_after", "TIMESTAMPTZ", nullable=False, default="now()")
    add_col("platform_revision_suggestions", "created_at", "TIMESTAMPTZ", nullable=False, default="now()")
    add_col("platform_revision_suggestions", "resolved_at", "TIMESTAMPTZ")

    # ===== platform_dweller_proposals =====
    add_col("platform_dweller_proposals", "world_id", "UUID", nullable=False)
    add_col("platform_dweller_proposals", "agent_id", "UUID", nullable=False)
    add_col("platform_dweller_proposals", "name", "VARCHAR(100)", nullable=False)
    add_col("platform_dweller_proposals", "origin_region", "VARCHAR(100)", nullable=False)
    add_col("platform_dweller_proposals", "generation", "VARCHAR(50)", nullable=False)
    add_col("platform_dweller_proposals", "name_context", "TEXT", nullable=False, default="''")
    add_col("platform_dweller_proposals", "cultural_identity", "TEXT", nullable=False, default="''")
    add_col("platform_dweller_proposals", "role", "VARCHAR(255)", nullable=False)
    add_col("platform_dweller_proposals", "age", "INTEGER", nullable=False)
    add_col("platform_dweller_proposals", "personality", "TEXT", nullable=False)
    add_col("platform_dweller_proposals", "background", "TEXT", nullable=False)
    add_col("platform_dweller_proposals", "core_memories", "JSONB", default="'[]'::jsonb")
    add_col("platform_dweller_proposals", "personality_blocks", "JSONB", default="'{}'::jsonb")
    add_col("platform_dweller_proposals", "current_situation", "TEXT", default="''")
    add_col("platform_dweller_proposals", "status", "dwellerproposalstatus", nullable=False, default="'DRAFT'")
    add_col("platform_dweller_proposals", "resulting_dweller_id", "UUID")
    add_col("platform_dweller_proposals", "created_at", "TIMESTAMPTZ", nullable=False, default="now()")
    add_col("platform_dweller_proposals", "updated_at", "TIMESTAMPTZ", nullable=False, default="now()")

    # ===== platform_dweller_validations =====
    add_col("platform_dweller_validations", "proposal_id", "UUID", nullable=False)
    add_col("platform_dweller_validations", "agent_id", "UUID", nullable=False)
    add_col("platform_dweller_validations", "verdict", "validationverdict", nullable=False)
    add_col("platform_dweller_validations", "critique", "TEXT", nullable=False)
    add_col("platform_dweller_validations", "cultural_issues", "TEXT[]", default="'{}'")
    add_col("platform_dweller_validations", "suggested_fixes", "TEXT[]", default="'{}'")
    add_col("platform_dweller_validations", "created_at", "TIMESTAMPTZ", nullable=False, default="now()")

    # ===== platform_stories =====
    add_col("platform_stories", "world_id", "UUID", nullable=False)
    add_col("platform_stories", "author_id", "UUID", nullable=False)
    add_col("platform_stories", "title", "VARCHAR(200)", nullable=False)
    add_col("platform_stories", "content", "TEXT", nullable=False)
    add_col("platform_stories", "summary", "VARCHAR(500)")
    add_col("platform_stories", "perspective", "storyperspective", nullable=False)
    add_col("platform_stories", "perspective_dweller_id", "UUID")
    add_col("platform_stories", "source_event_ids", "JSONB", default="'[]'::jsonb")
    add_col("platform_stories", "source_action_ids", "JSONB", default="'[]'::jsonb")
    add_col("platform_stories", "time_period_start", "VARCHAR(50)")
    add_col("platform_stories", "time_period_end", "VARCHAR(50)")
    add_col("platform_stories", "status", "storystatus", nullable=False, default="'PUBLISHED'")
    add_col("platform_stories", "reaction_count", "INTEGER", default="0")
    add_col("platform_stories", "comment_count", "INTEGER", default="0")
    add_col("platform_stories", "created_at", "TIMESTAMPTZ", nullable=False, default="now()")
    add_col("platform_stories", "updated_at", "TIMESTAMPTZ", nullable=False, default="now()")

    # ===== platform_story_reviews =====
    add_col("platform_story_reviews", "story_id", "UUID", nullable=False)
    add_col("platform_story_reviews", "reviewer_id", "UUID", nullable=False)
    add_col("platform_story_reviews", "recommend_acclaim", "BOOLEAN", nullable=False)
    add_col("platform_story_reviews", "improvements", "TEXT[]", nullable=False)
    add_col("platform_story_reviews", "canon_notes", "TEXT", nullable=False)
    add_col("platform_story_reviews", "event_notes", "TEXT", nullable=False)
    add_col("platform_story_reviews", "style_notes", "TEXT", nullable=False)
    add_col("platform_story_reviews", "canon_issues", "TEXT[]", default="'{}'")
    add_col("platform_story_reviews", "event_issues", "TEXT[]", default="'{}'")
    add_col("platform_story_reviews", "style_issues", "TEXT[]", default="'{}'")
    add_col("platform_story_reviews", "created_at", "TIMESTAMPTZ", nullable=False, default="now()")
    add_col("platform_story_reviews", "author_responded", "BOOLEAN", default="false")
    add_col("platform_story_reviews", "author_response", "TEXT")
    add_col("platform_story_reviews", "author_responded_at", "TIMESTAMPTZ")

    # ===== platform_feedback =====
    add_col("platform_feedback", "agent_id", "UUID", nullable=False)
    add_col("platform_feedback", "category", "feedbackcategory", nullable=False)
    add_col("platform_feedback", "priority", "feedbackpriority", nullable=False)
    add_col("platform_feedback", "title", "VARCHAR(255)", nullable=False)
    add_col("platform_feedback", "description", "TEXT", nullable=False)
    add_col("platform_feedback", "endpoint", "VARCHAR(255)")
    add_col("platform_feedback", "error_code", "INTEGER")
    add_col("platform_feedback", "error_message", "TEXT")
    add_col("platform_feedback", "expected_behavior", "TEXT")
    add_col("platform_feedback", "reproduction_steps", "JSONB")
    add_col("platform_feedback", "request_payload", "JSONB")
    add_col("platform_feedback", "response_payload", "JSONB")
    add_col("platform_feedback", "status", "feedbackstatus", nullable=False, default="'NEW'")
    add_col("platform_feedback", "resolution_notes", "TEXT")
    add_col("platform_feedback", "resolved_at", "TIMESTAMPTZ")
    add_col("platform_feedback", "resolved_by", "UUID")
    add_col("platform_feedback", "upvote_count", "INTEGER", default="0")
    add_col("platform_feedback", "upvoters", "JSONB", default="'[]'::jsonb")
    add_col("platform_feedback", "created_at", "TIMESTAMPTZ", nullable=False, default="now()")
    add_col("platform_feedback", "updated_at", "TIMESTAMPTZ", nullable=False, default="now()")

    # ===== platform_world_events =====
    add_col("platform_world_events", "world_id", "UUID", nullable=False)
    add_col("platform_world_events", "title", "VARCHAR(255)", nullable=False)
    add_col("platform_world_events", "description", "TEXT", nullable=False)
    add_col("platform_world_events", "year_in_world", "INTEGER", nullable=False)
    add_col("platform_world_events", "origin_type", "worldeventorigin", nullable=False, default="'PROPOSAL'")
    add_col("platform_world_events", "origin_action_id", "UUID")
    add_col("platform_world_events", "proposed_by", "UUID", nullable=False)
    add_col("platform_world_events", "canon_justification", "TEXT", nullable=False, default="''")
    add_col("platform_world_events", "status", "worldeventstatus", nullable=False, default="'PENDING'")
    add_col("platform_world_events", "approved_by", "UUID")
    add_col("platform_world_events", "rejection_reason", "TEXT")
    add_col("platform_world_events", "affected_regions", "JSONB", default="'[]'::jsonb")
    add_col("platform_world_events", "canon_update", "TEXT")
    add_col("platform_world_events", "created_at", "TIMESTAMPTZ", nullable=False, default="now()")
    add_col("platform_world_events", "approved_at", "TIMESTAMPTZ")


def downgrade() -> None:
    pass
