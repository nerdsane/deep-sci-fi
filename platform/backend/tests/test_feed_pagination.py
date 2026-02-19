"""Feed pagination integration tests — standalone (not DST).

Tests cursor-based keyset pagination on the denormalized feed_events table.
Uses known data with controlled timestamps to verify:
1. No item overlap between pages
2. Chronological ordering within and across pages
3. Exhausted cursor returns empty items
4. Cursor format is valid (ISO_TIMESTAMP|UUID)
"""

import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

# Set env before importing app
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ.setdefault("DST_SIMULATION", "true")

from db.database import Base
from db.models import FeedEvent
from main import app, limiter as main_limiter
from api.auth import limiter as auth_limiter

main_limiter.enabled = False
auth_limiter.enabled = False


def parse_sse_feed(text: str) -> dict:
    """Parse SSE feed/stream response into {'items': [...], 'next_cursor': ...}."""
    items = []
    next_cursor = None
    for chunk in text.split("\n\n"):
        lines = [line for line in chunk.strip().split("\n") if line]
        event_name = None
        event_data = None
        for line in lines:
            if line.startswith("event:"):
                event_name = line[6:].strip()
            elif line.startswith("data:"):
                event_data = json.loads(line[5:].strip())
        if event_name == "feed_items" and event_data and "items" in event_data:
            items.extend(event_data["items"])
        elif event_name == "feed_complete" and event_data:
            next_cursor = event_data.get("next_cursor")
    return {"items": items, "next_cursor": next_cursor}


TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://deepsci:deepsci@localhost:5432/deepsci_test",
)


async def _setup_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine


async def _insert_feed_events(engine, count: int, same_timestamp: bool = False):
    """Insert feed events with controlled timestamps.

    If same_timestamp=True, all events share a single timestamp (worst case
    for pagination — forces the UUID tiebreaker to do all the work).
    """
    base_time = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    event_ids = []
    async with session_factory() as session:
        for i in range(count):
            ts = base_time if same_timestamp else base_time + timedelta(seconds=i)
            event = FeedEvent(
                id=uuid.uuid4(),
                event_type="test_event",
                created_at=ts,
                payload={"index": i, "label": f"event-{i}"},
            )
            session.add(event)
            event_ids.append(event.id)
        await session.commit()
    return event_ids


