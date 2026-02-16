"""Seed PENDING cover image generations for stories with videos but no covers.

One-shot data migration. The process-pending endpoint will pick these up.

Revision ID: 0018
Revises: 0017
"""
from typing import Union
from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO platform_media_generations 
            (id, requested_by, target_type, target_id, media_type, prompt, provider, status, retry_count, created_at)
        SELECT
            gen_random_uuid(),
            (SELECT id FROM platform_users LIMIT 1),
            'story',
            s.id,
            'COVER_IMAGE',
            s.video_prompt,
            'grok_imagine_image',
            'PENDING',
            0,
            NOW()
        FROM platform_stories s
        WHERE s.video_url IS NOT NULL
          AND s.cover_image_url IS NULL
          AND s.video_prompt IS NOT NULL
    """)


def downgrade() -> None:
    # Can't cleanly undo — the generations will have run
    pass
