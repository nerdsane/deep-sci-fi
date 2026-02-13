"""Add critical review system tables and review_system column.

This migration adds the new critical review system alongside the existing
legacy validation tables. Existing content defaults to 'legacy' review system.
New content will use 'critical_review'.

Idempotent: Uses existence checks before creating tables/columns/enums.

Revision ID: 0012
Revises: 0011
Create Date: 2026-02-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: str = "0011"
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = :table"
        ),
        {"table": table_name},
    )
    return result.fetchone() is not None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table_name, "column": column_name},
    )
    return result.fetchone() is not None


def enum_exists(enum_name: str) -> bool:
    """Check if a PostgreSQL enum type exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :name"),
        {"name": enum_name},
    )
    return result.fetchone() is not None


def upgrade():
    conn = op.get_bind()

    # Step 1: Create new enum types if they don't exist
    # IMPORTANT: Use UPPERCASE values to match SQLAlchemy enum member NAMES
    # (see CLAUDE.md "SQLAlchemy Enum Gotcha #2: Case Matching")
    if not enum_exists("reviewsystemtype"):
        op.execute("CREATE TYPE reviewsystemtype AS ENUM ('LEGACY', 'CRITICAL_REVIEW')")

    if not enum_exists("reviewfeedbackcategory"):
        op.execute(
            "CREATE TYPE reviewfeedbackcategory AS ENUM ("
            "'CAUSAL_GAP', 'SCIENTIFIC_ISSUE', 'ACTOR_VAGUENESS', "
            "'TIMELINE', 'INTERNAL_CONSISTENCY', 'OTHER')"
        )

    if not enum_exists("feedbackseverity"):
        op.execute("CREATE TYPE feedbackseverity AS ENUM ('CRITICAL', 'IMPORTANT', 'MINOR')")

    if not enum_exists("feedbackitemstatus"):
        op.execute(
            "CREATE TYPE feedbackitemstatus AS ENUM ("
            "'OPEN', 'ADDRESSED', 'RESOLVED', 'DISPUTED')"
        )

    # Step 2: Add review_system column to content tables
    for table_name in [
        "platform_proposals",
        "platform_aspects",
        "platform_dweller_proposals",
        "platform_stories",
    ]:
        if not column_exists(table_name, "review_system"):
            # Add column with server_default for existing rows
            op.add_column(
                table_name,
                sa.Column(
                    "review_system",
                    postgresql.ENUM(
                        "LEGACY",
                        "CRITICAL_REVIEW",
                        name="reviewsystemtype",
                        create_type=False,
                    ),
                    nullable=False,
                    server_default="LEGACY",
                ),
            )
            # Remove server_default after column is created (we want new rows to default
            # to CRITICAL_REVIEW via model default, not DB default)
            op.alter_column(table_name, "review_system", server_default=None)

    # Step 3: Create platform_review_feedback table
    if not table_exists("platform_review_feedback"):
        op.create_table(
            "platform_review_feedback",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("content_type", sa.String(50), nullable=False),
            sa.Column("content_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["reviewer_id"],
                ["platform_users.id"],
                name=op.f("fk_platform_review_feedback_reviewer_id_platform_users"),
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_review_feedback")),
        )
        op.create_index(
            "review_feedback_content_idx",
            "platform_review_feedback",
            ["content_type", "content_id"],
        )
        op.create_index(
            "review_feedback_reviewer_idx",
            "platform_review_feedback",
            ["reviewer_id"],
        )
        op.create_index(
            "review_feedback_created_at_idx",
            "platform_review_feedback",
            ["created_at"],
        )
        op.create_index(
            "review_feedback_unique_idx",
            "platform_review_feedback",
            ["content_type", "content_id", "reviewer_id"],
            unique=True,
        )

    # Step 4: Create platform_feedback_items table
    if not table_exists("platform_feedback_items"):
        op.create_table(
            "platform_feedback_items",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "review_feedback_id", postgresql.UUID(as_uuid=True), nullable=False
            ),
            sa.Column(
                "category",
                postgresql.ENUM(
                    "CAUSAL_GAP",
                    "SCIENTIFIC_ISSUE",
                    "ACTOR_VAGUENESS",
                    "TIMELINE",
                    "INTERNAL_CONSISTENCY",
                    "OTHER",
                    name="reviewfeedbackcategory",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column(
                "severity",
                postgresql.ENUM(
                    "CRITICAL",
                    "IMPORTANT",
                    "MINOR",
                    name="feedbackseverity",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column(
                "status",
                postgresql.ENUM(
                    "OPEN",
                    "ADDRESSED",
                    "RESOLVED",
                    "DISPUTED",
                    name="feedbackitemstatus",
                    create_type=False,
                ),
                nullable=False,
                server_default="OPEN",
            ),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("resolution_note", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["review_feedback_id"],
                ["platform_review_feedback.id"],
                name=op.f("fk_platform_feedback_items_review_feedback_id_platform_review_feedback"),
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_feedback_items")),
        )
        op.create_index(
            "feedback_item_review_idx",
            "platform_feedback_items",
            ["review_feedback_id"],
        )
        op.create_index(
            "feedback_item_status_idx", "platform_feedback_items", ["status"]
        )
        op.create_index(
            "feedback_item_created_at_idx",
            "platform_feedback_items",
            ["created_at"],
        )

    # Step 5: Create platform_feedback_responses table
    if not table_exists("platform_feedback_responses"):
        op.create_table(
            "platform_feedback_responses",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "feedback_item_id", postgresql.UUID(as_uuid=True), nullable=False
            ),
            sa.Column("responder_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("response_text", sa.Text(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["feedback_item_id"],
                ["platform_feedback_items.id"],
                name=op.f("fk_platform_feedback_responses_feedback_item_id_platform_feedback_items"),
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["responder_id"],
                ["platform_users.id"],
                name=op.f("fk_platform_feedback_responses_responder_id_platform_users"),
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_feedback_responses")),
        )
        op.create_index(
            "feedback_response_item_idx",
            "platform_feedback_responses",
            ["feedback_item_id"],
        )
        op.create_index(
            "feedback_response_responder_idx",
            "platform_feedback_responses",
            ["responder_id"],
        )
        op.create_index(
            "feedback_response_created_at_idx",
            "platform_feedback_responses",
            ["created_at"],
        )


def downgrade():
    """Downgrade removes the critical review tables and review_system column."""
    # Drop tables in reverse order (respecting foreign keys)
    if table_exists("platform_feedback_responses"):
        op.drop_table("platform_feedback_responses")

    if table_exists("platform_feedback_items"):
        op.drop_table("platform_feedback_items")

    if table_exists("platform_review_feedback"):
        op.drop_table("platform_review_feedback")

    # Remove review_system column from content tables
    for table_name in [
        "platform_proposals",
        "platform_aspects",
        "platform_dweller_proposals",
        "platform_stories",
    ]:
        if column_exists(table_name, "review_system"):
            op.drop_column(table_name, "review_system")

    # Drop enum types
    if enum_exists("feedbackitemstatus"):
        op.execute("DROP TYPE feedbackitemstatus")
    if enum_exists("feedbackseverity"):
        op.execute("DROP TYPE feedbackseverity")
    if enum_exists("reviewfeedbackcategory"):
        op.execute("DROP TYPE reviewfeedbackcategory")
    if enum_exists("reviewsystemtype"):
        op.execute("DROP TYPE reviewsystemtype")
