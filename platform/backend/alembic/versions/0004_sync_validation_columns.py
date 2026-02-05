"""Sync missing columns on validation and remaining tables.

Revision ID: 0004
Revises: 0003
Create Date: 2026-02-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
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
    sql = f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {typedef}{null}{dflt}"
    op.get_bind().exec_driver_sql(sql)


def upgrade() -> None:
    # platform_validations
    add_col("platform_validations", "research_conducted", "TEXT")
    add_col("platform_validations", "scientific_issues", "TEXT[]", default="'{}'")
    add_col("platform_validations", "suggested_fixes", "TEXT[]", default="'{}'")
    add_col("platform_validations", "weaknesses", "TEXT[]")

    # platform_aspect_validations
    add_col("platform_aspect_validations", "canon_conflicts", "TEXT[]", default="'{}'")
    add_col("platform_aspect_validations", "suggested_fixes", "TEXT[]", default="'{}'")
    add_col("platform_aspect_validations", "updated_canon_summary", "TEXT")
    add_col("platform_aspect_validations", "approved_timeline_entry", "JSONB")

    # platform_dweller_validations
    add_col("platform_dweller_validations", "cultural_issues", "TEXT[]", default="'{}'")
    add_col("platform_dweller_validations", "suggested_fixes", "TEXT[]", default="'{}'")

    # platform_comments
    add_col("platform_comments", "reaction", "VARCHAR(20)")
    add_col("platform_comments", "parent_id", "UUID")
    add_col("platform_comments", "is_deleted", "BOOLEAN", default="false")

    # platform_revision_suggestions
    add_col("platform_revision_suggestions", "response_by", "UUID")
    add_col("platform_revision_suggestions", "response_reason", "TEXT")
    add_col("platform_revision_suggestions", "upvotes", "JSONB", default="'[]'::jsonb")

    # platform_api_keys
    add_col("platform_api_keys", "name", "VARCHAR(100)")
    add_col("platform_api_keys", "last_used_at", "TIMESTAMPTZ")
    add_col("platform_api_keys", "expires_at", "TIMESTAMPTZ")
    add_col("platform_api_keys", "is_revoked", "BOOLEAN", default="false")


def downgrade() -> None:
    pass
