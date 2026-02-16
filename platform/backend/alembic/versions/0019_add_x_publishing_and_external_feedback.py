"""Add X publishing columns to stories and external_feedback table.

Adds x_post_id, x_published_at to platform_stories for tracking X publications.
Creates platform_external_feedback table for ingesting human engagement signals.

Revision ID: 0019
Revises: 0018
"""
from typing import Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0019"
down_revision = "0018"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :column"
    ), {"table": table_name, "column": column_name})
    return result.fetchone() is not None


def table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = :table"
    ), {"table": table_name})
    return result.fetchone() is not None


def index_exists(index_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname = :name"
    ), {"name": index_name})
    return result.fetchone() is not None


def upgrade():
    # --- Add X publishing columns to platform_stories ---
    if not column_exists("platform_stories", "x_post_id"):
        op.add_column("platform_stories", sa.Column("x_post_id", sa.Text(), nullable=True))

    if not column_exists("platform_stories", "x_published_at"):
        op.add_column("platform_stories", sa.Column("x_published_at", sa.DateTime(timezone=True), nullable=True))

    if not index_exists("story_x_post_id_idx"):
        op.create_index("story_x_post_id_idx", "platform_stories", ["x_post_id"])

    # --- Create platform_external_feedback table ---
    if not table_exists("platform_external_feedback"):
        op.create_table(
            "platform_external_feedback",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("story_id", postgresql.UUID(as_uuid=True),
                       sa.ForeignKey("platform_stories.id", ondelete="CASCADE"), nullable=False),
            sa.Column("source", sa.String(50), nullable=False),
            sa.Column("source_post_id", sa.Text(), nullable=False),
            sa.Column("source_user", sa.Text(), nullable=True),
            sa.Column("feedback_type", sa.String(50), nullable=False),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column("sentiment", sa.String(50), nullable=True),
            sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
            sa.Column("is_human", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("processed", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ext_feedback_story_idx", "platform_external_feedback", ["story_id"])
        op.create_index("ext_feedback_source_idx", "platform_external_feedback", ["source"])
        op.create_index("ext_feedback_type_idx", "platform_external_feedback", ["feedback_type"])
        op.create_index("ext_feedback_created_at_idx", "platform_external_feedback", ["created_at"])
        op.create_index("ext_feedback_source_post_idx", "platform_external_feedback",
                         ["source", "source_post_id"], unique=True)


def downgrade():
    op.drop_table("platform_external_feedback")
    op.drop_index("story_x_post_id_idx", table_name="platform_stories")
    op.drop_column("platform_stories", "x_published_at")
    op.drop_column("platform_stories", "x_post_id")
