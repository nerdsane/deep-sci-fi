"""Pydantic Logfire observability — optional distributed tracing.

All functions are no-ops when LOGFIRE_TOKEN is not set.
Each wrapper is individually guarded so one failure never crashes the app.
"""

import logging
import os

logger = logging.getLogger(__name__)

_logfire_enabled = False


def configure_logfire() -> bool:
    """Configure Logfire if LOGFIRE_TOKEN is set. Returns True if enabled."""
    global _logfire_enabled

    token = os.getenv("LOGFIRE_TOKEN")
    if not token:
        logger.info("Logfire observability disabled (LOGFIRE_TOKEN not set)")
        return False

    try:
        import logfire

        environment = os.getenv("ENVIRONMENT", "development")
        logfire.configure(
            token=token,
            service_name="deep-sci-fi-api",
            service_version="0.2.0",
            environment=environment,
        )
        _logfire_enabled = True
        logger.info("Logfire observability enabled (environment=%s)", environment)
        return True
    except Exception:
        logger.warning("Failed to configure Logfire", exc_info=True)
        return False


def setup_logging_handler() -> None:
    """Add Logfire handler to Python's standard logging so all logs appear in traces."""
    if not _logfire_enabled:
        return
    try:
        import logfire

        root_logger = logging.getLogger()
        root_logger.addHandler(logfire.LogfireLoggingHandler())
        logger.info("Logfire: logging handler added")
    except Exception:
        logger.warning("Failed to add Logfire logging handler", exc_info=True)


def instrument_fastapi(app) -> None:
    """Instrument FastAPI with Logfire tracing."""
    if not _logfire_enabled:
        return
    try:
        import logfire

        logfire.instrument_fastapi(
            app,
            excluded_urls="^/health$,^/$,^/docs$,^/redoc$,^/openapi.json$,^/skill.md$,^/heartbeat.md$",
            capture_headers=True,
        )
        logger.info("Logfire: FastAPI instrumented")
    except Exception:
        logger.warning("Failed to instrument FastAPI with Logfire", exc_info=True)


def instrument_sqlalchemy(engine) -> None:
    """Instrument a SQLAlchemy engine with Logfire tracing."""
    if not _logfire_enabled:
        return
    try:
        import logfire

        logfire.instrument_sqlalchemy(engine=engine)
        logger.info("Logfire: SQLAlchemy instrumented")
    except Exception:
        logger.warning("Failed to instrument SQLAlchemy with Logfire", exc_info=True)


def instrument_asyncpg() -> None:
    """Instrument asyncpg globally with Logfire tracing."""
    if not _logfire_enabled:
        return
    try:
        import logfire

        logfire.instrument_asyncpg()
        logger.info("Logfire: asyncpg instrumented")
    except Exception:
        logger.warning("Failed to instrument asyncpg with Logfire", exc_info=True)


def instrument_httpx() -> None:
    """Instrument httpx globally with Logfire tracing."""
    if not _logfire_enabled:
        return
    try:
        import logfire

        logfire.instrument_httpx()
        logger.info("Logfire: httpx instrumented")
    except Exception:
        logger.warning("Failed to instrument httpx with Logfire", exc_info=True)


def instrument_openai() -> None:
    """Instrument OpenAI client globally with Logfire tracing."""
    if not _logfire_enabled:
        return
    try:
        import logfire

        logfire.instrument_openai()
        logger.info("Logfire: OpenAI instrumented")
    except Exception:
        logger.warning("Failed to instrument OpenAI with Logfire", exc_info=True)


def instrument_pydantic() -> None:
    """Instrument Pydantic validation with Logfire tracing.

    Uses record='failure' to trace validation failures only,
    avoiding overwhelming Logfire with every successful validation.
    """
    if not _logfire_enabled:
        return
    try:
        import logfire

        logfire.instrument_pydantic(record="failure")
        logger.info("Logfire: Pydantic instrumented (record=failure)")
    except Exception:
        logger.warning("Failed to instrument Pydantic with Logfire", exc_info=True)


def instrument_system_metrics() -> None:
    """Collect CPU, memory, and swap metrics."""
    if not _logfire_enabled:
        return
    try:
        import logfire

        logfire.instrument_system_metrics()
        logger.info("Logfire: system metrics instrumented")
    except Exception:
        logger.warning("Failed to instrument system metrics with Logfire", exc_info=True)
