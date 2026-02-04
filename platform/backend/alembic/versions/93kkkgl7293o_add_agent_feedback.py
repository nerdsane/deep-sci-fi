"""Add agent feedback table for closed-loop development.

Revision ID: 93kkkgl7293o
Revises: 92jjjfk6182n
Create Date: 2026-02-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "93kkkgl7293o"
down_revision: Union[str, None] = "92jjjfk6182n"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = :table"
        ),
        {"table": table_name},
    )
    return result.fetchone() is not None


def enum_exists(enum_name: str) -> bool:
    """Check if an enum type exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :name"),
        {"name": enum_name},
    )
    return result.fetchone() is not None


def index_exists(index_name: str) -> bool:
    """Check if an index exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :name"),
        {"name": index_name},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    # Create feedbackcategory enum if not exists
    if not enum_exists("feedbackcategory"):
        op.execute(
            """CREATE TYPE feedbackcategory AS ENUM (
                'api_bug', 'api_usability', 'documentation',
                'feature_request', 'error_message', 'performance'
            )"""
        )

    # Create feedbackpriority enum if not exists
    if not enum_exists("feedbackpriority"):
        op.execute(
            """CREATE TYPE feedbackpriority AS ENUM (
                'critical', 'high', 'medium', 'low'
            )"""
        )

    # Create feedbackstatus enum if not exists
    if not enum_exists("feedbackstatus"):
        op.execute(
            """CREATE TYPE feedbackstatus AS ENUM (
                'new', 'acknowledged', 'in_progress', 'resolved', 'wont_fix'
            )"""
        )

    # Create feedback table
    if not table_exists("platform_feedback"):
        op.create_table(
            "platform_feedback",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "agent_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("platform_users.id"),
                nullable=False,
            ),
            # Classification
            sa.Column(
                "category",
                postgresql.ENUM(
                    "api_bug", "api_usability", "documentation",
                    "feature_request", "error_message", "performance",
                    name="feedbackcategory",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column(
                "priority",
                postgresql.ENUM(
                    "critical", "high", "medium", "low",
                    name="feedbackpriority",
                    create_type=False,
                ),
                nullable=False,
            ),
            # Content
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.Text, nullable=False),
            # Technical context
            sa.Column("endpoint", sa.String(255), nullable=True),
            sa.Column("error_code", sa.Integer, nullable=True),
            sa.Column("error_message", sa.Text, nullable=True),
            sa.Column("expected_behavior", sa.Text, nullable=True),
            sa.Column("reproduction_steps", postgresql.JSONB, nullable=True),
            sa.Column("request_payload", postgresql.JSONB, nullable=True),
            sa.Column("response_payload", postgresql.JSONB, nullable=True),
            # Status tracking
            sa.Column(
                "status",
                postgresql.ENUM(
                    "new", "acknowledged", "in_progress", "resolved", "wont_fix",
                    name="feedbackstatus",
                    create_type=False,
                ),
                nullable=False,
                server_default="new",
            ),
            sa.Column("resolution_notes", sa.Text, nullable=True),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "resolved_by",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("platform_users.id"),
                nullable=True,
            ),
            # Community voting
            sa.Column("upvote_count", sa.Integer, server_default="0"),
            sa.Column("upvoters", postgresql.JSONB, server_default="[]"),
            # Timestamps
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

        # Create indexes
        if not index_exists("feedback_agent_idx"):
            op.create_index(
                "feedback_agent_idx",
                "platform_feedback",
                ["agent_id"],
            )
        if not index_exists("feedback_status_idx"):
            op.create_index(
                "feedback_status_idx",
                "platform_feedback",
                ["status"],
            )
        if not index_exists("feedback_priority_idx"):
            op.create_index(
                "feedback_priority_idx",
                "platform_feedback",
                ["priority"],
            )
        if not index_exists("feedback_category_idx"):
            op.create_index(
                "feedback_category_idx",
                "platform_feedback",
                ["category"],
            )
        if not index_exists("feedback_created_at_idx"):
            op.create_index(
                "feedback_created_at_idx",
                "platform_feedback",
                ["created_at"],
            )
        if not index_exists("feedback_upvote_count_idx"):
            op.create_index(
                "feedback_upvote_count_idx",
                "platform_feedback",
                ["upvote_count"],
            )


def downgrade() -> None:
    # Drop indexes
    for idx_name in [
        "feedback_agent_idx",
        "feedback_status_idx",
        "feedback_priority_idx",
        "feedback_category_idx",
        "feedback_created_at_idx",
        "feedback_upvote_count_idx",
    ]:
        if index_exists(idx_name):
            op.drop_index(idx_name, table_name="platform_feedback")

    # Drop table
    if table_exists("platform_feedback"):
        op.drop_table("platform_feedback")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS feedbackstatus")
    op.execute("DROP TYPE IF EXISTS feedbackpriority")
    op.execute("DROP TYPE IF EXISTS feedbackcategory")
