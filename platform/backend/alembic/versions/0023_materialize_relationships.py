"""Materialize dweller relationships table.

Creates platform_dweller_relationships to store pre-computed relationship
scores between dwellers. Computed on story write, served from table — no
per-request computation.

Revision ID: 0023
Revises: 0022
"""
from typing import Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0023"
down_revision = "0022"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


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
    if not table_exists("platform_dweller_relationships"):
        op.create_table(
            "platform_dweller_relationships",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "dweller_a_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("platform_dwellers.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "dweller_b_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("platform_dwellers.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("co_occurrence_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("semantic_similarity", sa.Float(), nullable=True),
            sa.Column("combined_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column(
                "shared_story_ids",
                postgresql.JSONB(),
                nullable=False,
                server_default="[]",
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.UniqueConstraint("dweller_a_id", "dweller_b_id", name="uq_dweller_relationship_pair"),
            sa.CheckConstraint("dweller_a_id < dweller_b_id", name="ck_dweller_relationship_canonical_order"),
        )

    if not index_exists("idx_dweller_rel_a"):
        op.create_index("idx_dweller_rel_a", "platform_dweller_relationships", ["dweller_a_id"])
    if not index_exists("idx_dweller_rel_b"):
        op.create_index("idx_dweller_rel_b", "platform_dweller_relationships", ["dweller_b_id"])
    if not index_exists("idx_dweller_rel_score"):
        op.create_index(
            "idx_dweller_rel_score",
            "platform_dweller_relationships",
            [sa.text("combined_score DESC")],
        )


def downgrade():
    if index_exists("idx_dweller_rel_score"):
        op.drop_index("idx_dweller_rel_score", table_name="platform_dweller_relationships")
    if index_exists("idx_dweller_rel_b"):
        op.drop_index("idx_dweller_rel_b", table_name="platform_dweller_relationships")
    if index_exists("idx_dweller_rel_a"):
        op.drop_index("idx_dweller_rel_a", table_name="platform_dweller_relationships")
    if table_exists("platform_dweller_relationships"):
        op.drop_table("platform_dweller_relationships")
