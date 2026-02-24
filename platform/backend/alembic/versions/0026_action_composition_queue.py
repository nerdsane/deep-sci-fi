"""add action composition queue table

Revision ID: 0026
Revises: e97cb81af096
Create Date: 2026-02-24 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0026"
down_revision: Union[str, None] = "e97cb81af096"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'platform_action_composition_queue'"
        )
    )
    if result.fetchone() is not None:
        return

    op.create_table(
        "platform_action_composition_queue",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID(), nullable=False),
        sa.Column("dweller_id", sa.UUID(), nullable=False),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("composed_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_action_id", sa.UUID(), nullable=True),
        sa.Column("submission_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["agent_id"], ["platform_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dweller_id"], ["platform_dwellers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitted_action_id"], ["platform_dweller_actions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )

    op.create_index(
        "action_comp_queue_agent_idx",
        "platform_action_composition_queue",
        ["agent_id"],
    )
    op.create_index(
        "action_comp_queue_dweller_idx",
        "platform_action_composition_queue",
        ["dweller_id"],
    )
    op.create_index(
        "action_comp_queue_submitted_idx",
        "platform_action_composition_queue",
        ["submitted_at"],
    )
    op.create_index(
        "action_comp_queue_next_attempt_idx",
        "platform_action_composition_queue",
        ["next_attempt_at"],
    )
    op.create_index(
        "action_comp_queue_composed_at_idx",
        "platform_action_composition_queue",
        ["composed_at"],
    )


def downgrade() -> None:
    op.drop_index("action_comp_queue_composed_at_idx", table_name="platform_action_composition_queue")
    op.drop_index("action_comp_queue_next_attempt_idx", table_name="platform_action_composition_queue")
    op.drop_index("action_comp_queue_submitted_idx", table_name="platform_action_composition_queue")
    op.drop_index("action_comp_queue_dweller_idx", table_name="platform_action_composition_queue")
    op.drop_index("action_comp_queue_agent_idx", table_name="platform_action_composition_queue")
    op.drop_table("platform_action_composition_queue")
