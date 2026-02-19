"""Add portrait_url to platform_dwellers.

Part of PROP-010 (World Art Generation — The Atlas), Phase 1.
Stores the URL of the AI-generated portrait image for each dweller.

Revision ID: 0020
Revises: 0019
"""
from typing import Union
from alembic import op
import sqlalchemy as sa

revision = "0020"
down_revision = "0019"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


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


def upgrade():
    if not column_exists("platform_dwellers", "portrait_url"):
        op.add_column(
            "platform_dwellers",
            sa.Column("portrait_url", sa.Text(), nullable=True),
        )


def downgrade():
    if column_exists("platform_dwellers", "portrait_url"):
        op.drop_column("platform_dwellers", "portrait_url")
