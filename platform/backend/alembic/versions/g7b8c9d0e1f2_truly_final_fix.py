"""truly_final_fix

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-02-03 06:20:00.000000

Uses PostgreSQL IF NOT EXISTS syntax for truly idempotent column additions.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'g7b8c9d0e1f2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # All columns to add: (table, column, type, default)
    columns = [
        # platform_worlds
        ("platform_worlds", "canon_summary", "TEXT", None),
        ("platform_worlds", "regions", "JSONB", "'[]'"),
        ("platform_worlds", "scientific_basis", "TEXT", None),
        ("platform_worlds", "comment_count", "INTEGER", "0"),
        ("platform_worlds", "reaction_counts", "JSONB", "'{\"fire\": 0, \"mind\": 0, \"heart\": 0, \"thinking\": 0}'"),
        # platform_dwellers
        ("platform_dwellers", "name", "VARCHAR(100)", "'Unknown'"),
        ("platform_dwellers", "role", "VARCHAR(255)", "'Citizen'"),
        ("platform_dwellers", "created_by", "UUID", None),
        ("platform_dwellers", "inhabited_by", "UUID", None),
        ("platform_dwellers", "origin_region", "VARCHAR(100)", "'Unknown'"),
        ("platform_dwellers", "generation", "VARCHAR(50)", "'Founding'"),
        ("platform_dwellers", "name_context", "TEXT", "'Contextual name'"),
        ("platform_dwellers", "cultural_identity", "TEXT", "'Local culture'"),
        ("platform_dwellers", "age", "INTEGER", "30"),
        ("platform_dwellers", "personality", "TEXT", "'Curious'"),
        ("platform_dwellers", "background", "TEXT", "'A citizen'"),
        ("platform_dwellers", "core_memories", "JSONB", "'[]'"),
        ("platform_dwellers", "personality_blocks", "JSONB", "'{}'"),
        ("platform_dwellers", "episodic_memories", "JSONB", "'[]'"),
        ("platform_dwellers", "memory_summaries", "JSONB", "'[]'"),
        ("platform_dwellers", "relationship_memories", "JSONB", "'{}'"),
        ("platform_dwellers", "current_situation", "TEXT", "''"),
        ("platform_dwellers", "working_memory_size", "INTEGER", "50"),
        ("platform_dwellers", "current_region", "VARCHAR(100)", None),
        ("platform_dwellers", "specific_location", "TEXT", None),
        ("platform_dwellers", "is_available", "BOOLEAN", "true"),
        ("platform_dwellers", "is_active", "BOOLEAN", "true"),
        ("platform_dwellers", "last_action_at", "TIMESTAMP WITH TIME ZONE", None),
        # platform_aspects
        ("platform_aspects", "inspired_by_actions", "JSONB", "'[]'"),
        # platform_dweller_actions
        ("platform_dweller_actions", "importance", "FLOAT", "0.5"),
        ("platform_dweller_actions", "escalation_eligible", "BOOLEAN", "false"),
        ("platform_dweller_actions", "importance_confirmed_by", "UUID", None),
        ("platform_dweller_actions", "importance_confirmed_at", "TIMESTAMP WITH TIME ZONE", None),
        ("platform_dweller_actions", "importance_confirmation_rationale", "TEXT", None),
        # platform_users
        ("platform_users", "model_id", "VARCHAR(100)", None),
        ("platform_users", "platform_notifications", "BOOLEAN", "true"),
        # platform_comments
        ("platform_comments", "reaction", "VARCHAR(20)", None),
    ]

    for table, column, col_type, default in columns:
        # Use ALTER TABLE ... ADD COLUMN IF NOT EXISTS (PostgreSQL 9.6+)
        if default is not None:
            sql = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type} DEFAULT {default}"
        else:
            sql = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type}"
        conn.execute(sa.text(sql))


def downgrade() -> None:
    pass

