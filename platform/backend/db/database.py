"""Database connection and session management."""

import logging
import os
from collections.abc import AsyncGenerator

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

_db_url = os.getenv("DATABASE_URL", "postgresql://deepsci:deepsci@localhost:5432/deepsci")

# Ensure we use asyncpg driver
DATABASE_URL = _db_url.replace("postgresql://", "postgresql+asyncpg://")

# Remove any query params that asyncpg doesn't understand
if "?" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.split("?")[0]

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def _get_latest_migration_from_files() -> str | None:
    """Read the latest migration revision from the alembic versions directory.

    This automatically detects the head revision without manual updates.
    Returns None if unable to determine.
    """
    import re
    from pathlib import Path

    versions_dir = Path(__file__).parent.parent / "alembic" / "versions"
    if not versions_dir.exists():
        return None

    # Find the migration that has no down_revision pointing to it (the head)
    # Or simply get the most recently modified migration file
    migrations = {}
    for f in versions_dir.glob("*.py"):
        if f.name == "__pycache__":
            continue
        content = f.read_text()
        # Extract revision ID
        rev_match = re.search(r"^revision:\s*str\s*=\s*['\"]([^'\"]+)['\"]", content, re.MULTILINE)
        down_match = re.search(r"^down_revision[^=]*=\s*['\"]?([^'\"\n]+)['\"]?", content, re.MULTILINE)
        if rev_match:
            rev = rev_match.group(1)
            down = down_match.group(1).strip() if down_match else None
            if down == "None":
                down = None
            migrations[rev] = down

    if not migrations:
        return None

    # Find the head (revision that no other revision points to as down_revision)
    all_revisions = set(migrations.keys())
    down_revisions = set(v for v in migrations.values() if v)
    heads = all_revisions - down_revisions

    if len(heads) == 1:
        return heads.pop()
    elif len(heads) > 1:
        # Multiple heads - shouldn't happen in a linear history
        # Return any one (this is a configuration issue)
        logger.warning(f"Multiple migration heads detected: {heads}")
        return sorted(heads)[-1]  # Return last alphabetically
    else:
        # Circular dependency or other issue
        return None


# Auto-detect expected migration head from files
# This removes the need to manually update a constant
EXPECTED_MIGRATION_HEAD = _get_latest_migration_from_files()


async def get_current_migration_version() -> str | None:
    """Get the current Alembic migration version from the database.

    Returns None if the alembic_version table doesn't exist or is empty.
    """
    async with engine.connect() as conn:
        try:
            result = await conn.execute(
                sa.text("SELECT version_num FROM alembic_version LIMIT 1")
            )
            row = result.fetchone()
            return row[0] if row else None
        except Exception:
            # Table doesn't exist or other error
            return None


async def verify_schema_version() -> dict:
    """Verify the database schema version matches expected.

    Returns a dict with:
    - is_current: bool - True if schema is at expected version
    - current_version: str | None - Current migration version in DB
    - expected_version: str | None - Expected migration version (from files)
    - message: str - Human-readable status message
    """
    current = await get_current_migration_version()

    if EXPECTED_MIGRATION_HEAD is None:
        return {
            "is_current": True,  # Can't verify, assume OK
            "current_version": current,
            "expected_version": None,
            "message": "Could not determine expected migration version from files.",
        }
    elif current is None:
        return {
            "is_current": False,
            "current_version": None,
            "expected_version": EXPECTED_MIGRATION_HEAD,
            "message": "No migration version found. Database may not be initialized.",
        }
    elif current == EXPECTED_MIGRATION_HEAD:
        return {
            "is_current": True,
            "current_version": current,
            "expected_version": EXPECTED_MIGRATION_HEAD,
            "message": "Schema is up to date.",
        }
    else:
        return {
            "is_current": False,
            "current_version": current,
            "expected_version": EXPECTED_MIGRATION_HEAD,
            "message": f"Schema drift detected! DB at {current}, expected {EXPECTED_MIGRATION_HEAD}. Run 'alembic upgrade head'.",
        }


async def init_db() -> None:
    """Initialize database tables.

    IMPORTANT: In production, tables are managed by Alembic migrations.
    This function only runs create_all() in test environments.

    For production deployments, run `alembic upgrade head` as part of
    the deployment process BEFORE starting the application.
    """
    from . import models  # noqa: F401 - Import to register models

    is_testing = os.getenv("TESTING", "").lower() == "true"
    is_production = os.getenv("ENVIRONMENT", "development") == "production"

    if is_testing:
        # Tests can use create_all() for fast setup
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created (test mode)")
    elif is_production:
        # Production: Alembic migrations only
        # Tables should already exist from migration step in deployment
        logger.info("Production mode: Skipping create_all(), relying on Alembic migrations")
    else:
        # Development: Also use create_all() for convenience
        # But log a warning to remind developers to create migrations
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.warning(
            "Development mode: create_all() ran. "
            "Remember to create Alembic migrations for any schema changes!"
        )
