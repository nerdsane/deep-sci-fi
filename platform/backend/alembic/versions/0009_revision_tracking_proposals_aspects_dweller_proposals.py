"""Add revision tracking to proposals, aspects, and dweller proposals.

Supports the strengthen gate: mandatory revision after strengthen feedback
before auto-approval can trigger.

- platform_proposals: revision_count (int), last_revised_at (datetime)
- platform_aspects: revision_count (int), last_revised_at (datetime)
- platform_dweller_proposals: revision_count (int), last_revised_at (datetime)

Revision ID: 0009
Revises: 0008
Create Date: 2026-02-06
"""
from alembic import op
import sqlalchemy as sa


revision: str = "0009"
down_revision: str = "0008"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :column"
    ), {"table": table_name, "column": column_name})
    return result.fetchone() is not None


def upgrade() -> None:
    tables = ["platform_proposals", "platform_aspects", "platform_dweller_proposals"]
    for table in tables:
        if not column_exists(table, "revision_count"):
            op.add_column(
                table,
                sa.Column("revision_count", sa.Integer(), nullable=False, server_default="0"),
            )
        if not column_exists(table, "last_revised_at"):
            op.add_column(
                table,
                sa.Column("last_revised_at", sa.DateTime(timezone=True), nullable=True),
            )


def downgrade() -> None:
    tables = ["platform_dweller_proposals", "platform_aspects", "platform_proposals"]
    for table in tables:
        op.drop_column(table, "last_revised_at")
        op.drop_column(table, "revision_count")
