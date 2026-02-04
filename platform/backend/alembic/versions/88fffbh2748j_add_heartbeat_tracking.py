"""Add last_heartbeat_at column to users.

Revision ID: 88fffbh2748j
Revises: 87eeebg1637i
Create Date: 2026-02-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "88fffbh2748j"
down_revision: Union[str, None] = "87eeebg1637i"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
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
    # Add last_heartbeat_at column for tracking agent activity
    if not column_exists("platform_users", "last_heartbeat_at"):
        op.add_column(
            "platform_users",
            sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    if column_exists("platform_users", "last_heartbeat_at"):
        op.drop_column("platform_users", "last_heartbeat_at")
