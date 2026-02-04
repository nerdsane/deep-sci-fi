"""add_timeline_entry_fields

Revision ID: j0e1f2g3h4i5
Revises: i9d0e1f2g3h4
Create Date: 2026-02-03 12:00:00.000000

Add proposed_timeline_entry to platform_aspects and approved_timeline_entry
to platform_aspect_validations for causal chain integration when event
aspects are approved.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'j0e1f2g3h4i5'
down_revision: Union[str, None] = 'i9d0e1f2g3h4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = :table"
    ), {"table": table_name})
    return result.fetchone() is not None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :column"
    ), {"table": table_name, "column": column_name})
    return result.fetchone() is not None


def upgrade() -> None:
    # Add proposed_timeline_entry to platform_aspects
    # Only add if table exists and column doesn't exist yet
    if table_exists('platform_aspects') and not column_exists('platform_aspects', 'proposed_timeline_entry'):
        op.add_column('platform_aspects', sa.Column(
            'proposed_timeline_entry',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True
        ))

    # Add approved_timeline_entry to platform_aspect_validations
    if table_exists('platform_aspect_validations') and not column_exists('platform_aspect_validations', 'approved_timeline_entry'):
        op.add_column('platform_aspect_validations', sa.Column(
            'approved_timeline_entry',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True
        ))


def downgrade() -> None:
    if column_exists('platform_aspect_validations', 'approved_timeline_entry'):
        op.drop_column('platform_aspect_validations', 'approved_timeline_entry')

    if column_exists('platform_aspects', 'proposed_timeline_entry'):
        op.drop_column('platform_aspects', 'proposed_timeline_entry')
