"""Add dialogue and stage_direction to DwellerAction.

Restructures SPEAK actions from single 'content' blob to:
- dialogue: Text, nullable - Direct speech only
- stage_direction: Text, nullable - Physical actions, scene setting

Backwards compatible: existing actions keep content as-is.

Revision ID: 0015
Revises: 0014
Create Date: 2026-02-14
"""
from alembic import op
import sqlalchemy as sa


revision: str = "0015"
down_revision: str = "0014"
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
    # Add dialogue to platform_dweller_actions
    if not column_exists("platform_dweller_actions", "dialogue"):
        op.add_column(
            "platform_dweller_actions",
            sa.Column("dialogue", sa.Text(), nullable=True),
        )

    # Add stage_direction to platform_dweller_actions
    if not column_exists("platform_dweller_actions", "stage_direction"):
        op.add_column(
            "platform_dweller_actions",
            sa.Column("stage_direction", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("platform_dweller_actions", "stage_direction")
    op.drop_column("platform_dweller_actions", "dialogue")
