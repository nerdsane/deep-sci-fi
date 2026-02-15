"""Widen dweller string columns to prevent 500s on descriptive text.

generation: VARCHAR(50) → TEXT (agents write descriptive generation context)
current_region: VARCHAR(100) → VARCHAR(255) (region names can be long)
role: VARCHAR(255) → TEXT (agents write descriptive roles)

Revision ID: 0017
Revises: ca3fe29ae6ed
Create Date: 2026-02-15
"""

from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "ca3fe29ae6ed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # generation: VARCHAR(50) → TEXT — this was the main cause of 500s
    op.alter_column(
        "platform_dwellers",
        "generation",
        type_=sa.Text(),
        existing_type=sa.String(50),
        existing_nullable=False,
    )
    # current_region: VARCHAR(100) → VARCHAR(255) — match origin_region
    op.alter_column(
        "platform_dwellers",
        "current_region",
        type_=sa.String(255),
        existing_type=sa.String(100),
        existing_nullable=True,
    )
    # role: VARCHAR(255) → TEXT — some agents write longer role descriptions
    op.alter_column(
        "platform_dwellers",
        "role",
        type_=sa.Text(),
        existing_type=sa.String(255),
        existing_nullable=False,
    )
    # Same changes for dweller_proposals table
    op.alter_column(
        "platform_dweller_proposals",
        "generation",
        type_=sa.Text(),
        existing_type=sa.String(50),
        existing_nullable=False,
    )
    op.alter_column(
        "platform_dweller_proposals",
        "role",
        type_=sa.Text(),
        existing_type=sa.String(255),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "platform_dwellers",
        "generation",
        type_=sa.String(50),
        existing_type=sa.Text(),
        existing_nullable=False,
    )
    op.alter_column(
        "platform_dwellers",
        "current_region",
        type_=sa.String(100),
        existing_type=sa.String(255),
        existing_nullable=True,
    )
    op.alter_column(
        "platform_dwellers",
        "role",
        type_=sa.String(255),
        existing_type=sa.Text(),
        existing_nullable=False,
    )
    op.alter_column(
        "platform_dweller_proposals",
        "generation",
        type_=sa.String(50),
        existing_type=sa.Text(),
        existing_nullable=False,
    )
    op.alter_column(
        "platform_dweller_proposals",
        "role",
        type_=sa.String(255),
        existing_type=sa.Text(),
        existing_nullable=False,
    )
