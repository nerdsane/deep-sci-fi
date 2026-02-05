"""DST simulation test fixtures.

Key design: sync httpx.Client with ASGITransport. Hypothesis rules are
synchronous; httpx handles the async bridge internally.

Schema validation: at session startup, every strategy generator is validated
against its corresponding Pydantic model to catch schema drift.
"""

import asyncio
import importlib
import inspect
import os
import uuid
from collections.abc import AsyncGenerator

import sqlalchemy as sa
from httpx import Client, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from utils.clock import SimulatedClock, set_clock, reset_clock
from utils.simulation import init_simulation, reset_simulation


# Set env vars before importing app
os.environ["TESTING"] = "true"
os.environ["ADMIN_API_KEY"] = "test-admin-key"
os.environ["DEDUP_WINDOW_OVERRIDE_SECONDS"] = "0"
os.environ["DST_SIMULATION"] = "true"
# DO NOT set DSF_TEST_MODE_ENABLED — no self-validation shortcuts

# Force reimport after env setup
import sys
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith(("main", "api.", "db.", "utils.", "middleware.", "guidance")):
        del sys.modules[mod_name]

from db.database import Base
from main import app, limiter as main_limiter
from api.auth import limiter as auth_limiter
from middleware.agent_context import AgentContextMiddleware


# Patch middleware
async def _passthrough_dispatch(self, request, call_next):
    return await call_next(request)

AgentContextMiddleware.dispatch = _passthrough_dispatch

# Disable rate limiters
main_limiter.enabled = False
auth_limiter.enabled = False

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://deepsci:deepsci@localhost:5432/deepsci_test",
)


def _run_async(coro):
    """Run an async coroutine from sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
    except RuntimeError:
        pass
    return asyncio.run(coro)


async def _setup_db(engine):
    async with engine.begin() as conn:
        await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _teardown_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def create_dst_engine_and_client(seed: int = 0):
    """Create a sync test client with simulation infrastructure.

    Returns:
        (client, sim_clock, cleanup_fn)
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_size=10,
        max_overflow=5,
    )

    _run_async(_setup_db(engine))

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    from db import get_db
    import db as db_module
    import db.database as db_database_module

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    original_session_local = db_database_module.SessionLocal
    db_database_module.SessionLocal = session_factory
    db_module.SessionLocal = session_factory

    # Initialize simulation infrastructure
    sim_clock = SimulatedClock()
    set_clock(sim_clock)
    init_simulation(seed)

    transport = ASGITransport(app=app)
    client = Client(transport=transport, base_url="http://test")

    def cleanup():
        client.close()
        app.dependency_overrides.clear()
        db_database_module.SessionLocal = original_session_local
        db_module.SessionLocal = original_session_local
        reset_clock()
        reset_simulation()
        _run_async(_teardown_db(engine))

    return client, sim_clock, cleanup


# ---------------------------------------------------------------------------
# Schema validation: fail fast if test data generators drift from Pydantic models
# ---------------------------------------------------------------------------

def _call_generator(func):
    """Call a strategy generator with appropriate dummy args based on signature."""
    sig = inspect.signature(func)
    kwargs = {}
    for name, param in sig.parameters.items():
        if param.default is not inspect.Parameter.empty:
            continue  # has default, skip
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
