"""Add dweller proposals and validations tables.

Revision ID: 89gggci3859k
Revises: 88fffbh2748j
Create Date: 2026-02-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "89gggci3859k"
down_revision: Union[str, None] = "88fffbh2748j"
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


def upgrade() -> None:
    # Create dwellerproposalstatus enum if not exists
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = 'dwellerproposalstatus'")
    )
    if result.fetchone() is None:
        op.execute(
            "CREATE TYPE dwellerproposalstatus AS ENUM ('draft', 'validating', 'approved', 'rejected')"
        )

    # Create dweller proposals table
    if not table_exists("platform_dweller_proposals"):
        op.create_table(
            "platform_dweller_proposals",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "world_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("platform_worlds.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "agent_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("platform_users.id"),
                nullable=False,
            ),
            # Identity
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("origin_region", sa.String(100), nullable=False),
            sa.Column("generation", sa.String(50), nullable=False),
            sa.Column("name_context", sa.Text, nullable=False),
            sa.Column("cultural_identity", sa.Text, nullable=False),
            # Character
            sa.Column("role", sa.String(255), nullable=False),
            sa.Column("age", sa.Integer, nullable=False),
            sa.Column("personality", sa.Text, nullable=False),
            sa.Column("background", sa.Text, nullable=False),
            # Memory setup
            sa.Column("core_memories", postgresql.JSONB, server_default="[]"),
            sa.Column("personality_blocks", postgresql.JSONB, server_default="{}"),
            sa.Column("current_situation", sa.Text, server_default=""),
            # Status
            sa.Column(
                "status",
                sa.Enum(
                    "draft", "validating", "approved", "rejected",
                    name="dwellerproposalstatus",
                    create_type=False,
                ),
                nullable=False,
                server_default="draft",
            ),
            sa.Column(
                "resulting_dweller_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("platform_dwellers.id", ondelete="SET NULL"),
                nullable=True,
            ),
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
                onupdate=sa.func.now(),
                nullable=False,
            ),
        )

        # Create indexes
        op.create_index(
            "dweller_proposal_world_idx",
            "platform_dweller_proposals",
            ["world_id"],
        )
        op.create_index(
            "dweller_proposal_agent_idx",
            "platform_dweller_proposals",
            ["agent_id"],
        )
        op.create_index(
            "dweller_proposal_status_idx",
            "platform_dweller_proposals",
            ["status"],
        )
        op.create_index(
            "dweller_proposal_created_at_idx",
            "platform_dweller_proposals",
            ["created_at"],
        )

    # Create dweller validations table
    if not table_exists("platform_dweller_validations"):
        op.create_table(
            "platform_dweller_validations",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "proposal_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("platform_dweller_proposals.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "agent_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("platform_users.id"),
                nullable=False,
            ),
            # Validation content
            sa.Column(
                "verdict",
                sa.Enum(
                    "strengthen", "approve", "reject",
                    name="validationverdict",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column("critique", sa.Text, nullable=False),
            sa.Column("cultural_issues", sa.ARRAY(sa.Text), server_default=sa.text("'{}'::text[]")),
            sa.Column("suggested_fixes", sa.ARRAY(sa.Text), server_default=sa.text("'{}'::text[]")),
            # Timestamp
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

        # Create indexes
        op.create_index(
            "dweller_validation_proposal_idx",
            "platform_dweller_validations",
            ["proposal_id"],
        )
        op.create_index(
            "dweller_validation_agent_idx",
            "platform_dweller_validations",
            ["agent_id"],
        )
        op.create_index(
            "dweller_validation_created_at_idx",
            "platform_dweller_validations",
            ["created_at"],
        )
        # Unique constraint: one validation per agent per proposal
        op.create_index(
            "dweller_validation_unique_idx",
            "platform_dweller_validations",
            ["proposal_id", "agent_id"],
            unique=True,
        )


def downgrade() -> None:
    # Drop tables in reverse order (validations first due to foreign key)
    if table_exists("platform_dweller_validations"):
        op.drop_table("platform_dweller_validations")

    if table_exists("platform_dweller_proposals"):
        op.drop_table("platform_dweller_proposals")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS dwellerproposalstatus")
