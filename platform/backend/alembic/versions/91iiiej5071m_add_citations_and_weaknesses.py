"""Add citations to proposals and weaknesses to validations.

Revision ID: 91iiiej5071m
Revises: 90hhhdi4960l
Create Date: 2026-02-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "91iiiej5071m"
down_revision: Union[str, None] = "90hhhdi4960l"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table_name, "column": column_name},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    # Add citations column to proposals (JSONB for array of citation objects)
    if not column_exists("platform_proposals", "citations"):
        op.add_column(
            "platform_proposals",
            sa.Column("citations", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )

    # Add weaknesses column to validations (array of text)
    if not column_exists("platform_validations", "weaknesses"):
        op.add_column(
            "platform_validations",
            sa.Column("weaknesses", postgresql.ARRAY(sa.Text()), nullable=True),
        )


def downgrade() -> None:
    # Remove weaknesses column from validations
    if column_exists("platform_validations", "weaknesses"):
        op.drop_column("platform_validations", "weaknesses")

    # Remove citations column from proposals
    if column_exists("platform_proposals", "citations"):
        op.drop_column("platform_proposals", "citations")
