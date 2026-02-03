"""fix_all_missing_dweller_columns

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-02-03 05:45:00.000000

Fix for ALL dweller and world columns that were supposed to be added
by a1b2c3d4e5f6 but the DDL failed after marking migration as complete.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
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
    """Add all columns that may be missing from a1b2c3d4e5f6."""

    # === platform_worlds columns ===
    if not column_exists('platform_worlds', 'canon_summary'):
        op.add_column('platform_worlds', sa.Column('canon_summary', sa.Text(), nullable=True))

    if not column_exists('platform_worlds', 'regions'):
        op.add_column('platform_worlds', sa.Column('regions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'))

    if not column_exists('platform_worlds', 'scientific_basis'):
        op.add_column('platform_worlds', sa.Column('scientific_basis', sa.Text(), nullable=True))

    # === platform_dwellers columns ===
    if not column_exists('platform_dwellers', 'created_by'):
        op.add_column('platform_dwellers', sa.Column('created_by', sa.UUID(), nullable=True))

    if not column_exists('platform_dwellers', 'inhabited_by'):
        op.add_column('platform_dwellers', sa.Column('inhabited_by', sa.UUID(), nullable=True))

    if not column_exists('platform_dwellers', 'origin_region'):
        op.add_column('platform_dwellers', sa.Column('origin_region', sa.String(100), nullable=False, server_default='Unknown'))

    if not column_exists('platform_dwellers', 'generation'):
        op.add_column('platform_dwellers', sa.Column('generation', sa.String(50), nullable=False, server_default='Founding'))

    if not column_exists('platform_dwellers', 'name_context'):
        op.add_column('platform_dwellers', sa.Column('name_context', sa.Text(), nullable=False, server_default='Contextual name'))

    if not column_exists('platform_dwellers', 'cultural_identity'):
        op.add_column('platform_dwellers', sa.Column('cultural_identity', sa.Text(), nullable=False, server_default='Local culture'))

    if not column_exists('platform_dwellers', 'age'):
        op.add_column('platform_dwellers', sa.Column('age', sa.Integer(), nullable=False, server_default='30'))

    if not column_exists('platform_dwellers', 'personality'):
        op.add_column('platform_dwellers', sa.Column('personality', sa.Text(), nullable=False, server_default='Curious and thoughtful'))

    if not column_exists('platform_dwellers', 'background'):
        op.add_column('platform_dwellers', sa.Column('background', sa.Text(), nullable=False, server_default='A citizen of this world'))

    if not column_exists('platform_dwellers', 'core_memories'):
        op.add_column('platform_dwellers', sa.Column('core_memories', postgresql.JSONB(astext_type=sa.Text()), server_default='[]'))

    if not column_exists('platform_dwellers', 'personality_blocks'):
        op.add_column('platform_dwellers', sa.Column('personality_blocks', postgresql.JSONB(astext_type=sa.Text()), server_default='{}'))

    if not column_exists('platform_dwellers', 'episodic_memories'):
        op.add_column('platform_dwellers', sa.Column('episodic_memories', postgresql.JSONB(astext_type=sa.Text()), server_default='[]'))

    if not column_exists('platform_dwellers', 'memory_summaries'):
        op.add_column('platform_dwellers', sa.Column('memory_summaries', postgresql.JSONB(astext_type=sa.Text()), server_default='[]'))

    if not column_exists('platform_dwellers', 'relationship_memories'):
        op.add_column('platform_dwellers', sa.Column('relationship_memories', postgresql.JSONB(astext_type=sa.Text()), server_default='{}'))

    if not column_exists('platform_dwellers', 'current_situation'):
        op.add_column('platform_dwellers', sa.Column('current_situation', sa.Text(), server_default=''))

    if not column_exists('platform_dwellers', 'working_memory_size'):
        op.add_column('platform_dwellers', sa.Column('working_memory_size', sa.Integer(), server_default='50'))

    if not column_exists('platform_dwellers', 'current_region'):
        op.add_column('platform_dwellers', sa.Column('current_region', sa.String(100), nullable=True))

    if not column_exists('platform_dwellers', 'specific_location'):
        op.add_column('platform_dwellers', sa.Column('specific_location', sa.Text(), nullable=True))

    if not column_exists('platform_dwellers', 'is_available'):
        op.add_column('platform_dwellers', sa.Column('is_available', sa.Boolean(), server_default='true'))


def downgrade() -> None:
    """Remove all columns added by this migration."""
    # Dweller columns
    dweller_cols = [
        'is_available', 'specific_location', 'current_region', 'working_memory_size',
        'current_situation', 'relationship_memories', 'memory_summaries', 'episodic_memories',
        'personality_blocks', 'core_memories', 'background', 'personality', 'age',
        'cultural_identity', 'name_context', 'generation', 'origin_region',
        'inhabited_by', 'created_by'
    ]
    for col in dweller_cols:
        if column_exists('platform_dwellers', col):
            op.drop_column('platform_dwellers', col)

    # World columns
    if column_exists('platform_worlds', 'scientific_basis'):
        op.drop_column('platform_worlds', 'scientific_basis')
    if column_exists('platform_worlds', 'regions'):
        op.drop_column('platform_worlds', 'regions')
    if column_exists('platform_worlds', 'canon_summary'):
        op.drop_column('platform_worlds', 'canon_summary')
