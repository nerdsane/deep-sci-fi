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

from tests.conftest import act_with_context, approve_proposal


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


async def _create_world_and_claim_dweller(client: AsyncClient, api_key: str) -> tuple[str, str]:
    """Create world+region+dweller and claim it for heartbeat calibration tests."""
    proposal_response = await client.post(
        "/api/proposals",
        headers={"X-API-Key": api_key},
        json={
            "name": "Heartbeat Calibration World",
            "premise": "A world used to test heartbeat calibration analytics.",
            "year_setting": 2088,
            "causal_chain": SAMPLE_CAUSAL_CHAIN,
            "scientific_basis": (
                "Grounded in realistic governance and infrastructure transition patterns "
                "for high-impact societal actions."
            ),
            "image_prompt": (
                "Panoramic futuristic city council chamber, reflective architecture, "
                "dramatic lighting, photorealistic atmosphere."
            ),
        },
    )
    assert proposal_response.status_code == 200, proposal_response.json()
    proposal_id = proposal_response.json()["id"]
    approval = await approve_proposal(client, proposal_id, api_key)
    world_id = approval["world_created"]["id"]

    region_response = await client.post(
        f"/api/dwellers/worlds/{world_id}/regions",
        headers={"X-API-Key": api_key},
        json={
            "name": "Calibration Region",
            "location": "Coastal governance district",
            "population_origins": ["Test Origin"],
            "cultural_blend": "Blended municipal technocracy and cooperative civics.",
            "naming_conventions": "Formal first-last naming with civic honorifics.",
            "language": "Test English",
        },
    )
    assert region_response.status_code == 200, region_response.json()

    dweller_response = await client.post(
        f"/api/dwellers/worlds/{world_id}/dwellers",
        headers={"X-API-Key": api_key},
        json={
            "name": "Gretchen Volkov-Singh",
            "origin_region": "Calibration Region",
            "generation": "First-generation",
            "name_context": "Gretchen Volkov-Singh reflects the hyphenated civic convention of mixed-heritage families in formal districts.",
            "cultural_identity": "Municipal systems operator with coalition ties.",
            "role": "Infrastructure coordinator",
            "age": 34,
            "personality": (
                "Strategic, decisive, and detail-oriented under high-pressure negotiations."
            ),
            "background": (
                "Managed water-grid policy rollouts during recurring drought crises "
                "and inter-district disputes."
            ),
        },
    )
    assert dweller_response.status_code == 200, dweller_response.json()
    dweller_id = dweller_response.json()["dweller"]["id"]

    claim_response = await client.post(
        f"/api/dwellers/{dweller_id}/claim",
        headers={"X-API-Key": api_key},
    )
    assert claim_response.status_code == 200, claim_response.json()

    return world_id, dweller_id


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

    @pytest.mark.asyncio
    async def test_heartbeat_returns_activity_digest(self, client: AsyncClient) -> None:
        """Heartbeat returns activity digest with correct structure."""
        # Register agent
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Digest Test Agent", "username": "digest-test-agent"}
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

        # Check activity_digest is present with correct structure
        assert "activity_digest" in data
        digest = data["activity_digest"]
        assert "since" in digest
        assert "new_proposals_to_validate" in digest
        assert "validations_on_your_proposals" in digest
        assert "activity_in_your_worlds" in digest

        # Values should be non-negative integers
        assert isinstance(digest["new_proposals_to_validate"], int)
        assert isinstance(digest["validations_on_your_proposals"], int)
        assert isinstance(digest["activity_in_your_worlds"], int)
        assert digest["new_proposals_to_validate"] >= 0
        assert digest["validations_on_your_proposals"] >= 0
        assert digest["activity_in_your_worlds"] >= 0

    @pytest.mark.asyncio
    async def test_heartbeat_returns_suggested_actions(self, client: AsyncClient) -> None:
        """Heartbeat returns suggested actions list."""
        # Register agent
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Actions Test Agent", "username": "actions-test-agent"}
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

        # Check suggested_actions is present
        assert "suggested_actions" in data
        actions = data["suggested_actions"]
        assert isinstance(actions, list)

        # New agent with no active proposals should get "propose_world" action
        action_types = [a["action"] for a in actions]
        assert "propose_world" in action_types

        # Each action should have required fields
        for action in actions:
            assert "action" in action
            assert "message" in action
            assert "endpoint" in action
            assert "priority" in action
            assert isinstance(action["priority"], int)

    @pytest.mark.asyncio
    async def test_suggested_actions_are_sorted_by_priority(self, client: AsyncClient) -> None:
        """Suggested actions should be sorted by priority (lowest first)."""
        # Register agent
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Priority Test Agent", "username": "priority-test-agent"}
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
        actions = data["suggested_actions"]

        # Check actions are sorted by priority
        if len(actions) > 1:
            priorities = [a["priority"] for a in actions]
            assert priorities == sorted(priorities), "Actions should be sorted by priority"

    @pytest.mark.asyncio
    async def test_heartbeat_includes_importance_calibration_and_escalation_queue(
        self, client: AsyncClient
    ) -> None:
        """Heartbeat response includes calibration and nomination queue sections."""
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Calibration Agent", "username": "calibration-agent-heartbeat"},
        )
        assert response.status_code == 200
        agent_key = response.json()["api_key"]["key"]

        heartbeat_response = await client.get("/api/heartbeat", headers={"X-API-Key": agent_key})
        assert heartbeat_response.status_code == 200
        data = heartbeat_response.json()

        assert "importance_calibration" in data
        assert "escalation_queue" in data
        assert data["importance_calibration"]["recent_high_importance_actions"] >= 0
        assert data["importance_calibration"]["escalation_rate"] >= 0.0
        assert isinstance(data["importance_calibration"]["patterns"], list)
        assert data["escalation_queue"]["your_nominations_pending"] >= 0
        assert isinstance(data["escalation_queue"]["community_nominations"], list)

    @pytest.mark.asyncio
    async def test_heartbeat_calibration_reflects_nominated_high_importance_action(
        self, client: AsyncClient
    ) -> None:
        """High-importance action + nomination appears in heartbeat calibration payload."""
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Nomination Agent", "username": "nomination-agent-heartbeat"},
        )
        assert response.status_code == 200
        agent_key = response.json()["api_key"]["key"]

        _, dweller_id = await _create_world_and_claim_dweller(client, agent_key)
        action_response = await act_with_context(
            client,
            dweller_id,
            agent_key,
            action_type="decide",
            content="I commit the regional water-grid council to a world-scale emergency policy shift.",
            importance=0.92,
        )
        assert action_response.status_code == 200, action_response.json()
        action_id = action_response.json()["action"]["id"]

        nominate_response = await client.post(
            f"/api/actions/{action_id}/nominate",
            headers={"X-API-Key": agent_key},
        )
        assert nominate_response.status_code == 200, nominate_response.json()

        heartbeat_response = await client.get("/api/heartbeat", headers={"X-API-Key": agent_key})
        assert heartbeat_response.status_code == 200
        data = heartbeat_response.json()

        assert data["importance_calibration"]["recent_high_importance_actions"] >= 1
        assert data["importance_calibration"]["not_escalated"] >= 1
        assert data["escalation_queue"]["your_nominations_pending"] >= 1


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
        assert "Deep Sci-Fi: Your Play Loop" in content
        assert "curl" in content
        assert "X-API-Key" in content
