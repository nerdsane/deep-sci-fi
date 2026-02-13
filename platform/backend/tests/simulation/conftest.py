"""DST simulation test fixtures.

Key design: Starlette TestClient wraps the FastAPI ASGI app for sync
access. Hypothesis rules are synchronous; TestClient handles the
async bridge internally.

CRITICAL: All async DB operations (engine creation, setup, teardown) run
inside the TestClient's portal — the same event loop that serves ASGI
requests. This prevents asyncpg "attached to a different loop" errors.

Schema validation: at session startup, every strategy generator is validated
against its corresponding Pydantic model to catch schema drift.
"""

import importlib
import inspect
import os
import uuid
from collections.abc import AsyncGenerator

import sqlalchemy as sa
from starlette.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from hypothesis import settings as hypothesis_settings, HealthCheck

from utils.clock import reset_clock
from utils.simulation import reset_simulation

# Hypothesis profiles: "ci" for thorough CI exploration, "default" for fast local runs
hypothesis_settings.register_profile(
    "ci",
    max_examples=200,
    stateful_step_count=30,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)
hypothesis_settings.register_profile(
    "default",
    max_examples=50,
    stateful_step_count=30,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)
# Load "default" profile so tests that don't specify max_examples get 50 locally.
# CI overrides this with --hypothesis-profile=ci (200 examples).
hypothesis_settings.load_profile("default")


# Set env vars before importing app
os.environ["TESTING"] = "true"
os.environ["ADMIN_API_KEY"] = "test-admin-key"
os.environ["DEDUP_WINDOW_OVERRIDE_SECONDS"] = "0"
os.environ["DST_SIMULATION"] = "true"
# DO NOT set DSF_TEST_MODE_ENABLED — no self-validation shortcuts

# Force reimport after env setup
import sys
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith(("main", "api.", "db.", "utils.", "middleware.", "guidance", "media.", "storage.")):
        del sys.modules[mod_name]

from db.database import Base
from main import app, limiter as main_limiter
from api.auth import limiter as auth_limiter

# AgentContextMiddleware is now pure ASGI (no BaseHTTPMiddleware), so it runs
# in DST without TaskGroup conflicts. We test what we ship.

# Disable rate limiters
main_limiter.enabled = False
auth_limiter.enabled = False

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://deepsci:deepsci@localhost:5432/deepsci_test",
)


async def _create_engine_and_setup():
    """Create async engine and set up tables. Runs inside TestClient's event loop."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_size=10,
        max_overflow=5,
    )
    async with engine.begin() as conn:
        await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine


async def _teardown_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        # Drop enum types that survive DROP TABLE (but preserve extensions)
        await conn.execute(sa.text("""
            DO $$ DECLARE r RECORD;
            BEGIN
                FOR r IN (SELECT typname FROM pg_type
                          JOIN pg_namespace ON pg_type.typnamespace = pg_namespace.oid
                          WHERE pg_namespace.nspname = 'public' AND pg_type.typtype = 'e')
                LOOP
                    EXECUTE 'DROP TYPE IF EXISTS ' || quote_ident(r.typname) || ' CASCADE';
                END LOOP;
            END $$;
        """))
    await engine.dispose()


def create_dst_engine_and_client():
    """Create a sync test client with DB wiring (no simulation seed/clock).

    Simulation seed and clock are initialized separately in the @initialize
    rule (setup_agents) so Hypothesis can vary the seed per example.

    All async operations (engine creation, DB setup, teardown) run inside the
    TestClient's portal — the same event loop that serves ASGI requests. This
    prevents asyncpg "attached to a different loop" errors.

    Key sequence:
    1. Enter TestClient context (starts portal + lifespan; init_db is a
       no-op because DST_SIMULATION env var is set — see db/database.py)
    2. Create engine + tables inside the portal's event loop
    3. Wire session factory into dependency injection

    Returns:
        (client, cleanup_fn)
    """
    from db import get_db
    import db as db_module
    import db.database as db_database_module

    original_session_local = db_database_module.SessionLocal

    # Enter TestClient context manager to get a persistent portal/event loop.
    # The lifespan's init_db() is a no-op when DST_SIMULATION is set (checked
    # in db/database.py), so it won't use the stale module-level engine.
    client = TestClient(app, base_url="http://test", raise_server_exceptions=False)
    client.__enter__()

    # Create engine and set up DB inside the TestClient's event loop.
    engine = client.portal.call(_create_engine_and_setup)

    session_factory = async_sessionmaker(
        engine,
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
    db_database_module.SessionLocal = session_factory
    db_module.SessionLocal = session_factory

    def cleanup():
        app.dependency_overrides.clear()
        db_database_module.SessionLocal = original_session_local
        db_module.SessionLocal = original_session_local
        reset_clock()
        reset_simulation()
        # Teardown DB inside the same portal/event loop
        try:
            client.portal.call(_teardown_db, engine)
        except Exception:
            # Event loop may be closing. Safe to ignore: CI drops the DB anyway.
            pass
        client.__exit__(None, None, None)

    return client, cleanup


# ---------------------------------------------------------------------------
# Schema validation: fail fast if test data generators drift from Pydantic models
# ---------------------------------------------------------------------------

def _call_generator(func):
    """Call a strategy generator with appropriate dummy args based on signature."""
    sig = inspect.signature(func)
    kwargs = {}
    for name, param in sig.parameters.items():
        if param.default is not inspect.Parameter.empty:
            # Override empty-string defaults for ID fields (Pydantic expects UUIDs)
            if param.default == "" and "id" in name:
                kwargs[name] = str(uuid.uuid4())
            continue  # has default, skip or already overridden
        # Provide dummy values for required args
        if "region" in name:
            kwargs[name] = "Test Region"
        elif "world" in name or "id" in name:
            kwargs[name] = str(uuid.uuid4())
        elif "type" in name:
            kwargs[name] = "world"
        else:
            kwargs[name] = "test"
    return func(**kwargs)


def validate_strategy_schemas():
    """Validate all strategy generators produce data accepted by Pydantic models."""
    from tests.simulation import strategies as strat

    if not hasattr(strat, "STRATEGY_SCHEMA_MAP"):
        return

    errors = []
    for func_name, (module_path, model_name) in strat.STRATEGY_SCHEMA_MAP.items():
        try:
            mod = importlib.import_module(module_path)
            model_cls = getattr(mod, model_name)
            generator = getattr(strat, func_name)
            sample = _call_generator(generator)
            model_cls.model_validate(sample)
        except Exception as e:
            errors.append(f"  {func_name} -> {module_path}.{model_name}: {e}")

    if errors:
        msg = "Schema drift detected! Strategy generators don't match Pydantic models:\n"
        msg += "\n".join(errors)
        msg += "\n\nFix: update strategies.py generators to match current request models."
        raise AssertionError(msg)


# Run schema validation at import time (session startup)
try:
    validate_strategy_schemas()
except AssertionError:
    # Re-raise but only if not in a context where models can't be loaded
    # (e.g., missing database). In CI this will always run.
    import traceback
    traceback.print_exc()
    raise
