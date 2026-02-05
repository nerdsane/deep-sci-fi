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

_connect_args = {}
_engine_kwargs = {}
if "supabase" in DATABASE_URL or "pooler" in DATABASE_URL:
    import ssl as _ssl
    import tempfile
    from base64 import b64decode
    from pathlib import Path

    _connect_args["statement_cache_size"] = 0
    _engine_kwargs["pool_pre_ping"] = True

    # SSL Configuration for Supabase Pooler
    # =====================================
    # Supabase's connection pooler uses a CA certificate that's not in standard
    # system CA stores. The PROPER fix is to configure the CA certificate.
    #
    # Options (in order of preference):
    # 1. SUPABASE_CA_CERT env var: Base64-encoded or raw PEM certificate
    # 2. Bundled cert file: platform/backend/certs/supabase-ca.crt
    # 3. Fallback: Disable verification (NOT RECOMMENDED for production)

    _ca_cert = os.getenv("SUPABASE_CA_CERT", "")
    _cert_file = Path(__file__).parent.parent / "certs" / "supabase-ca.crt"
    _temp_cert_file = None

    if _ca_cert:
        # Option 1: CA cert from environment variable
        try:
            # Try base64 decode first
            if not _ca_cert.startswith("-----BEGIN"):
                _ca_cert = b64decode(_ca_cert).decode("utf-8")

            # Write to temp file for ssl context
            _temp_cert_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".crt", delete=False
            )
            _temp_cert_file.write(_ca_cert)
            _temp_cert_file.close()

            _ssl_ctx = _ssl.create_default_context(cafile=_temp_cert_file.name)
            _connect_args["ssl"] = _ssl_ctx
            logger.info("SSL: Using CA certificate from SUPABASE_CA_CERT env var")
        except Exception as e:
            logger.warning(f"SSL: Failed to parse SUPABASE_CA_CERT: {e}")
            _ca_cert = ""  # Fall through to other options

    if not _ca_cert and _cert_file.exists():
        # Option 2: Bundled certificate file
        _ssl_ctx = _ssl.create_default_context(cafile=str(_cert_file))
        _connect_args["ssl"] = _ssl_ctx
        logger.info(f"SSL: Using bundled CA certificate from {_cert_file}")

    if "ssl" not in _connect_args:
        # Option 3: Fallback - disable verification (with warning)
        logger.warning(
            "SSL: No CA certificate configured for Supabase. "
            "Disabling certificate verification. "
            "To fix: set SUPABASE_CA_CERT env var or add certs/supabase-ca.crt. "
            "Download cert from Supabase Dashboard > Database Settings > SSL Configuration."
        )
        _ssl_ctx = _ssl.create_default_context()
        _ssl_ctx.check_hostname = False
        _ssl_ctx.verify_mode = _ssl.CERT_NONE
        _connect_args["ssl"] = _ssl_ctx

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args=_connect_args,
    **_engine_kwargs,
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

    Tables are ALWAYS managed by Alembic migrations. create_all() is only
    used in test environments for fast setup.

    For all other environments (dev, staging, production), run
    `alembic upgrade head` before starting the application.
    """
    from . import models  # noqa: F401 - Import to register models

    is_testing = os.getenv("TESTING", "").lower() == "true"

    if is_testing:
        # Tests use create_all() for fast setup (no migration history needed)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created (test mode)")
    else:
        # All real environments: Alembic migrations only.
        # Never use create_all() — it creates tables without migration
        # history, causing schema drift when models evolve.
        logger.info("Schema managed by Alembic migrations")
