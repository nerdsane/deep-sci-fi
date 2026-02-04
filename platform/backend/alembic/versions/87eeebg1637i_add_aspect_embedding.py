"""add embedding column to aspects

Revision ID: 87eeebg1637i
Revises: 86dddaf0526h
Create Date: 2026-02-03 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '87eeebg1637i'
down_revision: Union[str, None] = '86dddaf0526h'
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
    # Add embedding column to aspects for similarity search
    if not column_exists('platform_aspects', 'premise_embedding'):
        op.execute(
            "ALTER TABLE platform_aspects "
            "ADD COLUMN premise_embedding vector(1536)"
        )
        # Create index for similarity search
        op.execute(
            "CREATE INDEX IF NOT EXISTS aspects_embedding_idx "
            "ON platform_aspects USING ivfflat (premise_embedding vector_cosine_ops) "
            "WITH (lists = 100)"
        )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS aspects_embedding_idx")
    if column_exists('platform_aspects', 'premise_embedding'):
        op.drop_column('platform_aspects', 'premise_embedding')
