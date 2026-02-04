"""Sync missing columns on existing tables.

Tables created by old migrations or create_all may be missing newer columns.
Uses ADD COLUMN IF NOT EXISTS for full idempotency.

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
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


def add_col(table, col, typedef, nullable=True, default=None):
    if column_exists(table, col):
        return
    null = "" if nullable else " NOT NULL"
    dflt = f" DEFAULT {default}" if default else ""
    op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {typedef}{null}{dflt}")


def upgrade() -> None:
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


def downgrade() -> None:
    pass  # Column removal not safe to automate
