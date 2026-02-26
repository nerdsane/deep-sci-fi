"""agent calibration loop schema updates

Revision ID: 0029
Revises: 0028
Create Date: 2026-02-25 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0029"
down_revision: Union[str, None] = "0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :table_name"
        ),
        {"table_name": table_name},
    )
    return result.fetchone() is not None


def column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :table_name "
            "AND column_name = :column_name"
        ),
        {"table_name": table_name, "column_name": column_name},
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
    if not table_exists("platform_guidance_compliance_signals"):
        op.create_table(
            "platform_guidance_compliance_signals",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("story_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("guidance_version", sa.String(length=100), nullable=False),
            sa.Column("review_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(
                "signal_data",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'{}'::jsonb"),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["story_id"],
                ["platform_stories.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["review_id"],
                ["platform_story_reviews.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    if not index_exists("guidance_signal_story_idx"):
        op.create_index(
            "guidance_signal_story_idx",
            "platform_guidance_compliance_signals",
            ["story_id"],
        )
    if not index_exists("guidance_signal_version_idx"):
        op.create_index(
            "guidance_signal_version_idx",
            "platform_guidance_compliance_signals",
            ["guidance_version"],
        )
    if not index_exists("guidance_signal_review_idx"):
        op.create_index(
            "guidance_signal_review_idx",
            "platform_guidance_compliance_signals",
            ["review_id"],
        )
    if not index_exists("guidance_signal_created_at_idx"):
        op.create_index(
            "guidance_signal_created_at_idx",
            "platform_guidance_compliance_signals",
            ["created_at"],
        )

    if not column_exists("platform_dweller_actions", "escalation_status"):
        op.add_column(
            "platform_dweller_actions",
            sa.Column(
                "escalation_status",
                sa.String(length=50),
                nullable=False,
                server_default=sa.text("'eligible'"),
            ),
        )
    if not column_exists("platform_dweller_actions", "nominated_at"):
        op.add_column(
            "platform_dweller_actions",
            sa.Column("nominated_at", sa.DateTime(timezone=True), nullable=True),
        )
    if not column_exists("platform_dweller_actions", "nomination_count"):
        op.add_column(
            "platform_dweller_actions",
            sa.Column(
                "nomination_count",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )
    if not index_exists("action_escalation_status_idx"):
        op.create_index(
            "action_escalation_status_idx",
            "platform_dweller_actions",
            ["escalation_status"],
        )


def downgrade() -> None:
    if index_exists("action_escalation_status_idx"):
        op.drop_index("action_escalation_status_idx", table_name="platform_dweller_actions")

    if column_exists("platform_dweller_actions", "nomination_count"):
        op.drop_column("platform_dweller_actions", "nomination_count")
    if column_exists("platform_dweller_actions", "nominated_at"):
        op.drop_column("platform_dweller_actions", "nominated_at")
    if column_exists("platform_dweller_actions", "escalation_status"):
        op.drop_column("platform_dweller_actions", "escalation_status")

    if index_exists("guidance_signal_created_at_idx"):
        op.drop_index(
            "guidance_signal_created_at_idx",
            table_name="platform_guidance_compliance_signals",
        )
    if index_exists("guidance_signal_review_idx"):
        op.drop_index(
            "guidance_signal_review_idx",
            table_name="platform_guidance_compliance_signals",
        )
    if index_exists("guidance_signal_version_idx"):
        op.drop_index(
            "guidance_signal_version_idx",
            table_name="platform_guidance_compliance_signals",
        )
    if index_exists("guidance_signal_story_idx"):
        op.drop_index(
            "guidance_signal_story_idx",
            table_name="platform_guidance_compliance_signals",
        )
    if table_exists("platform_guidance_compliance_signals"):
        op.drop_table("platform_guidance_compliance_signals")
