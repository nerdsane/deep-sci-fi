"""Increase origin_region column size to prevent truncation.

Fixes StringDataRightTruncationError when agents create dwellers with
longer region names (observed in Logfire production logs).

Revision ID: 0006_increase_origin_region_size
Revises: 0005_comprehensive_column_sync
Create Date: 2026-02-05
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Increase origin_region from VARCHAR(100) to VARCHAR(255) in both tables."""
    # platform_dwellers
    op.alter_column(
        "platform_dwellers",
        "origin_region",
        existing_type=sa.VARCHAR(100),
        type_=sa.VARCHAR(255),
        existing_nullable=False,
    )

    # platform_dweller_proposals
    op.alter_column(
        "platform_dweller_proposals",
        "origin_region",
        existing_type=sa.VARCHAR(100),
        type_=sa.VARCHAR(255),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Revert to VARCHAR(100) - may truncate data."""
    op.alter_column(
        "platform_dwellers",
        "origin_region",
        existing_type=sa.VARCHAR(255),
        type_=sa.VARCHAR(100),
        existing_nullable=False,
    )

    op.alter_column(
        "platform_dweller_proposals",
        "origin_region",
        existing_type=sa.VARCHAR(255),
        type_=sa.VARCHAR(100),
        existing_nullable=False,
    )
