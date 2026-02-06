"""Add unique constraint on api_key key_hash.

Prevents duplicate API key rows which cause MultipleResultsFound
errors in get_current_user when scalar_one_or_none() finds >1 row.

Revision ID: 0008
Revises: 0007
Create Date: 2026-02-06
"""
from alembic import op
import sqlalchemy as sa


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :column"
    ), {"table": table_name, "column": column_name})
    return result.fetchone() is not None


def index_exists(index_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname = :name"
    ), {"name": index_name})
    return result.fetchone() is not None


def upgrade():
    # Remove any duplicate key_hash rows before adding unique constraint
    # Keep only the most recently created row for each hash
    op.execute(sa.text("""
        DELETE FROM platform_api_keys a
        USING platform_api_keys b
        WHERE a.key_hash = b.key_hash
          AND a.id != b.id
          AND a.created_at < b.created_at
    """))

    if not index_exists("uq_platform_api_keys_key_hash"):
        op.create_unique_constraint(
            "uq_platform_api_keys_key_hash",
            "platform_api_keys",
            ["key_hash"],
        )


def downgrade():
    if index_exists("uq_platform_api_keys_key_hash"):
        op.drop_constraint(
            "uq_platform_api_keys_key_hash",
            "platform_api_keys",
            type_="unique",
        )
