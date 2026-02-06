"""E2E tests for the Callback Delivery system (Phase 7).

Tests the flow:
1. Create notification for user with callback_url
2. Background processor sends callbacks
3. Retry logic on failure
4. Status updates (SENT, FAILED)
"""

import asyncio
import pytest
from aiohttp import web
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import Notification, NotificationStatus, User
from utils.notifications import (
    process_pending_notifications,
    send_callback,
    CALLBACK_MAX_RETRIES,
)


class MockCallbackServer:
    """A mock HTTP server to receive callback notifications."""

    def __init__(self):
        self.received_callbacks: list[dict] = []
        self.should_fail = False
        self.fail_count = 0
        self.max_failures = 0
        self.app = web.Application()
        self.app.router.add_post("/callback", self.handle_callback)
        self.runner = None
        self.site = None
        self.port = None

    async def handle_callback(self, request: web.Request) -> web.Response:
        """Handle incoming callback requests."""
        data = await request.json()
        self.received_callbacks.append(data)

        if self.should_fail:
            if self.fail_count < self.max_failures:
                self.fail_count += 1
                return web.Response(status=500, text="Simulated failure")

        return web.Response(status=200, text="OK")

    async def start(self, port: int = 0) -> int:
        """Start the mock server and return the assigned port."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "127.0.0.1", port)
        await self.site.start()
        # Get the actual port (useful when port=0 for random assignment)
        self.port = self.site._server.sockets[0].getsockname()[1]
        return self.port

    async def stop(self):
        """Stop the mock server."""
        if self.runner:
            await self.runner.cleanup()

    def reset(self):
        """Reset the server state."""
        self.received_callbacks = []
        self.should_fail = False
        self.fail_count = 0
        self.max_failures = 0


@pytest.fixture
async def mock_server():
    """Provide a mock callback server for testing."""
    server = MockCallbackServer()
    port = await server.start()
    yield server
    await server.stop()


@pytest.mark.asyncio
async def test_send_callback_success(mock_server: MockCallbackServer, db_session: AsyncSession):
    """Test successful callback delivery."""
    # Create a test notification
    notification = Notification(
        user_id="00000000-0000-0000-0000-000000000001",  # Fake UUID
        notification_type="test_event",
        target_type="test",
        data={"message": "Hello from test"},
        status=NotificationStatus.PENDING,
    )

    callback_url = f"http://127.0.0.1:{mock_server.port}/callback"

    success, error = await send_callback(callback_url, notification)

    assert success is True
    assert error is None
    assert len(mock_server.received_callbacks) == 1
    assert mock_server.received_callbacks[0]["event"] == "test_event"
    assert mock_server.received_callbacks[0]["data"]["message"] == "Hello from test"


@pytest.mark.asyncio
async def test_send_callback_failure(mock_server: MockCallbackServer, db_session: AsyncSession):
    """Test callback delivery failure handling."""
    mock_server.should_fail = True
    mock_server.max_failures = 999  # Always fail

    notification = Notification(
        user_id="00000000-0000-0000-0000-000000000001",
        notification_type="test_event",
        data={},
        status=NotificationStatus.PENDING,
    )

    callback_url = f"http://127.0.0.1:{mock_server.port}/callback"

    success, error = await send_callback(callback_url, notification)

    assert success is False
    assert error is not None
    assert "500" in error


@pytest.mark.asyncio
async def test_send_callback_connection_error(db_session: AsyncSession):
    """Test callback delivery when server is unreachable."""
    notification = Notification(
        user_id="00000000-0000-0000-0000-000000000001",
        notification_type="test_event",
        data={},
        status=NotificationStatus.PENDING,
    )

    # Use a port that's definitely not listening
    callback_url = "http://127.0.0.1:59999/callback"

    success, error = await send_callback(callback_url, notification)

    assert success is False
    assert error is not None
    assert "error" in error.lower()


@pytest.mark.asyncio
async def test_process_pending_notifications_success(
    client: AsyncClient,
    mock_server: MockCallbackServer,
    db_session: AsyncSession,
):
    """Test background processing successfully sends notifications."""
    # Create an agent with a callback URL
    callback_url = f"http://127.0.0.1:{mock_server.port}/callback"

    agent_response = await client.post(
        "/api/auth/agent",
        json={
            "name": "Callback Agent",
            "username": "callback-agent",
            "callback_url": callback_url,
        },
    )
    assert agent_response.status_code == 200
    agent_id = agent_response.json()["agent"]["id"]

    # Create a pending notification directly in the database
    notification = Notification(
        user_id=agent_id,
        notification_type="test_callback",
        target_type="test",
        data={"test": "data"},
        status=NotificationStatus.PENDING,
        retry_count=0,
    )
    db_session.add(notification)
    await db_session.commit()
    notification_id = notification.id

    # Process pending notifications
    stats = await process_pending_notifications(db_session, batch_size=10)

    assert stats["processed"] >= 1
    assert stats["sent"] >= 1

    # Verify notification was received
    assert len(mock_server.received_callbacks) >= 1

    # Verify notification status was updated
    await db_session.refresh(notification)
    assert notification.status == NotificationStatus.SENT
    assert notification.sent_at is not None


@pytest.mark.asyncio
async def test_process_pending_notifications_retry(
    client: AsyncClient,
    mock_server: MockCallbackServer,
    db_session: AsyncSession,
):
    """Test that failed notifications are marked for retry."""
    mock_server.should_fail = True
    mock_server.max_failures = 999  # Always fail

    callback_url = f"http://127.0.0.1:{mock_server.port}/callback"

    # Create an agent with a callback URL
    agent_response = await client.post(
        "/api/auth/agent",
        json={
            "name": "Retry Agent",
            "username": "retry-agent",
            "callback_url": callback_url,
        },
    )
    agent_id = agent_response.json()["agent"]["id"]

    # Create a pending notification
    notification = Notification(
        user_id=agent_id,
        notification_type="test_retry",
        data={},
        status=NotificationStatus.PENDING,
        retry_count=0,
    )
    db_session.add(notification)
    await db_session.commit()

    # Process - should fail and increment retry_count
    stats = await process_pending_notifications(db_session, batch_size=10)

    await db_session.refresh(notification)
    assert notification.status == NotificationStatus.PENDING
    assert notification.retry_count == 1
    assert notification.last_error is not None
    assert stats["retrying"] >= 1


@pytest.mark.asyncio
async def test_process_pending_notifications_max_retries(
    client: AsyncClient,
    mock_server: MockCallbackServer,
    db_session: AsyncSession,
):
    """Test that notifications are marked FAILED after max retries."""
    mock_server.should_fail = True
    mock_server.max_failures = 999

    callback_url = f"http://127.0.0.1:{mock_server.port}/callback"

    agent_response = await client.post(
        "/api/auth/agent",
        json={
            "name": "Max Retry Agent",
            "username": "max-retry-agent",
            "callback_url": callback_url,
        },
    )
    agent_id = agent_response.json()["agent"]["id"]

    # Create notification with retry_count at max - 1
    notification = Notification(
        user_id=agent_id,
        notification_type="test_max_retry",
        data={},
        status=NotificationStatus.PENDING,
        retry_count=CALLBACK_MAX_RETRIES - 1,  # One more failure will exceed max
    )
    db_session.add(notification)
    await db_session.commit()

    # Process - should fail and mark as FAILED
    stats = await process_pending_notifications(db_session, batch_size=10)

    await db_session.refresh(notification)
    assert notification.status == NotificationStatus.FAILED
    assert notification.retry_count == CALLBACK_MAX_RETRIES
    assert stats["failed"] >= 1


@pytest.mark.asyncio
async def test_process_notifications_endpoint(
    client: AsyncClient,
    mock_server: MockCallbackServer,
    db_session: AsyncSession,
):
    """Test the /api/platform/process-notifications endpoint."""
    callback_url = f"http://127.0.0.1:{mock_server.port}/callback"

    # Create an agent with callback URL
    agent_response = await client.post(
        "/api/auth/agent",
        json={
            "name": "Endpoint Test Agent",
            "username": "endpoint-test-agent",
            "callback_url": callback_url,
        },
    )
    agent_id = agent_response.json()["agent"]["id"]

    # Create a pending notification
    notification = Notification(
        user_id=agent_id,
        notification_type="endpoint_test",
        data={"via": "endpoint"},
        status=NotificationStatus.PENDING,
        retry_count=0,
    )
    db_session.add(notification)
    await db_session.commit()

    # Call the process endpoint (requires admin auth)
    process_response = await client.post(
        "/api/platform/process-notifications",
        headers={"X-API-Key": "test-admin-key"},
    )
    assert process_response.status_code == 200

    process_data = process_response.json()
    assert process_data["status"] == "completed"
    assert "stats" in process_data
    assert process_data["stats"]["processed"] >= 1

    # Verify callback was received
    assert len(mock_server.received_callbacks) >= 1


@pytest.mark.asyncio
async def test_notifications_without_callback_url_ignored(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """Test that notifications for users without callback_url are not processed."""
    # Create an agent WITHOUT a callback URL
    agent_response = await client.post(
        "/api/auth/agent",
        json={
            "name": "No Callback Agent",
            "username": "no-callback-agent",
            # No callback_url
        },
    )
    agent_id = agent_response.json()["agent"]["id"]

    # Create a pending notification
    notification = Notification(
        user_id=agent_id,
        notification_type="should_be_ignored",
        data={},
        status=NotificationStatus.PENDING,
        retry_count=0,
    )
    db_session.add(notification)
    await db_session.commit()

    # Process - should not pick up this notification
    stats = await process_pending_notifications(db_session, batch_size=10)

    # Notification should still be pending (not processed because no callback_url)
    await db_session.refresh(notification)
    assert notification.status == NotificationStatus.PENDING
    assert notification.retry_count == 0


@pytest.mark.asyncio
async def test_callback_payload_format(
    client: AsyncClient,
    mock_server: MockCallbackServer,
    db_session: AsyncSession,
):
    """Test that callback payload contains all required fields."""
    callback_url = f"http://127.0.0.1:{mock_server.port}/callback"

    agent_response = await client.post(
        "/api/auth/agent",
        json={
            "name": "Payload Agent",
            "username": "payload-agent",
            "callback_url": callback_url,
        },
    )
    agent_id = agent_response.json()["agent"]["id"]

    # Create notification with specific data
    notification = Notification(
        user_id=agent_id,
        notification_type="dweller_spoken_to",
        target_type="dweller",
        target_id="11111111-1111-1111-1111-111111111111",
        data={
            "from_dweller": "Test Speaker",
            "content": "Hello there!",
        },
        status=NotificationStatus.PENDING,
        retry_count=0,
    )
    db_session.add(notification)
    await db_session.commit()

    await process_pending_notifications(db_session, batch_size=10)

    # Verify payload structure
    assert len(mock_server.received_callbacks) >= 1
    payload = mock_server.received_callbacks[-1]

    assert "event" in payload
    assert payload["event"] == "dweller_spoken_to"
    assert "data" in payload
    assert "notification_id" in payload["data"]
    assert "timestamp" in payload["data"]
    assert "target_type" in payload["data"]
    assert payload["data"]["target_type"] == "dweller"
    assert "target_id" in payload["data"]
    assert payload["data"]["from_dweller"] == "Test Speaker"
    assert payload["data"]["content"] == "Hello there!"
