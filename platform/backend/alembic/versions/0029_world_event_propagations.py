"""add world event propagation tracking table

Revision ID: 0029
Revises: 0028
Create Date: 2026-02-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0029"
down_revision: Union[str, None] = "0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = :table"
        ),
        {"table": table_name},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    if table_exists("platform_world_event_propagations"):
        return

    op.create_table(
        "platform_world_event_propagations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("world_event_id", sa.UUID(), nullable=False),
        sa.Column("dweller_id", sa.UUID(), nullable=False),
        sa.Column("propagated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["world_event_id"], ["platform_world_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dweller_id"], ["platform_dwellers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("world_event_id", "dweller_id", name="world_event_prop_event_dweller_key"),
    )

    op.create_index(
        "world_event_prop_event_idx",
        "platform_world_event_propagations",
        ["world_event_id"],
    )
    op.create_index(
        "world_event_prop_dweller_idx",
        "platform_world_event_propagations",
        ["dweller_id"],
    )
    op.create_index(
        "world_event_prop_propagated_at_idx",
        "platform_world_event_propagations",
        ["propagated_at"],
    )


def downgrade() -> None:
    op.drop_index("world_event_prop_propagated_at_idx", table_name="platform_world_event_propagations")
    op.drop_index("world_event_prop_dweller_idx", table_name="platform_world_event_propagations")
    op.drop_index("world_event_prop_event_idx", table_name="platform_world_event_propagations")
    op.drop_table("platform_world_event_propagations")
