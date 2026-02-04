"""Fix story enum cases to match SQLAlchemy convention.

Revision ID: 94lllhm8404p
Revises: 93kkkgl7293o
Create Date: 2026-02-04

The storystatus and storyperspective enums were created with lowercase/snake_case values
but SQLAlchemy's Enum type sends uppercase enum member names by default.
This migration fixes the mismatch by updating the enum values to uppercase.

Example issue:
- Database has: 'published', 'acclaimed'
- SQLAlchemy sends: 'PUBLISHED', 'ACCLAIMED'
- Result: "invalid input value for enum storystatus: 'ACCLAIMED'"
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "94lllhm8404p"
down_revision: Union[str, None] = "93kkkgl7293o"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def enum_exists(enum_name: str) -> bool:
    """Check if an enum type exists."""
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :name"),
        {"name": enum_name},
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


def upgrade() -> None:
    """Change story enums from lowercase to uppercase."""

    # =========================================================================
    # Fix storystatus enum: 'published' -> 'PUBLISHED', 'acclaimed' -> 'ACCLAIMED'
    # =========================================================================
    if enum_exists("storystatus"):
        # Rename old enum
        op.execute("ALTER TYPE storystatus RENAME TO storystatus_old")

        # Create new enum with uppercase values
        op.execute("CREATE TYPE storystatus AS ENUM ('PUBLISHED', 'ACCLAIMED')")

        # Update the column to use the new enum
        if column_exists("platform_stories", "status"):
            op.execute("""
                ALTER TABLE platform_stories
                ALTER COLUMN status TYPE text
                USING UPPER(status::text)
            """)

            op.execute("""
                ALTER TABLE platform_stories
                ALTER COLUMN status TYPE storystatus
                USING status::storystatus
            """)

            op.execute("""
                ALTER TABLE platform_stories
                ALTER COLUMN status SET DEFAULT 'PUBLISHED'
            """)

        # Drop old enum
        op.execute("DROP TYPE storystatus_old")

    # =========================================================================
    # Fix storyperspective enum
    # =========================================================================
    if enum_exists("storyperspective"):
        # Rename old enum
        op.execute("ALTER TYPE storyperspective RENAME TO storyperspective_old")

        # Create new enum with uppercase values
        op.execute("""
            CREATE TYPE storyperspective AS ENUM (
                'FIRST_PERSON_AGENT',
                'FIRST_PERSON_DWELLER',
                'THIRD_PERSON_LIMITED',
                'THIRD_PERSON_OMNISCIENT'
            )
        """)

        # Update the column to use the new enum
        if column_exists("platform_stories", "perspective"):
            op.execute("""
                ALTER TABLE platform_stories
                ALTER COLUMN perspective TYPE text
                USING UPPER(perspective::text)
            """)

            op.execute("""
                ALTER TABLE platform_stories
                ALTER COLUMN perspective TYPE storyperspective
                USING perspective::storyperspective
            """)

        # Drop old enum
        op.execute("DROP TYPE storyperspective_old")


def downgrade() -> None:
    """Revert to lowercase enum values."""

    # Revert storystatus
    if enum_exists("storystatus"):
        op.execute("ALTER TYPE storystatus RENAME TO storystatus_old")
        op.execute("CREATE TYPE storystatus AS ENUM ('published', 'acclaimed')")

        if column_exists("platform_stories", "status"):
            op.execute("""
                ALTER TABLE platform_stories
                ALTER COLUMN status TYPE text
                USING LOWER(status::text)
            """)
            op.execute("""
                ALTER TABLE platform_stories
                ALTER COLUMN status TYPE storystatus
                USING status::storystatus
            """)
            op.execute("""
                ALTER TABLE platform_stories
                ALTER COLUMN status SET DEFAULT 'published'
            """)

        op.execute("DROP TYPE storystatus_old")

    # Revert storyperspective
    if enum_exists("storyperspective"):
        op.execute("ALTER TYPE storyperspective RENAME TO storyperspective_old")
        op.execute("""
            CREATE TYPE storyperspective AS ENUM (
                'first_person_agent',
                'first_person_dweller',
                'third_person_limited',
                'third_person_omniscient'
            )
        """)

        if column_exists("platform_stories", "perspective"):
            op.execute("""
                ALTER TABLE platform_stories
                ALTER COLUMN perspective TYPE text
                USING LOWER(perspective::text)
            """)
            op.execute("""
                ALTER TABLE platform_stories
                ALTER COLUMN perspective TYPE storyperspective
                USING perspective::storyperspective
            """)

        op.execute("DROP TYPE storyperspective_old")
