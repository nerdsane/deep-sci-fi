"""add idempotency keys table

Revision ID: ca3fe29ae6ed
Revises: 0015
Create Date: 2026-02-14 19:00:10.070343

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca3fe29ae6ed'
down_revision: Union[str, None] = '0015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if table already exists
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'platform_idempotency_keys'"
    ))
    if result.fetchone() is not None:
        return

    op.create_table(
        'platform_idempotency_keys',
        sa.Column('key', sa.String(255), primary_key=True),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('endpoint', sa.String(255), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='in_progress'),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['platform_users.id'], ondelete='CASCADE'),
    )

    op.create_index('idx_idempotency_keys_created', 'platform_idempotency_keys', ['created_at'])
    op.create_index('idx_idempotency_keys_user', 'platform_idempotency_keys', ['user_id'])


def downgrade() -> None:
    op.drop_index('idx_idempotency_keys_user', table_name='platform_idempotency_keys')
    op.drop_index('idx_idempotency_keys_created', table_name='platform_idempotency_keys')
    op.drop_table('platform_idempotency_keys')
