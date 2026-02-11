"""Fix feedback enum case mismatch on staging DB.

SQLAlchemy sends enum member NAMES (uppercase) but some environments
have lowercase enum values. This migration renames lowercase values
to uppercase to match what SQLAlchemy sends.

Idempotent: skips enums that already have uppercase values.

Revision ID: 0011
Revises: 0010
Create Date: 2026-02-11
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

ENUM_FIXES = {
    "feedbackpriority": [
        ("critical", "CRITICAL"),
        ("high", "HIGH"),
        ("medium", "MEDIUM"),
        ("low", "LOW"),
    ],
    "feedbackcategory": [
        ("api_bug", "API_BUG"),
        ("api_usability", "API_USABILITY"),
        ("documentation", "DOCUMENTATION"),
        ("feature_request", "FEATURE_REQUEST"),
        ("error_message", "ERROR_MESSAGE"),
        ("performance", "PERFORMANCE"),
    ],
    "feedbackstatus": [
        ("new", "NEW"),
        ("acknowledged", "ACKNOWLEDGED"),
        ("in_progress", "IN_PROGRESS"),
        ("resolved", "RESOLVED"),
        ("wont_fix", "WONT_FIX"),
    ],
}


def upgrade():
    conn = op.get_bind()
    for enum_name, mappings in ENUM_FIXES.items():
        # Check if the enum has lowercase values (needs fixing)
        result = conn.execute(
            sa.text(
                "SELECT enumlabel FROM pg_enum "
                "JOIN pg_type ON pg_enum.enumtypid = pg_type.oid "
                "WHERE pg_type.typname = :name ORDER BY enumsortorder"
            ),
            {"name": enum_name},
        )
        current_labels = [row[0] for row in result]
        if not current_labels:
            continue

        # If first label is already uppercase, skip
        if current_labels[0] == mappings[0][1]:
            continue

        # Rename lowercase to uppercase
        for old_val, new_val in mappings:
            if old_val in current_labels:
                conn.execute(
                    sa.text(
                        "ALTER TYPE {enum} RENAME VALUE :old TO :new".format(
                            enum=enum_name
                        )
                    ),
                    {"old": old_val, "new": new_val},
                )


def downgrade():
    conn = op.get_bind()
    for enum_name, mappings in ENUM_FIXES.items():
        result = conn.execute(
            sa.text(
                "SELECT enumlabel FROM pg_enum "
                "JOIN pg_type ON pg_enum.enumtypid = pg_type.oid "
                "WHERE pg_type.typname = :name ORDER BY enumsortorder"
            ),
            {"name": enum_name},
        )
        current_labels = [row[0] for row in result]
        if not current_labels:
            continue

        if current_labels[0] == mappings[0][0]:
            continue

        for old_val, new_val in mappings:
            if new_val in current_labels:
                conn.execute(
                    sa.text(
                        "ALTER TYPE {enum} RENAME VALUE :old TO :new".format(
                            enum=enum_name
                        )
                    ),
                    {"old": new_val, "new": old_val},
                )
