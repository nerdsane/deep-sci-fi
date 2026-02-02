"""Database connection and session management."""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

_db_url = os.getenv("DATABASE_URL", "postgresql://letta:letta@localhost:5432/letta")

# Ensure we use asyncpg driver
DATABASE_URL = _db_url.replace("postgresql://", "postgresql+asyncpg://")

# For Supabase pooled connections, we need specific settings
# Supabase uses pgbouncer which requires prepared_statement_cache_size=0
is_supabase = "supabase" in _db_url or "pooler" in _db_url

# Build connect_args for asyncpg
connect_args = {}
if is_supabase:
    import ssl
    # Supabase pooler doesn't support prepared statements
    connect_args["prepared_statement_cache_size"] = 0
    # Supabase requires SSL
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connect_args["ssl"] = ssl_context

# Remove any query params that asyncpg doesn't understand
if "?" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.split("?")[0]

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args=connect_args,
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


async def init_db() -> None:
    """Initialize database tables."""
    from . import models  # noqa: F401 - Import to register models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