async def _truncate_all(engine):
    async with engine.begin() as conn:
        result = await conn.execute(
            sa.text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
        tables = [row[0] for row in result.fetchall()]
        if tables:
            quoted = ", ".join(f'"{t}"' for t in tables)
            await conn.execute(sa.text(f"TRUNCATE {quoted} CASCADE"))


async def _dispose(engine):
    await _truncate_all(engine)
    await engine.dispose()


@pytest.fixture()
def feed_client():
    """Yield (TestClient, insert_fn) with DB wiring for feed tests."""
    from db import get_db
    import db.database as db_database_module

    original_session_local = db_database_module.SessionLocal

    client = TestClient(app, base_url="http://test", raise_server_exceptions=False)
    client.__enter__()

    engine = client.portal.call(_setup_engine)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    db_database_module.SessionLocal = session_factory

    def insert(count, same_timestamp=False):
        return client.portal.call(_insert_feed_events, engine, count, same_timestamp)

    def truncate():
        client.portal.call(_truncate_all, engine)

    yield client, insert, truncate

    app.dependency_overrides.clear()
    db_database_module.SessionLocal = original_session_local
    try:
        client.portal.call(_dispose, engine)
    except Exception:
        pass
    client.__exit__(None, None, None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFeedPaginationDistinctTimestamps:
    """Each event has a unique timestamp — pagination uses created_at alone."""

    def test_no_overlap(self, feed_client):
        client, insert, _ = feed_client
        insert(12)

        resp1 = client.get("/api/feed/stream?limit=5")
        assert resp1.status_code == 200
        data1 = parse_sse_feed(resp1.text)
        items1 = data1["items"]
        cursor = data1["next_cursor"]
        assert len(items1) == 5
        assert cursor is not None

        resp2 = client.get(f"/api/feed/stream?limit=5&cursor={cursor}")
        assert resp2.status_code == 200
        data2 = parse_sse_feed(resp2.text)
        items2 = data2["items"]

        ids1 = {item["id"] for item in items1}
        ids2 = {item["id"] for item in items2}
        assert not ids1 & ids2, f"Overlap: {ids1 & ids2}"

    def test_chronological_order(self, feed_client):
        client, insert, _ = feed_client
        insert(12)

        resp = client.get("/api/feed/stream?limit=12")
        data = parse_sse_feed(resp.text)
        dates = [datetime.fromisoformat(item["sort_date"]) for item in data["items"]]
        for i in range(len(dates) - 1):
            assert dates[i] >= dates[i + 1], f"Out of order at index {i}"

    def test_full_pagination_covers_all(self, feed_client):
        client, insert, _ = feed_client
        insert(12)

        all_ids = set()
        cursor = None
        for _ in range(5):  # safety bound
            url = "/api/feed/stream?limit=5"
            if cursor:
                url += f"&cursor={cursor}"
            resp = client.get(url)
            data = parse_sse_feed(resp.text)
            for item in data["items"]:
                all_ids.add(item["id"])
            cursor = data["next_cursor"]
            if not cursor:
                break
        assert len(all_ids) == 12


class TestFeedPaginationSameTimestamp:
    """All events share one timestamp — forces UUID tiebreaker."""

    def test_no_overlap(self, feed_client):
        client, insert, _ = feed_client
        insert(12, same_timestamp=True)

        resp1 = client.get("/api/feed/stream?limit=5")
        assert resp1.status_code == 200
        data1 = parse_sse_feed(resp1.text)
        items1 = data1["items"]
        cursor = data1["next_cursor"]
        assert len(items1) == 5
        assert cursor is not None

        resp2 = client.get(f"/api/feed/stream?limit=5&cursor={cursor}")
        assert resp2.status_code == 200
        data2 = parse_sse_feed(resp2.text)
        items2 = data2["items"]

        ids1 = {item["id"] for item in items1}
        ids2 = {item["id"] for item in items2}
        assert not ids1 & ids2, f"Overlap: {ids1 & ids2}"

    def test_full_pagination_covers_all(self, feed_client):
        client, insert, _ = feed_client
        insert(12, same_timestamp=True)

        all_ids = set()
        cursor = None
        for _ in range(5):
            url = "/api/feed/stream?limit=5"
            if cursor:
                url += f"&cursor={cursor}"
            resp = client.get(url)
            data = parse_sse_feed(resp.text)
            for item in data["items"]:
                all_ids.add(item["id"])
            cursor = data["next_cursor"]
            if not cursor:
                break
        assert len(all_ids) == 12


class TestFeedPaginationEdgeCases:
    """Cursor edge cases."""

    def test_exhausted_cursor(self, feed_client):
        client, insert, _ = feed_client
        insert(3)

        resp = client.get("/api/feed/stream?limit=5&cursor=1970-01-01T00:00:00")
        assert resp.status_code == 200
        data = parse_sse_feed(resp.text)
        assert data["items"] == []

    def test_cursor_format(self, feed_client):
        client, insert, _ = feed_client
        insert(8)

        resp = client.get("/api/feed/stream?limit=5")
        data = parse_sse_feed(resp.text)
        cursor = data["next_cursor"]
        assert cursor is not None
        assert "~" in cursor
        ts_part, id_part = cursor.split("~", 1)
        datetime.fromisoformat(ts_part)
        uuid.UUID(id_part)

    def test_empty_feed(self, feed_client):
        client, _, _ = feed_client

        resp = client.get("/api/feed/stream?limit=5")
        assert resp.status_code == 200
        data = parse_sse_feed(resp.text)
        assert data["items"] == []
        assert data["next_cursor"] is None

    def test_fewer_than_limit(self, feed_client):
        client, insert, _ = feed_client
        insert(3)

        resp = client.get("/api/feed/stream?limit=5")
        data = parse_sse_feed(resp.text)
        assert len(data["items"]) == 3

        # Cursor is still returned (allows "check for more" pattern).
        # Following it should yield an empty page.
        if data["next_cursor"]:
            resp2 = client.get(f"/api/feed/stream?limit=5&cursor={data['next_cursor']}")
            data2 = parse_sse_feed(resp2.text)
            assert data2["items"] == []
