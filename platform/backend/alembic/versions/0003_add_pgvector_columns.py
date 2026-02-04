"""Add pgvector premise_embedding columns.

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
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


def upgrade() -> None:
    conn = op.get_bind()
    try:
        conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS vector")
        for table in ["platform_worlds", "platform_proposals", "platform_aspects"]:
            if not column_exists(table, "premise_embedding"):
                conn.exec_driver_sql(
                    f"ALTER TABLE {table} ADD COLUMN premise_embedding vector(1536)"
                )
    except Exception:
        pass  # pgvector not available


def downgrade() -> None:
    pass
