"""add callback_token to users

Revision ID: 86dddaf0526h
Revises: 85cccaf9415g
Create Date: 2026-02-03 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '86dddaf0526h'
down_revision: Union[str, None] = '85cccaf9415g'
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
    # Add callback_token column to platform_users
    if not column_exists('platform_users', 'callback_token'):
        op.add_column(
            'platform_users',
            sa.Column('callback_token', sa.String(256), nullable=True)
        )


def downgrade() -> None:
    # Remove callback_token column
    if column_exists('platform_users', 'callback_token'):
        op.drop_column('platform_users', 'callback_token')
