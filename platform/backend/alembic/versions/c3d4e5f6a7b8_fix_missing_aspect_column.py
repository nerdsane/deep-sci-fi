"""fix_missing_aspect_column

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-02-03 05:30:00.000000

Fix for inspired_by_actions column that was supposed to be added
by a1b2c3d4e5f6 but the DDL failed after marking migration as complete.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
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
    """Add inspired_by_actions if it doesn't exist."""
    if not column_exists('platform_aspects', 'inspired_by_actions'):
        op.add_column('platform_aspects', sa.Column('inspired_by_actions',
            postgresql.JSONB(astext_type=sa.Text()), server_default='[]'))


def downgrade() -> None:
    """Remove inspired_by_actions."""
    if column_exists('platform_aspects', 'inspired_by_actions'):
        op.drop_column('platform_aspects', 'inspired_by_actions')
