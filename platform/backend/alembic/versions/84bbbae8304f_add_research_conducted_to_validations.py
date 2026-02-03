"""add research_conducted to validations

Revision ID: 84bbbae8304f
Revises: j0e1f2g3h4i5
Create Date: 2026-02-03 12:57:33.830786

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '84bbbae8304f'
down_revision: Union[str, None] = 'j0e1f2g3h4i5'
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
    # Add research_conducted column to platform_validations
    if not column_exists('platform_validations', 'research_conducted'):
        op.add_column(
            'platform_validations',
            sa.Column('research_conducted', sa.Text(), nullable=True)
        )


def downgrade() -> None:
    # Remove research_conducted column
    if column_exists('platform_validations', 'research_conducted'):
        op.drop_column('platform_validations', 'research_conducted')
