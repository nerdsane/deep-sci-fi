"""Shared test fixtures for Deep Sci-Fi backend tests."""

import os
import sys
from uuid import uuid4

# IMPORTANT: Set env vars before importing app to disable rate limiting
# and enable admin auth for test fixtures. Must happen before any imports.
os.environ["TESTING"] = "true"
os.environ["ADMIN_API_KEY"] = "test-admin-key"
os.environ["DEDUP_WINDOW_OVERRIDE_SECONDS"] = "0"

# Force reimport of main module if already loaded (for pytest-xdist workers)
if 'main' in sys.modules:
    del sys.modules['main']

import pytest
import pytest_asyncio
import sqlalchemy as sa
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

# Disable AgentContextMiddleware during tests.
# It uses BaseHTTPMiddleware which has known issues with async dependency injection
# (wraps handlers in a TaskGroup, causing session cleanup to conflict with
# middleware database operations → asyncpg "another operation is in progress").
# It also uses SessionLocal directly (bypassing get_db override), hitting the
# production engine instead of the test engine.
from middleware.agent_context import AgentContextMiddleware


async def _passthrough_dispatch(self, request, call_next):
    return await call_next(request)


AgentContextMiddleware.dispatch = _passthrough_dispatch


# Use PostgreSQL for integration tests (SQLite doesn't support JSONB/ARRAY types)
# Default to local test database, override with TEST_DATABASE_URL
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://deepsci:deepsci@localhost:5432/deepsci_test"
)

# Standard research text that meets the 100-char minimum for validation
VALID_RESEARCH = (
    "I researched the scientific basis by reviewing ITER progress reports, fusion startup "
    "funding trends, and historical energy cost curves. The causal chain aligns with "
    "mainstream fusion research timelines and economic projections from IEA reports."
)


@pytest_asyncio.fixture
async def db_engine():
    """Create a test database engine with tables. Torn down after each test."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_size=10,
        max_overflow=5,
    )

    # Ensure pgvector extension exists before creating tables
    async with engine.begin() as conn:
        await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup - drop all tables for isolation
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for direct DB access in tests.

    Requires PostgreSQL because the models use PostgreSQL-specific types (JSONB, ARRAY).
    """
    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx AsyncClient with per-request database sessions.

    Each HTTP request gets its own session (matching production behavior),
    which prevents asyncpg 'another operation is in progress' errors.
    """
    from db import get_db
    import db as db_module
    import db.database as db_database_module

    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    # Also override SessionLocal so any code bypassing dependency injection
    # (e.g. middleware, utility functions) uses the test engine
    original_session_local = db_database_module.SessionLocal
    db_database_module.SessionLocal = session_factory
    db_module.SessionLocal = session_factory

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    db_database_module.SessionLocal = original_session_local
    db_module.SessionLocal = original_session_local


@pytest_asyncio.fixture
async def test_agent(client: AsyncClient) -> dict[str, Any]:
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
async def second_agent(client: AsyncClient) -> dict[str, Any]:
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


async def approve_proposal(client: AsyncClient, proposal_id: str, proposer_key: str) -> dict:
    """Submit and approve a proposal with 2 validations to meet APPROVAL_THRESHOLD.

    The proposer self-validates (test_mode), then a helper agent provides the
    second approval. Returns the final validation response dict which includes
    world_created on success.
    """
    # Submit the proposal
    submit_resp = await client.post(
        f"/api/proposals/{proposal_id}/submit",
        headers={"X-API-Key": proposer_key},
    )
    assert submit_resp.status_code == 200, f"Submit failed: {submit_resp.json()}"

    # First validation: proposer self-validates with test_mode
    r1 = await client.post(
        f"/api/proposals/{proposal_id}/validate?test_mode=true",
        headers={"X-API-Key": proposer_key},
        json={
            "verdict": "approve",
            "research_conducted": VALID_RESEARCH,
            "critique": "Test approval with sufficient length for validation requirements.",
            "scientific_issues": [],
            "suggested_fixes": [],
            "weaknesses": ["Timeline optimism in intermediate steps"],
        },
    )
    assert r1.status_code == 200, f"First validation failed: {r1.json()}"

    # Second validation: create helper agent
    helper_resp = await client.post(
        "/api/auth/agent",
        json={
            "name": "Approval Helper",
            "username": f"approval-helper-{uuid4().hex[:8]}",
        },
    )
    assert helper_resp.status_code == 200
    helper_key = helper_resp.json()["api_key"]["key"]

    r2 = await client.post(
        f"/api/proposals/{proposal_id}/validate",
        headers={"X-API-Key": helper_key},
        json={
            "verdict": "approve",
            "research_conducted": VALID_RESEARCH,
            "critique": "Second approval with sufficient length for validation requirements.",
            "scientific_issues": [],
            "suggested_fixes": [],
            "weaknesses": ["Timeline optimism in intermediate steps"],
        },
    )
    assert r2.status_code == 200, f"Second validation failed: {r2.json()}"
    return r2.json()


async def get_context_token(client: AsyncClient, dweller_id: str, api_key: str, target: str | None = None) -> str:
    """Get a context token for a dweller (required before POST /act)."""
    body = {"target": target} if target else None
    resp = await client.post(
        f"/api/dwellers/{dweller_id}/act/context",
        headers={"X-API-Key": api_key},
        json=body,
    )
    assert resp.status_code == 200, f"get_context_token failed: {resp.json()}"
    return resp.json()["context_token"]


async def act_with_context(
    client: AsyncClient,
    dweller_id: str,
    api_key: str,
    action_type: str,
    content: str,
    target: str | None = None,
    importance: float = 0.5,
    in_reply_to_action_id: str | None = None,
) -> dict:
    """Two-phase action: get context token then act. Returns the act response dict."""
    token = await get_context_token(client, dweller_id, api_key, target=target)
    body = {
        "context_token": token,
        "action_type": action_type,
        "content": content,
        "importance": importance,
    }
    if target:
        body["target"] = target
    if in_reply_to_action_id:
        body["in_reply_to_action_id"] = in_reply_to_action_id
    resp = await client.post(
        f"/api/dwellers/{dweller_id}/act",
        headers={"X-API-Key": api_key},
        json=body,
    )
    return resp


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
    "name": "Edmund Whitestone",
    "origin_region": "Test Region",
    "generation": "First-generation",
    "name_context": (
        "Edmund is a traditional name preserved by first-generation settlers; "
        "Whitestone references the limestone cliffs of this region's early settlements."
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
