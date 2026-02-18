"""Add story arc detection: content_embedding column + platform_story_arcs table.

Adds content_embedding (vector 1536) to platform_stories for semantic similarity.
Creates platform_story_arcs table to track detected narrative arcs.

Revision ID: 0022
Revises: 0021
"""
from typing import Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0022"
down_revision = "0021"
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
    # --- Ensure pgvector extension exists ---
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # --- Add content_embedding column to platform_stories ---
    if not column_exists("platform_stories", "content_embedding"):
        op.execute(
            "ALTER TABLE platform_stories ADD COLUMN content_embedding vector(1536)"
        )

    # --- Create platform_story_arcs table ---
    if not table_exists("platform_story_arcs"):
        op.create_table(
            "platform_story_arcs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                      server_default=sa.text("gen_random_uuid()")),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("world_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("platform_worlds.id", ondelete="CASCADE"), nullable=False),
            sa.Column("dweller_id", postgresql.UUID(as_uuid=True),
                      sa.ForeignKey("platform_dwellers.id", ondelete="SET NULL"), nullable=True),
            sa.Column("story_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
            sa.Column("created_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True),
                      server_default=sa.func.now(), nullable=False),
        )

    if not index_exists("story_arc_world_idx"):
        op.create_index("story_arc_world_idx", "platform_story_arcs", ["world_id"])
    if not index_exists("story_arc_dweller_idx"):
        op.create_index("story_arc_dweller_idx", "platform_story_arcs", ["dweller_id"])
    if not index_exists("story_arc_created_at_idx"):
        op.create_index("story_arc_created_at_idx", "platform_story_arcs", ["created_at"])

    # GIN index to accelerate JSONB containment queries (@>) on story_ids
    # Required for efficient GET /stories/{id}/arc lookups
    if not index_exists("story_arc_story_ids_gin_idx"):
        op.execute(
            "CREATE INDEX story_arc_story_ids_gin_idx ON platform_story_arcs USING GIN (story_ids)"
        )


def downgrade():
    if index_exists("story_arc_story_ids_gin_idx"):
        op.drop_index("story_arc_story_ids_gin_idx", table_name="platform_story_arcs")
    if index_exists("story_arc_created_at_idx"):
        op.drop_index("story_arc_created_at_idx", table_name="platform_story_arcs")
    if index_exists("story_arc_dweller_idx"):
        op.drop_index("story_arc_dweller_idx", table_name="platform_story_arcs")
    if index_exists("story_arc_world_idx"):
        op.drop_index("story_arc_world_idx", table_name="platform_story_arcs")
    if table_exists("platform_story_arcs"):
        op.drop_table("platform_story_arcs")
    if column_exists("platform_stories", "content_embedding"):
        op.drop_column("platform_stories", "content_embedding")
