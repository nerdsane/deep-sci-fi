"""Add media generation table and media fields to worlds/stories.

- platform_worlds: cover_image_url (Text)
- platform_stories: cover_image_url (Text), video_url (Text), thumbnail_url (Text)
- platform_media_generations: new table for tracking generation requests

Revision ID: 0010
Revises: 0009
Create Date: 2026-02-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0010"
down_revision: str = "0009"
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :column"
    ), {"table": table_name, "column": column_name})
    return result.fetchone() is not None


def table_exists(table_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = :table"
    ), {"table": table_name})
    return result.fetchone() is not None


def enum_exists(enum_name: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM pg_type WHERE typname = :name"
    ), {"name": enum_name})
    return result.fetchone() is not None


def upgrade() -> None:
    # --- Add cover_image_url to worlds ---
    if not column_exists("platform_worlds", "cover_image_url"):
        op.add_column(
            "platform_worlds",
            sa.Column("cover_image_url", sa.Text(), nullable=True),
        )

    # --- Add media fields to stories ---
    if not column_exists("platform_stories", "cover_image_url"):
        op.add_column(
            "platform_stories",
            sa.Column("cover_image_url", sa.Text(), nullable=True),
        )
    if not column_exists("platform_stories", "video_url"):
        op.add_column(
            "platform_stories",
            sa.Column("video_url", sa.Text(), nullable=True),
        )
    if not column_exists("platform_stories", "thumbnail_url"):
        op.add_column(
            "platform_stories",
            sa.Column("thumbnail_url", sa.Text(), nullable=True),
        )

    # --- Create enums for media_generations ---
    if not enum_exists("mediatype"):
        op.execute("CREATE TYPE mediatype AS ENUM ('COVER_IMAGE', 'THUMBNAIL', 'VIDEO')")

    if not enum_exists("mediagenerationstatus"):
        op.execute("CREATE TYPE mediagenerationstatus AS ENUM ('PENDING', 'GENERATING', 'COMPLETED', 'FAILED')")

    # --- Create media_generations table ---
    if not table_exists("platform_media_generations"):
        op.create_table(
            "platform_media_generations",
            sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("requested_by", sa.dialects.postgresql.UUID(as_uuid=True),
                       sa.ForeignKey("platform_users.id"), nullable=False),
            sa.Column("target_type", sa.String(20), nullable=False),
            sa.Column("target_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("media_type", postgresql.ENUM("COVER_IMAGE", "THUMBNAIL", "VIDEO",
                       name="mediatype", create_type=False), nullable=False),
            sa.Column("prompt", sa.Text(), nullable=False),
            sa.Column("provider", sa.String(50), nullable=False),
            sa.Column("status", postgresql.ENUM("PENDING", "GENERATING", "COMPLETED", "FAILED",
                       name="mediagenerationstatus", create_type=False),
                       nullable=False, server_default="PENDING"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("media_url", sa.Text(), nullable=True),
            sa.Column("storage_key", sa.String(500), nullable=True),
            sa.Column("file_size_bytes", sa.Integer(), nullable=True),
            sa.Column("duration_seconds", sa.Float(), nullable=True),
            sa.Column("cost_usd", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True),
                       server_default=sa.func.now(), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )

        # Indexes
        op.create_index("media_gen_requested_by_idx", "platform_media_generations", ["requested_by"])
        op.create_index("media_gen_target_idx", "platform_media_generations", ["target_type", "target_id"])
        op.create_index("media_gen_status_idx", "platform_media_generations", ["status"])
        op.create_index("media_gen_created_at_idx", "platform_media_generations", ["created_at"])


def downgrade() -> None:
    op.drop_table("platform_media_generations")
    op.execute("DROP TYPE IF EXISTS mediagenerationstatus")
    op.execute("DROP TYPE IF EXISTS mediatype")
    op.drop_column("platform_stories", "thumbnail_url")
    op.drop_column("platform_stories", "video_url")
    op.drop_column("platform_stories", "cover_image_url")
    op.drop_column("platform_worlds", "cover_image_url")
