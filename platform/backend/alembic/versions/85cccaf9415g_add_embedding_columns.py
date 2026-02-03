"""add embedding columns for similarity search

Revision ID: 85cccaf9415g
Revises: 84bbbae8304f
Create Date: 2026-02-03 13:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '85cccaf9415g'
down_revision: Union[str, None] = '84bbbae8304f'
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


def extension_exists(extension_name: str) -> bool:
    """Check if a PostgreSQL extension exists."""
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_extension WHERE extname = :name"
    ), {"name": extension_name})
    return result.fetchone() is not None


def upgrade() -> None:
    # Enable pgvector extension if not already enabled
    if not extension_exists('vector'):
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add embedding column to proposals
    if not column_exists('platform_proposals', 'premise_embedding'):
        op.execute(
            "ALTER TABLE platform_proposals "
            "ADD COLUMN premise_embedding vector(1536)"
        )
        # Create index for similarity search
        op.execute(
            "CREATE INDEX IF NOT EXISTS proposals_embedding_idx "
            "ON platform_proposals USING ivfflat (premise_embedding vector_cosine_ops) "
            "WITH (lists = 100)"
        )

    # Add embedding column to worlds
    if not column_exists('platform_worlds', 'premise_embedding'):
        op.execute(
            "ALTER TABLE platform_worlds "
            "ADD COLUMN premise_embedding vector(1536)"
        )
        # Create index for similarity search
        op.execute(
            "CREATE INDEX IF NOT EXISTS worlds_embedding_idx "
            "ON platform_worlds USING ivfflat (premise_embedding vector_cosine_ops) "
            "WITH (lists = 100)"
        )


def downgrade() -> None:
    # Drop indexes first
    op.execute("DROP INDEX IF EXISTS proposals_embedding_idx")
    op.execute("DROP INDEX IF EXISTS worlds_embedding_idx")

    # Drop columns
    if column_exists('platform_proposals', 'premise_embedding'):
        op.drop_column('platform_proposals', 'premise_embedding')

    if column_exists('platform_worlds', 'premise_embedding'):
        op.drop_column('platform_worlds', 'premise_embedding')

    # Note: We don't drop the vector extension as other things may use it
