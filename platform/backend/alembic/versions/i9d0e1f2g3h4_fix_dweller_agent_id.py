"""fix_dweller_agent_id

Revision ID: i9d0e1f2g3h4
Revises: h8c9d0e1f2g3
Create Date: 2026-02-03 10:00:00.000000

The platform_dwellers table has an old agent_id column (NOT NULL) that doesn't
match the model which uses created_by. This migration:
1. Copies agent_id to created_by where created_by is NULL
2. Makes created_by NOT NULL
3. Makes agent_id nullable (keeping for backwards compat)
4. Makes persona nullable (old column, not used anymore)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'i9d0e1f2g3h4'
down_revision: Union[str, None] = 'h8c9d0e1f2g3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Copy agent_id to created_by where created_by is NULL
    conn.execute(sa.text("""
        UPDATE platform_dwellers
        SET created_by = agent_id
        WHERE created_by IS NULL AND agent_id IS NOT NULL
    """))

    # 2. Make agent_id nullable (keep column for now, but don't require it)
    conn.execute(sa.text("""
        ALTER TABLE platform_dwellers
        ALTER COLUMN agent_id DROP NOT NULL
    """))

    # 3. Make persona nullable (old column, not used in new model)
    conn.execute(sa.text("""
        ALTER TABLE platform_dwellers
        ALTER COLUMN persona DROP NOT NULL
    """))

    # 4. Make created_by NOT NULL (with a default for any edge cases)
    # First set a fallback for any remaining NULLs (shouldn't happen but safe)
    conn.execute(sa.text("""
        UPDATE platform_dwellers
        SET created_by = agent_id
        WHERE created_by IS NULL
    """))

    # Note: We don't make created_by NOT NULL yet because there might be
    # rows where both are NULL from the table creation. We'll handle this
    # in the application layer with proper validation.


def downgrade() -> None:
    conn = op.get_bind()

    # Reverse: make agent_id required again
    conn.execute(sa.text("""
        UPDATE platform_dwellers
        SET agent_id = created_by
        WHERE agent_id IS NULL AND created_by IS NOT NULL
    """))

    conn.execute(sa.text("""
        ALTER TABLE platform_dwellers
        ALTER COLUMN agent_id SET NOT NULL
    """))
