"""add maintenance and cycle-aware presence fields to platform_users

Revision ID: 0031
Revises: 0030
Create Date: 2026-02-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0031"
down_revision: Union[str, None] = "0030"
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
    if not column_exists("platform_users", "maintenance_until"):
        op.add_column(
            "platform_users",
            sa.Column("maintenance_until", sa.DateTime(timezone=True), nullable=True),
        )
    if not column_exists("platform_users", "maintenance_reason"):
        op.add_column(
            "platform_users",
            sa.Column("maintenance_reason", sa.String(length=100), nullable=True),
        )
    if not column_exists("platform_users", "expected_cycle_hours"):
        op.add_column(
            "platform_users",
            sa.Column("expected_cycle_hours", sa.Float(), nullable=True),
        )


def downgrade() -> None:
    if column_exists("platform_users", "expected_cycle_hours"):
        op.drop_column("platform_users", "expected_cycle_hours")
    if column_exists("platform_users", "maintenance_reason"):
        op.drop_column("platform_users", "maintenance_reason")
    if column_exists("platform_users", "maintenance_until"):
        op.drop_column("platform_users", "maintenance_until")
