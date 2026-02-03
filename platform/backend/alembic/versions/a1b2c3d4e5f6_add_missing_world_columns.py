"""add_missing_world_columns

Revision ID: a1b2c3d4e5f6
Revises: 93bbfb2c4512
Create Date: 2026-02-03 03:59:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '93bbfb2c4512'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :column"
    ), {"table": table_name, "column": column_name})
    return result.fetchone() is not None


def upgrade() -> None:
    """Add columns that may be missing from platform_worlds table."""
    if not column_exists('platform_worlds', 'canon_summary'):
        op.add_column('platform_worlds', sa.Column('canon_summary', sa.Text(), nullable=True))

    if not column_exists('platform_worlds', 'regions'):
        op.add_column('platform_worlds', sa.Column('regions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'))

    if not column_exists('platform_worlds', 'scientific_basis'):
        op.add_column('platform_worlds', sa.Column('scientific_basis', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove columns - note: this will lose data."""
    if column_exists('platform_worlds', 'scientific_basis'):
        op.drop_column('platform_worlds', 'scientific_basis')
    if column_exists('platform_worlds', 'regions'):
        op.drop_column('platform_worlds', 'regions')
    if column_exists('platform_worlds', 'canon_summary'):
        op.drop_column('platform_worlds', 'canon_summary')
