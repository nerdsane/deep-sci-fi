# 035 - Add Pydantic Logfire Observability

**Created:** 2026-02-04
**Status:** Complete

## Goal

Add Pydantic Logfire to the FastAPI backend for distributed tracing and observability.
Logfire is optional — the app runs normally without `LOGFIRE_TOKEN` set.

## Phases

- [x] Phase 1: Add logfire dependency to requirements.txt
- [x] Phase 2: Create `platform/backend/observability.py` module
- [x] Phase 3: Wire observability into `main.py`
- [x] Phase 4: Update `.env.example` files
- [x] Phase 5: Verify implementation

## Auto-Instrumented

- FastAPI requests
- SQLAlchemy queries
- asyncpg connections
- httpx calls
- OpenAI API calls

## No Changes To

- db/database.py, utils/notifications.py, utils/embeddings.py
- Middleware, exception handlers, route handlers
- Database tables or migrations
- Existing logging or tests
