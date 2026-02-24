"""add inhabited_until lease field to dwellers

Revision ID: 0027
Revises: 0026
Create Date: 2026-02-24 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0028"
down_revision: Union[str, None] = "0027"
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
    if not column_exists("platform_dwellers", "inhabited_until"):
        op.add_column(
            "platform_dwellers",
            sa.Column("inhabited_until", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("platform_dwellers", "inhabited_until")
