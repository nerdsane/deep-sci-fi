"""Add stories table for narrative content.

Revision ID: 90hhhdi4960l
Revises: 89gggci3859k
Create Date: 2026-02-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "90hhhdi4960l"
down_revision: Union[str, None] = "89gggci3859k"
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


def upgrade() -> None:
    # Create storyperspective enum if not exists
    if not enum_exists("storyperspective"):
        op.execute(
            """CREATE TYPE storyperspective AS ENUM (
                'first_person_agent',
                'first_person_dweller',
                'third_person_limited',
                'third_person_omniscient'
            )"""
        )

    # Create stories table
    if not table_exists("platform_stories"):
        op.create_table(
            "platform_stories",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "world_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("platform_worlds.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "author_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("platform_users.id"),
                nullable=False,
            ),
            # Content
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("content", sa.Text, nullable=False),
            sa.Column("summary", sa.String(500), nullable=True),
            # Perspective
            sa.Column(
                "perspective",
                sa.Enum(
                    "first_person_agent",
                    "first_person_dweller",
                    "third_person_limited",
                    "third_person_omniscient",
                    name="storyperspective",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column(
                "perspective_dweller_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("platform_dwellers.id", ondelete="SET NULL"),
                nullable=True,
            ),
            # Sources
            sa.Column("source_event_ids", postgresql.JSONB, server_default="[]"),
            sa.Column("source_action_ids", postgresql.JSONB, server_default="[]"),
            sa.Column("time_period_start", sa.String(50), nullable=True),
            sa.Column("time_period_end", sa.String(50), nullable=True),
            # Engagement
            sa.Column("reaction_count", sa.Integer, server_default="0", nullable=False),
            sa.Column("comment_count", sa.Integer, server_default="0", nullable=False),
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
        op.create_index(
            "story_world_idx",
            "platform_stories",
            ["world_id"],
        )
        op.create_index(
            "story_author_idx",
            "platform_stories",
            ["author_id"],
        )
        op.create_index(
            "story_reaction_count_idx",
            "platform_stories",
            ["reaction_count"],
        )
        op.create_index(
            "story_created_at_idx",
            "platform_stories",
            ["created_at"],
        )


def downgrade() -> None:
    # Drop table
    if table_exists("platform_stories"):
        op.drop_table("platform_stories")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS storyperspective")
