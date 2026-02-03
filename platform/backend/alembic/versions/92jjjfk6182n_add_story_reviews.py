"""Add story reviews table for community review system.

Revision ID: 92jjjfk6182n
Revises: 91iiiej5071m
Create Date: 2026-02-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "92jjjfk6182n"
down_revision: Union[str, None] = "91iiiej5071m"
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
    # Create storystatus enum if not exists
    if not enum_exists("storystatus"):
        op.execute(
            """CREATE TYPE storystatus AS ENUM ('published', 'acclaimed')"""
        )

    # Add status column to stories (default 'published' for existing stories)
    if not column_exists("platform_stories", "status"):
        op.add_column(
            "platform_stories",
            sa.Column(
                "status",
                postgresql.ENUM(
                    "published",
                    "acclaimed",
                    name="storystatus",
                    create_type=False,
                ),
                nullable=False,
                server_default="published",
            ),
        )

    # Add index on status column
    if not index_exists("story_status_idx"):
        op.create_index(
            "story_status_idx",
            "platform_stories",
            ["status"],
        )

    # Create story reviews table
    if not table_exists("platform_story_reviews"):
        op.create_table(
            "platform_story_reviews",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "story_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("platform_stories.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "reviewer_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("platform_users.id"),
                nullable=False,
            ),
            # Verdict
            sa.Column("recommend_acclaim", sa.Boolean, nullable=False),
            # MANDATORY feedback
            sa.Column("improvements", postgresql.ARRAY(sa.Text), nullable=False),
            # Assessment by criterion
            sa.Column("canon_notes", sa.Text, nullable=False),
            sa.Column("event_notes", sa.Text, nullable=False),
            sa.Column("style_notes", sa.Text, nullable=False),
            # Optional: specific issues found
            sa.Column(
                "canon_issues",
                postgresql.ARRAY(sa.Text),
                server_default="{}",
            ),
            sa.Column(
                "event_issues",
                postgresql.ARRAY(sa.Text),
                server_default="{}",
            ),
            sa.Column(
                "style_issues",
                postgresql.ARRAY(sa.Text),
                server_default="{}",
            ),
            # Timestamp
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            # Author response tracking
            sa.Column("author_responded", sa.Boolean, server_default="false"),
            sa.Column("author_response", sa.Text, nullable=True),
            sa.Column("author_responded_at", sa.DateTime(timezone=True), nullable=True),
        )

        # Create indexes
        op.create_index(
            "story_review_story_idx",
            "platform_story_reviews",
            ["story_id"],
        )
        op.create_index(
            "story_review_reviewer_idx",
            "platform_story_reviews",
            ["reviewer_id"],
        )
        op.create_index(
            "story_review_unique_idx",
            "platform_story_reviews",
            ["story_id", "reviewer_id"],
            unique=True,
        )


def downgrade() -> None:
    # Drop story reviews table
    if table_exists("platform_story_reviews"):
        op.drop_table("platform_story_reviews")

    # Drop index on status column
    if index_exists("story_status_idx"):
        op.drop_index("story_status_idx", table_name="platform_stories")

    # Drop status column from stories
    if column_exists("platform_stories", "status"):
        op.drop_column("platform_stories", "status")

    # Drop storystatus enum
    op.execute("DROP TYPE IF EXISTS storystatus")
