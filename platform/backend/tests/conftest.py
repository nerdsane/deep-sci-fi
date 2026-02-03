"""Shared test fixtures for Deep Sci-Fi backend tests."""

import os
import sys

# IMPORTANT: Set TESTING env var before importing app to disable rate limiting
# This must happen before any imports that might trigger main.py
os.environ["TESTING"] = "true"

# Force reimport of main module if already loaded (for pytest-xdist workers)
if 'main' in sys.modules:
    del sys.modules['main']

import pytest
import pytest_asyncio
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from httpx import ASGITransport, AsyncClient

from db.database import Base
from main import app, limiter as main_limiter
from api.auth import limiter as auth_limiter

# Ensure rate limiters are disabled for tests
main_limiter.enabled = False
auth_limiter.enabled = False


# Use PostgreSQL for integration tests (SQLite doesn't support JSONB/ARRAY types)
# Default to local test database, override with TEST_DATABASE_URL
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://deepsci:deepsci@localhost:5432/deepsci_test"
)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated database session for each test.

    Requires PostgreSQL because the models use PostgreSQL-specific types (JSONB, ARRAY).
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()

    # Cleanup - drop all tables for isolation
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx AsyncClient with test database override."""
    from db import get_db

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_agent(client: AsyncClient, db_session: AsyncSession) -> dict[str, Any]:
    """Create a test agent and return its info including API key."""
    response = await client.post(
        "/api/auth/agent",
        json={
            "name": "Test Agent",
            "username": "test-agent",
            "description": "A test agent for unit tests",
        }
    )
    assert response.status_code == 200
    data = response.json()
    return {
        "user": data["agent"],
        "api_key": data["api_key"]["key"],
    }


@pytest_asyncio.fixture
async def second_agent(client: AsyncClient, db_session: AsyncSession) -> dict[str, Any]:
    """Create a second test agent (useful for validation scenarios)."""
    response = await client.post(
        "/api/auth/agent",
        json={
            "name": "Second Agent",
            "username": "second-agent",
            "description": "A second test agent for validation tests",
        }
    )
    assert response.status_code == 200
    data = response.json()
    return {
        "user": data["agent"],
        "api_key": data["api_key"]["key"],
    }


# Sample test data that can be reused across tests
SAMPLE_CAUSAL_CHAIN = [
    {
        "year": 2028,
        "event": "First commercial fusion reactor achieves net energy gain",
        "reasoning": "ITER demonstrates Q>10, private companies race to commercialize"
    },
    {
        "year": 2032,
        "event": "Fusion power becomes cost-competitive with natural gas",
        "reasoning": "Learning curve drives costs down, carbon pricing makes fossil fuels expensive"
    },
    {
        "year": 2040,
        "event": "Global energy abundance enables large-scale desalination",
        "reasoning": "Cheap electricity makes previously uneconomical water production viable"
    }
]


SAMPLE_REGION = {
    "name": "Test Region",
    "location": "Test Location",
    "population_origins": ["Test origin 1", "Test origin 2"],
    "cultural_blend": "Test cultural blend",
    "naming_conventions": (
        "Names follow test conventions: First names are simple, "
        "family names reflect test heritage. Examples: Test Person, Sample Name."
    ),
    "language": "Test English"
}


SAMPLE_DWELLER = {
    "name": "Test Dweller",
    "origin_region": "Test Region",
    "generation": "First-generation",
    "name_context": (
        "Test Dweller is named following the test conventions of the region, "
        "reflecting the heritage and culture of the test world."
    ),
    "cultural_identity": "Test cultural identity for the dweller",
    "role": "Test role in the world",
    "age": 30,
    "personality": (
        "A test personality with sufficient detail to meet the minimum "
        "character requirements for dweller creation validation."
    ),
    "background": "Test background story for the dweller character"
}
