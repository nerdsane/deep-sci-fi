"""Add story writing guidance and guidance token enforcement tables.

Revision ID: 0026
Revises: e97cb81af096
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0026"
down_revision = "e97cb81af096"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :table"
        ),
        {"table": table_name},
    )
    return result.fetchone() is not None


def column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :table AND column_name = :column"
        ),
        {"table": table_name, "column": column_name},
    )
    return result.fetchone() is not None


def index_exists(index_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_indexes "
            "WHERE schemaname = 'public' AND indexname = :index_name"
        ),
        {"index_name": index_name},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    if not table_exists("story_writing_guidance"):
        op.create_table(
            "story_writing_guidance",
            sa.Column("version", sa.String(length=50), nullable=False),
            sa.Column("rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("examples", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("created_by", sa.String(length=100), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.PrimaryKeyConstraint("version"),
        )

    if not index_exists("story_writing_guidance_active_idx"):
        op.create_index(
            "story_writing_guidance_active_idx",
            "story_writing_guidance",
            ["is_active"],
        )
    if not index_exists("story_writing_guidance_created_at_idx"):
        op.create_index(
            "story_writing_guidance_created_at_idx",
            "story_writing_guidance",
            ["created_at"],
        )

    if not column_exists("platform_stories", "guidance_version_used"):
        op.add_column(
            "platform_stories",
            sa.Column("guidance_version_used", sa.String(length=50), nullable=True),
        )

    if not table_exists("guidance_tokens"):
        op.create_table(
            "guidance_tokens",
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("guidance_version", sa.String(length=50), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("consumed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["guidance_version"],
                ["story_writing_guidance.version"],
            ),
            sa.ForeignKeyConstraint(
                ["story_id"],
                ["platform_stories.id"],
            ),
            sa.PrimaryKeyConstraint("token_hash"),
        )

    if not index_exists("guidance_tokens_guidance_version_idx"):
        op.create_index(
            "guidance_tokens_guidance_version_idx",
            "guidance_tokens",
            ["guidance_version"],
        )
    if not index_exists("guidance_tokens_expires_at_idx"):
        op.create_index(
            "guidance_tokens_expires_at_idx",
            "guidance_tokens",
            ["expires_at"],
        )
    if not index_exists("guidance_tokens_consumed_idx"):
        op.create_index(
            "guidance_tokens_consumed_idx",
            "guidance_tokens",
            ["consumed"],
        )


def downgrade() -> None:
    if index_exists("guidance_tokens_consumed_idx"):
        op.drop_index("guidance_tokens_consumed_idx", table_name="guidance_tokens")
    if index_exists("guidance_tokens_expires_at_idx"):
        op.drop_index("guidance_tokens_expires_at_idx", table_name="guidance_tokens")
    if index_exists("guidance_tokens_guidance_version_idx"):
        op.drop_index("guidance_tokens_guidance_version_idx", table_name="guidance_tokens")
    if table_exists("guidance_tokens"):
        op.drop_table("guidance_tokens")

    if column_exists("platform_stories", "guidance_version_used"):
        op.drop_column("platform_stories", "guidance_version_used")

    if index_exists("story_writing_guidance_created_at_idx"):
        op.drop_index(
            "story_writing_guidance_created_at_idx",
            table_name="story_writing_guidance",
        )
    if index_exists("story_writing_guidance_active_idx"):
        op.drop_index(
            "story_writing_guidance_active_idx",
            table_name="story_writing_guidance",
        )
    if table_exists("story_writing_guidance"):
        op.drop_table("story_writing_guidance")
