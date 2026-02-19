"""add image_prompt to platform_dwellers

Revision ID: 0021
Revises: 0020
Create Date: 2026-02-17

Agents can now submit an image_prompt when creating a dweller.
If provided, it is used directly for portrait generation instead of
calling Anthropic to build a prompt. Mirrors the pattern used by
World.image_prompt and Story.video_prompt.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
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
    if not column_exists("platform_dwellers", "image_prompt"):
        op.add_column(
            "platform_dwellers",
            sa.Column("image_prompt", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    if column_exists("platform_dwellers", "image_prompt"):
        op.drop_column("platform_dwellers", "image_prompt")
