"""final_schema_fix

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-02-03 06:10:00.000000

Final comprehensive fix to ensure all columns exist and have correct types.
Previous migrations were marked as applied but DDL failed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :column"
    ), {"table": table_name, "column": column_name})
    return result.fetchone() is not None


def upgrade() -> None:
    # === platform_worlds ===
    if not column_exists('platform_worlds', 'canon_summary'):
        op.add_column('platform_worlds', sa.Column('canon_summary', sa.Text(), nullable=True))
    if not column_exists('platform_worlds', 'regions'):
        op.add_column('platform_worlds', sa.Column('regions', postgresql.JSONB(), server_default='[]'))
    if not column_exists('platform_worlds', 'scientific_basis'):
        op.add_column('platform_worlds', sa.Column('scientific_basis', sa.Text(), nullable=True))
    if not column_exists('platform_worlds', 'comment_count'):
        op.add_column('platform_worlds', sa.Column('comment_count', sa.Integer(), server_default='0'))
    if not column_exists('platform_worlds', 'reaction_counts'):
        op.add_column('platform_worlds', sa.Column('reaction_counts', postgresql.JSONB(),
            server_default='{"fire": 0, "mind": 0, "heart": 0, "thinking": 0}'))

    # === platform_dwellers - ALL columns ===
    if not column_exists('platform_dwellers', 'name'):
        op.add_column('platform_dwellers', sa.Column('name', sa.String(100), nullable=False, server_default='Unknown'))
    if not column_exists('platform_dwellers', 'role'):
        op.add_column('platform_dwellers', sa.Column('role', sa.String(255), nullable=False, server_default='Citizen'))
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
        op.add_column('platform_dwellers', sa.Column('personality', sa.Text(), nullable=False, server_default='Curious'))
    if not column_exists('platform_dwellers', 'background'):
        op.add_column('platform_dwellers', sa.Column('background', sa.Text(), nullable=False, server_default='A citizen'))
    if not column_exists('platform_dwellers', 'core_memories'):
        op.add_column('platform_dwellers', sa.Column('core_memories', postgresql.JSONB(), server_default='[]'))
    if not column_exists('platform_dwellers', 'personality_blocks'):
        op.add_column('platform_dwellers', sa.Column('personality_blocks', postgresql.JSONB(), server_default='{}'))
    if not column_exists('platform_dwellers', 'episodic_memories'):
        op.add_column('platform_dwellers', sa.Column('episodic_memories', postgresql.JSONB(), server_default='[]'))
    if not column_exists('platform_dwellers', 'memory_summaries'):
        op.add_column('platform_dwellers', sa.Column('memory_summaries', postgresql.JSONB(), server_default='[]'))
    if not column_exists('platform_dwellers', 'relationship_memories'):
        op.add_column('platform_dwellers', sa.Column('relationship_memories', postgresql.JSONB(), server_default='{}'))
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
    if not column_exists('platform_dwellers', 'is_active'):
        op.add_column('platform_dwellers', sa.Column('is_active', sa.Boolean(), server_default='true'))
    if not column_exists('platform_dwellers', 'last_action_at'):
        op.add_column('platform_dwellers', sa.Column('last_action_at', sa.DateTime(timezone=True), nullable=True))

    # === platform_aspects ===
    if not column_exists('platform_aspects', 'inspired_by_actions'):
        op.add_column('platform_aspects', sa.Column('inspired_by_actions', postgresql.JSONB(), server_default='[]'))

    # === platform_dweller_actions ===
    if not column_exists('platform_dweller_actions', 'importance'):
        op.add_column('platform_dweller_actions', sa.Column('importance', sa.Float(), server_default='0.5'))
    if not column_exists('platform_dweller_actions', 'escalation_eligible'):
        op.add_column('platform_dweller_actions', sa.Column('escalation_eligible', sa.Boolean(), server_default='false'))
    if not column_exists('platform_dweller_actions', 'importance_confirmed_by'):
        op.add_column('platform_dweller_actions', sa.Column('importance_confirmed_by', sa.UUID(), nullable=True))
    if not column_exists('platform_dweller_actions', 'importance_confirmed_at'):
        op.add_column('platform_dweller_actions', sa.Column('importance_confirmed_at', sa.DateTime(timezone=True), nullable=True))
    if not column_exists('platform_dweller_actions', 'importance_confirmation_rationale'):
        op.add_column('platform_dweller_actions', sa.Column('importance_confirmation_rationale', sa.Text(), nullable=True))

    # === platform_users ===
    if not column_exists('platform_users', 'model_id'):
        op.add_column('platform_users', sa.Column('model_id', sa.String(100), nullable=True))
    if not column_exists('platform_users', 'platform_notifications'):
        op.add_column('platform_users', sa.Column('platform_notifications', sa.Boolean(), server_default='true'))

    # === platform_comments ===
    if not column_exists('platform_comments', 'reaction'):
        op.add_column('platform_comments', sa.Column('reaction', sa.String(20), nullable=True))


def downgrade() -> None:
    pass  # Not implementing downgrade for safety
