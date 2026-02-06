"""Add revision tracking, conversation threading, and context tokens.

- platform_stories: revision_count (int), last_revised_at (datetime)
- platform_dweller_actions: in_reply_to_action_id (UUID, FK self)
- platform_dwellers: last_context_token (UUID), last_context_at (datetime)

Revision ID: 0007
Revises: 0006
Create Date: 2026-02-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "0007"
down_revision: str = "0006"
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


def upgrade() -> None:
    # --- platform_stories ---
    if not column_exists("platform_stories", "revision_count"):
        op.add_column(
            "platform_stories",
            sa.Column("revision_count", sa.Integer(), nullable=False, server_default="0"),
        )
    if not column_exists("platform_stories", "last_revised_at"):
        op.add_column(
            "platform_stories",
            sa.Column("last_revised_at", sa.DateTime(timezone=True), nullable=True),
        )

    # --- platform_dweller_actions ---
    if not column_exists("platform_dweller_actions", "in_reply_to_action_id"):
        op.add_column(
            "platform_dweller_actions",
            sa.Column("in_reply_to_action_id", UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            "fk_action_reply_to",
            "platform_dweller_actions",
            "platform_dweller_actions",
            ["in_reply_to_action_id"],
            ["id"],
        )
    if not index_exists("action_reply_to_idx"):
        op.create_index("action_reply_to_idx", "platform_dweller_actions", ["in_reply_to_action_id"])

    # --- platform_dwellers ---
    if not column_exists("platform_dwellers", "last_context_token"):
        op.add_column(
            "platform_dwellers",
            sa.Column("last_context_token", UUID(as_uuid=True), nullable=True),
        )
    if not column_exists("platform_dwellers", "last_context_at"):
        op.add_column(
            "platform_dwellers",
            sa.Column("last_context_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("platform_dwellers", "last_context_at")
    op.drop_column("platform_dwellers", "last_context_token")
    op.drop_index("action_reply_to_idx", table_name="platform_dweller_actions")
    op.drop_constraint("fk_action_reply_to", "platform_dweller_actions", type_="foreignkey")
    op.drop_column("platform_dweller_actions", "in_reply_to_action_id")
    op.drop_column("platform_stories", "last_revised_at")
    op.drop_column("platform_stories", "revision_count")
