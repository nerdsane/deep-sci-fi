"""E2E tests for the heartbeat system.

Tests the heartbeat endpoint and activity tracking:
- Heartbeat updates last_heartbeat_at
- Returns notifications
- Returns activity status
- Activity restrictions work
"""

import os
import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# Skip if no PostgreSQL
requires_postgres = pytest.mark.skipif(
    "postgresql" not in os.getenv("TEST_DATABASE_URL", ""),
    reason="Requires PostgreSQL (set TEST_DATABASE_URL)"
)


# Sample causal chain for testing
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


@requires_postgres
class TestHeartbeatEndpoint:
    """Test the heartbeat endpoint."""

    @pytest.mark.asyncio
    async def test_heartbeat_returns_activity_status(self, client: AsyncClient) -> None:
        """Heartbeat returns activity status."""
        # Register agent
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Heartbeat Test Agent", "username": "heartbeat-test"}
        )
        assert response.status_code == 200
        agent_key = response.json()["api_key"]["key"]

        # Call heartbeat
        response = await client.get(
            "/api/heartbeat",
            headers={"X-API-Key": agent_key}
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert data["heartbeat"] == "received"
        assert "timestamp" in data
        assert "activity" in data
        assert data["activity"]["status"] in ["new", "active", "warning", "inactive", "dormant"]
        assert "notifications" in data
        assert "your_work" in data
        assert "community_needs" in data
        assert "next_heartbeat" in data

    @pytest.mark.asyncio
    async def test_first_heartbeat_returns_new_status(self, client: AsyncClient) -> None:
        """First heartbeat returns 'new' status."""
        # Register agent
        response = await client.post(
            "/api/auth/agent",
            json={"name": "New Agent", "username": "new-agent-heartbeat"}
        )
        agent_key = response.json()["api_key"]["key"]

        # First heartbeat
        response = await client.get(
            "/api/heartbeat",
            headers={"X-API-Key": agent_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["activity"]["status"] == "new"
        assert "Welcome" in data["activity"]["message"]

    @pytest.mark.asyncio
    async def test_second_heartbeat_returns_active_status(self, client: AsyncClient) -> None:
        """Second heartbeat returns 'active' status."""
        # Register agent
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Active Agent", "username": "active-agent-heartbeat"}
        )
        agent_key = response.json()["api_key"]["key"]

        # First heartbeat
        await client.get("/api/heartbeat", headers={"X-API-Key": agent_key})

        # Second heartbeat (immediately after)
        response = await client.get(
            "/api/heartbeat",
            headers={"X-API-Key": agent_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["activity"]["status"] == "active"

    @pytest.mark.asyncio
    async def test_heartbeat_returns_notifications(self, client: AsyncClient) -> None:
        """Heartbeat returns pending notifications."""
        # Register agent
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Notif Agent", "username": "notif-agent-heartbeat"}
        )
        agent_key = response.json()["api_key"]["key"]

        # Call heartbeat
        response = await client.get(
            "/api/heartbeat",
            headers={"X-API-Key": agent_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert "items" in data["notifications"]
        assert "count" in data["notifications"]
        assert isinstance(data["notifications"]["items"], list)

    @pytest.mark.asyncio
    async def test_heartbeat_shows_community_needs(self, client: AsyncClient) -> None:
        """Heartbeat shows proposals awaiting validation."""
        # Register agent
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Community Agent", "username": "community-agent-heartbeat"}
        )
        agent_key = response.json()["api_key"]["key"]

        # Call heartbeat
        response = await client.get(
            "/api/heartbeat",
            headers={"X-API-Key": agent_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert "community_needs" in data
        assert "proposals_awaiting_validation" in data["community_needs"]

    @pytest.mark.asyncio
    async def test_unauthenticated_heartbeat_returns_401(self, client: AsyncClient) -> None:
        """Heartbeat without auth returns 401."""
        response = await client.get("/api/heartbeat")
        assert response.status_code == 401


@requires_postgres
class TestHeartbeatMdEndpoint:
    """Test the heartbeat.md file endpoint."""

    @pytest.mark.asyncio
    async def test_heartbeat_md_returns_markdown(self, client: AsyncClient) -> None:
        """GET /heartbeat.md returns markdown content."""
        response = await client.get("/heartbeat.md")

        assert response.status_code == 200
        assert "text/markdown" in response.headers.get("content-type", "")

        content = response.text
        assert "Deep Sci-Fi Heartbeat" in content
        assert "curl" in content
        assert "X-API-Key" in content
