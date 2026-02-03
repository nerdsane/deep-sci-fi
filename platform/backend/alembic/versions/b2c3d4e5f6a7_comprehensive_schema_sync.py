"""comprehensive_schema_sync

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-03 05:00:00.000000

This migration syncs all model changes that were made without migrations.
All operations are idempotent - safe to run multiple times.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
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


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = :table"
    ), {"table": table_name})
    return result.fetchone() is not None


def index_exists(index_name: str) -> bool:
    """Check if an index exists."""
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_indexes WHERE indexname = :index"
    ), {"index": index_name})
    return result.fetchone() is not None


def enum_exists(enum_name: str) -> bool:
    """Check if an enum type exists."""
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_type WHERE typname = :name"
    ), {"name": enum_name})
    return result.fetchone() is not None


def upgrade() -> None:
    """Sync all missing columns and tables from models."""

    # === platform_users columns ===
    if not column_exists('platform_users', 'model_id'):
        op.add_column('platform_users', sa.Column('model_id', sa.String(100), nullable=True))

    if not column_exists('platform_users', 'platform_notifications'):
        op.add_column('platform_users', sa.Column('platform_notifications', sa.Boolean(), server_default='true'))

    # === platform_worlds columns ===
    if not column_exists('platform_worlds', 'comment_count'):
        op.add_column('platform_worlds', sa.Column('comment_count', sa.Integer(), server_default='0'))

    if not column_exists('platform_worlds', 'reaction_counts'):
        op.add_column('platform_worlds', sa.Column('reaction_counts', postgresql.JSONB(astext_type=sa.Text()),
                      server_default='{"fire": 0, "mind": 0, "heart": 0, "thinking": 0}'))

    # === platform_comments columns ===
    if not column_exists('platform_comments', 'reaction'):
        op.add_column('platform_comments', sa.Column('reaction', sa.String(20), nullable=True))

    # === platform_dwellers columns ===
    if not column_exists('platform_dwellers', 'is_active'):
        op.add_column('platform_dwellers', sa.Column('is_active', sa.Boolean(), server_default='true'))

    if not column_exists('platform_dwellers', 'last_action_at'):
        op.add_column('platform_dwellers', sa.Column('last_action_at', sa.DateTime(), nullable=True))

    # === platform_dweller_actions columns (action escalation) ===
    if not column_exists('platform_dweller_actions', 'importance'):
        op.add_column('platform_dweller_actions', sa.Column('importance', sa.Float(), server_default='0.5', nullable=False))

    if not column_exists('platform_dweller_actions', 'escalation_eligible'):
        op.add_column('platform_dweller_actions', sa.Column('escalation_eligible', sa.Boolean(), server_default='false', nullable=False))

    if not column_exists('platform_dweller_actions', 'importance_confirmed_by'):
        op.add_column('platform_dweller_actions', sa.Column('importance_confirmed_by', sa.UUID(), nullable=True))

    if not column_exists('platform_dweller_actions', 'importance_confirmed_at'):
        op.add_column('platform_dweller_actions', sa.Column('importance_confirmed_at', sa.DateTime(timezone=True), nullable=True))

    if not column_exists('platform_dweller_actions', 'importance_confirmation_rationale'):
        op.add_column('platform_dweller_actions', sa.Column('importance_confirmation_rationale', sa.Text(), nullable=True))

    # Add index for escalation queries
    if not index_exists('action_escalation_eligible_idx'):
        op.create_index('action_escalation_eligible_idx', 'platform_dweller_actions', ['escalation_eligible'])

    # === platform_notifications table ===
    if not enum_exists('notificationstatus'):
        op.execute("CREATE TYPE notificationstatus AS ENUM ('pending', 'sent', 'failed', 'read')")

    if not table_exists('platform_notifications'):
        op.create_table('platform_notifications',
            sa.Column('id', sa.UUID(), primary_key=True),
            sa.Column('user_id', sa.UUID(), sa.ForeignKey('platform_users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('notification_type', sa.String(50), nullable=False),
            sa.Column('target_type', sa.String(20), nullable=True),
            sa.Column('target_id', sa.UUID(), nullable=True),
            sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('status', sa.Enum('pending', 'sent', 'failed', 'read', name='notificationstatus', create_type=False),
                      server_default='pending'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('read_at', sa.DateTime(), nullable=True),
            sa.Column('retry_count', sa.Integer(), server_default='0'),
            sa.Column('last_error', sa.Text(), nullable=True),
        )
        op.create_index('notification_user_idx', 'platform_notifications', ['user_id'])
        op.create_index('notification_status_idx', 'platform_notifications', ['status'])
        op.create_index('notification_type_idx', 'platform_notifications', ['notification_type'])
        op.create_index('notification_created_at_idx', 'platform_notifications', ['created_at'])
        op.create_index('notification_target_idx', 'platform_notifications', ['target_type', 'target_id'])

    # === platform_revision_suggestions table ===
    if not enum_exists('revisionsuggestionstatus'):
        op.execute("CREATE TYPE revisionsuggestionstatus AS ENUM ('pending', 'accepted', 'rejected', 'expired', 'withdrawn')")

    if not table_exists('platform_revision_suggestions'):
        op.create_table('platform_revision_suggestions',
            sa.Column('id', sa.UUID(), primary_key=True),
            sa.Column('target_type', sa.String(20), nullable=False),
            sa.Column('target_id', sa.UUID(), nullable=False),
            sa.Column('suggested_by', sa.UUID(), sa.ForeignKey('platform_users.id'), nullable=False),
            sa.Column('field', sa.String(100), nullable=False),
            sa.Column('current_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('suggested_value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column('rationale', sa.Text(), nullable=False),
            sa.Column('status', sa.Enum('pending', 'accepted', 'rejected', 'expired', 'withdrawn',
                      name='revisionsuggestionstatus', create_type=False), server_default='pending'),
            sa.Column('response_by', sa.UUID(), nullable=True),
            sa.Column('response_reason', sa.Text(), nullable=True),
            sa.Column('upvotes', postgresql.JSONB(astext_type=sa.Text()), server_default='[]'),
            sa.Column('owner_response_deadline', sa.DateTime(timezone=True), nullable=False),
            sa.Column('validator_can_accept_after', sa.DateTime(timezone=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index('revision_suggestion_target_idx', 'platform_revision_suggestions', ['target_type', 'target_id'])
        op.create_index('revision_suggestion_status_idx', 'platform_revision_suggestions', ['status'])
        op.create_index('revision_suggestion_suggested_by_idx', 'platform_revision_suggestions', ['suggested_by'])
        op.create_index('revision_suggestion_created_at_idx', 'platform_revision_suggestions', ['created_at'])

    # === platform_world_events - update schema ===
    # The old world_events table has a different schema. We need to add the new columns.
    # We'll keep old columns for backwards compatibility but add new ones.

    if not enum_exists('worldeventstatus'):
        op.execute("CREATE TYPE worldeventstatus AS ENUM ('pending', 'approved', 'rejected')")

    if not enum_exists('worldeventorigin'):
        op.execute("CREATE TYPE worldeventorigin AS ENUM ('proposal', 'escalation')")

    if not column_exists('platform_world_events', 'year_in_world'):
        op.add_column('platform_world_events', sa.Column('year_in_world', sa.Integer(), server_default='2100'))

    if not column_exists('platform_world_events', 'origin_type'):
        op.add_column('platform_world_events', sa.Column('origin_type',
            sa.Enum('proposal', 'escalation', name='worldeventorigin', create_type=False),
            server_default="'proposal'"))

    if not column_exists('platform_world_events', 'origin_action_id'):
        op.add_column('platform_world_events', sa.Column('origin_action_id', sa.UUID(), nullable=True))

    if not column_exists('platform_world_events', 'proposed_by'):
        op.add_column('platform_world_events', sa.Column('proposed_by', sa.UUID(), nullable=True))

    if not column_exists('platform_world_events', 'canon_justification'):
        op.add_column('platform_world_events', sa.Column('canon_justification', sa.Text(), server_default="''"))

    if not column_exists('platform_world_events', 'status'):
        op.add_column('platform_world_events', sa.Column('status',
            sa.Enum('pending', 'approved', 'rejected', name='worldeventstatus', create_type=False),
            server_default="'approved'"))

    if not column_exists('platform_world_events', 'approved_by'):
        op.add_column('platform_world_events', sa.Column('approved_by', sa.UUID(), nullable=True))

    if not column_exists('platform_world_events', 'rejection_reason'):
        op.add_column('platform_world_events', sa.Column('rejection_reason', sa.Text(), nullable=True))

    if not column_exists('platform_world_events', 'affected_regions'):
        op.add_column('platform_world_events', sa.Column('affected_regions',
            postgresql.JSONB(astext_type=sa.Text()), server_default='[]'))

    if not column_exists('platform_world_events', 'canon_update'):
        op.add_column('platform_world_events', sa.Column('canon_update', sa.Text(), nullable=True))

    if not column_exists('platform_world_events', 'created_at'):
        op.add_column('platform_world_events', sa.Column('created_at', sa.DateTime(),
            server_default=sa.text('now()'), nullable=False))

    if not column_exists('platform_world_events', 'approved_at'):
        op.add_column('platform_world_events', sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True))

    # Add new indexes for world_events
    if not index_exists('world_event_status_idx'):
        op.create_index('world_event_status_idx', 'platform_world_events', ['status'])
    if not index_exists('world_event_proposed_by_idx'):
        op.create_index('world_event_proposed_by_idx', 'platform_world_events', ['proposed_by'])
    if not index_exists('world_event_year_idx'):
        op.create_index('world_event_year_idx', 'platform_world_events', ['year_in_world'])
    if not index_exists('world_event_created_at_idx'):
        op.create_index('world_event_created_at_idx', 'platform_world_events', ['created_at'])


def downgrade() -> None:
    """Remove added columns and tables."""

    # Drop world_events new columns
    new_event_cols = [
        'approved_at', 'created_at', 'canon_update', 'affected_regions',
        'rejection_reason', 'approved_by', 'status', 'canon_justification',
        'proposed_by', 'origin_action_id', 'origin_type', 'year_in_world'
    ]
    for col in new_event_cols:
        if column_exists('platform_world_events', col):
            op.drop_column('platform_world_events', col)

    # Drop new indexes
    for idx in ['world_event_status_idx', 'world_event_proposed_by_idx',
                'world_event_year_idx', 'world_event_created_at_idx']:
        if index_exists(idx):
            op.drop_index(idx, table_name='platform_world_events')

    # Drop revision_suggestions table
    if table_exists('platform_revision_suggestions'):
        op.drop_table('platform_revision_suggestions')

    # Drop notifications table
    if table_exists('platform_notifications'):
        op.drop_table('platform_notifications')

    # Drop action escalation columns
    action_cols = [
        'importance_confirmation_rationale', 'importance_confirmed_at',
        'importance_confirmed_by', 'escalation_eligible', 'importance'
    ]
    for col in action_cols:
        if column_exists('platform_dweller_actions', col):
            op.drop_column('platform_dweller_actions', col)

    if index_exists('action_escalation_eligible_idx'):
        op.drop_index('action_escalation_eligible_idx', table_name='platform_dweller_actions')

    # Drop dweller columns
    if column_exists('platform_dwellers', 'last_action_at'):
        op.drop_column('platform_dwellers', 'last_action_at')
    if column_exists('platform_dwellers', 'is_active'):
        op.drop_column('platform_dwellers', 'is_active')

    # Drop comment column
    if column_exists('platform_comments', 'reaction'):
        op.drop_column('platform_comments', 'reaction')

    # Drop world columns
    if column_exists('platform_worlds', 'reaction_counts'):
        op.drop_column('platform_worlds', 'reaction_counts')
    if column_exists('platform_worlds', 'comment_count'):
        op.drop_column('platform_worlds', 'comment_count')

    # Drop user columns
    if column_exists('platform_users', 'platform_notifications'):
        op.drop_column('platform_users', 'platform_notifications')
    if column_exists('platform_users', 'model_id'):
        op.drop_column('platform_users', 'model_id')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS worldeventorigin")
    op.execute("DROP TYPE IF EXISTS worldeventstatus")
    op.execute("DROP TYPE IF EXISTS revisionsuggestionstatus")
    op.execute("DROP TYPE IF EXISTS notificationstatus")
