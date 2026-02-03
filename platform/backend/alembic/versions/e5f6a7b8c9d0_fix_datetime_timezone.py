"""fix_datetime_timezone

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-02-03 06:00:00.000000

Convert datetime columns to timezone-aware (TIMESTAMP WITH TIME ZONE)
to match the Python code that now uses timezone-aware datetimes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
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
    """Convert timestamp columns to timestamp with time zone."""

    # List of (table, column) pairs that need timezone conversion
    columns_to_convert = [
        # platform_users
        ('platform_users', 'created_at'),
        ('platform_users', 'last_active_at'),
        # platform_api_keys
        ('platform_api_keys', 'created_at'),
        ('platform_api_keys', 'last_used_at'),
        ('platform_api_keys', 'expires_at'),
        # platform_worlds
        ('platform_worlds', 'created_at'),
        ('platform_worlds', 'updated_at'),
        # platform_dwellers
        ('platform_dwellers', 'created_at'),
        ('platform_dwellers', 'updated_at'),
        ('platform_dwellers', 'last_action_at'),
        # platform_dweller_actions
        ('platform_dweller_actions', 'created_at'),
        # platform_proposals
        ('platform_proposals', 'created_at'),
        ('platform_proposals', 'updated_at'),
        # platform_validations
        ('platform_validations', 'created_at'),
        # platform_aspects
        ('platform_aspects', 'created_at'),
        ('platform_aspects', 'updated_at'),
        # platform_aspect_validations
        ('platform_aspect_validations', 'created_at'),
        # platform_comments
        ('platform_comments', 'created_at'),
        ('platform_comments', 'updated_at'),
        # platform_social_interactions
        ('platform_social_interactions', 'created_at'),
    ]

    for table, column in columns_to_convert:
        if column_exists(table, column):
            # PostgreSQL allows this conversion directly
            op.execute(f'''
                ALTER TABLE {table}
                ALTER COLUMN {column} TYPE TIMESTAMP WITH TIME ZONE
                USING {column} AT TIME ZONE 'UTC'
            ''')


def downgrade() -> None:
    """Convert back to timestamp without time zone."""

    columns_to_convert = [
        ('platform_users', 'created_at'),
        ('platform_users', 'last_active_at'),
        ('platform_api_keys', 'created_at'),
        ('platform_api_keys', 'last_used_at'),
        ('platform_api_keys', 'expires_at'),
        ('platform_worlds', 'created_at'),
        ('platform_worlds', 'updated_at'),
        ('platform_dwellers', 'created_at'),
        ('platform_dwellers', 'updated_at'),
        ('platform_dwellers', 'last_action_at'),
        ('platform_dweller_actions', 'created_at'),
        ('platform_proposals', 'created_at'),
        ('platform_proposals', 'updated_at'),
        ('platform_validations', 'created_at'),
        ('platform_aspects', 'created_at'),
        ('platform_aspects', 'updated_at'),
        ('platform_aspect_validations', 'created_at'),
        ('platform_comments', 'created_at'),
        ('platform_comments', 'updated_at'),
        ('platform_social_interactions', 'created_at'),
    ]

    for table, column in columns_to_convert:
        if column_exists(table, column):
            op.execute(f'''
                ALTER TABLE {table}
                ALTER COLUMN {column} TYPE TIMESTAMP WITHOUT TIME ZONE
            ''')
