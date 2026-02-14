"""Add video_prompt to stories and image_prompt to proposals.

Required for automatic media generation at creation time.
- platform_stories: video_prompt (Text, nullable)
- platform_proposals: image_prompt (Text, nullable)

Revision ID: 0014
Revises: 0013
Create Date: 2026-02-14
"""
from alembic import op
import sqlalchemy as sa


revision: str = "0014"
down_revision: str = "0013"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :column"
    ), {"table": table_name, "column": column_name})
    return result.fetchone() is not None


def upgrade() -> None:
    # Add video_prompt to stories
    if not column_exists("platform_stories", "video_prompt"):
        op.add_column(
            "platform_stories",
            sa.Column("video_prompt", sa.Text(), nullable=True),
        )

    # Add image_prompt to proposals
    if not column_exists("platform_proposals", "image_prompt"):
        op.add_column(
            "platform_proposals",
            sa.Column("image_prompt", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("platform_proposals", "image_prompt")
    op.drop_column("platform_stories", "video_prompt")
