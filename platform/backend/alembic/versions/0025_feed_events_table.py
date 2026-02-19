"""Create platform_feed_events table.

A lightweight event log for feed rendering and activity streams.
Each row is an immutable event with a type, payload, and optional
FK associations to world/agent/dweller/story.

Revision ID: 0025
Revises: 0024
"""
from typing import Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0025"
down_revision = "0024"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = :table AND table_schema = 'public'"
    ), {"table": table_name})
    return result.fetchone() is not None


def upgrade():
    if table_exists("platform_feed_events"):
        return

    op.create_table(
        "platform_feed_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "world_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("platform_worlds.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("platform_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "dweller_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("platform_dwellers.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "story_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("platform_stories.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )

    op.create_index(
        "feed_events_created_at_idx",
        "platform_feed_events",
        [sa.text("created_at DESC")],
    )
    op.create_index(
        "feed_events_event_type_idx",
        "platform_feed_events",
        ["event_type"],
    )
    op.create_index(
        "feed_events_world_id_idx",
        "platform_feed_events",
        ["world_id"],
        postgresql_where=sa.text("world_id IS NOT NULL"),
    )


def downgrade():
    if not table_exists("platform_feed_events"):
        return

    op.drop_index("feed_events_world_id_idx", table_name="platform_feed_events")
    op.drop_index("feed_events_event_type_idx", table_name="platform_feed_events")
    op.drop_index("feed_events_created_at_idx", table_name="platform_feed_events")
    op.drop_table("platform_feed_events")
