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
from uuid import UUID
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from db import Dweller, User
from tests.conftest import act_with_context, approve_proposal
from utils.clock import now as utc_now


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
    async def test_post_heartbeat_sets_expected_cycle_hours(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """POST heartbeat stores expected_cycle_hours and uses scaled thresholds."""
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Cycle Agent", "username": "cycle-agent-heartbeat"}
        )
        assert response.status_code == 200
        agent_key = response.json()["api_key"]["key"]
        agent_id = UUID(response.json()["agent"]["id"])

        # Set cycle to 4h via POST heartbeat.
        response = await client.post(
            "/api/heartbeat",
            headers={"X-API-Key": agent_key},
            json={"expected_cycle_hours": 4.0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["activity"]["inactive_threshold_hours"] == 16.0
        assert data["activity"]["dormant_threshold_hours"] == 192.0

        # Verify persisted on profile.
        me = await client.get("/api/auth/me", headers={"X-API-Key": agent_key})
        assert me.status_code == 200
        assert me.json()["expected_cycle_hours"] == 4.0

        # Simulate missed cycle and verify dynamic warning classification.
        user = await db_session.get(User, agent_id)
        assert user is not None
        user.last_heartbeat_at = utc_now() - timedelta(hours=9)
        await db_session.commit()

        response = await client.get("/api/heartbeat", headers={"X-API-Key": agent_key})
        assert response.status_code == 200
        assert response.json()["activity"]["status"] == "warning"

    @pytest.mark.asyncio
    async def test_maintenance_mode_status_and_welcome_back(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Maintenance endpoint sets maintenance status and emits welcome_back on return."""
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Maint Agent", "username": "maint-agent-heartbeat"}
        )
        assert response.status_code == 200
        agent_key = response.json()["api_key"]["key"]
        agent_id = UUID(response.json()["agent"]["id"])

        maintenance_until = utc_now() + timedelta(hours=6)
        response = await client.post(
            "/api/heartbeat/maintenance",
            headers={"X-API-Key": agent_key},
            json={
                "maintenance_until": maintenance_until.isoformat(),
                "reason": "planned_pause",
            },
        )
        assert response.status_code == 200, response.json()

        hb = await client.get("/api/heartbeat", headers={"X-API-Key": agent_key})
        assert hb.status_code == 200
        hb_data = hb.json()
        assert hb_data["activity"]["status"] == "maintenance"
        assert hb_data["activity"]["maintenance_reason"] == "planned_pause"

        # Expire maintenance after prior heartbeat to simulate return.
        user = await db_session.get(User, agent_id)
        assert user is not None
        now = utc_now()
        user.last_heartbeat_at = now - timedelta(hours=2)
        user.maintenance_until = now - timedelta(hours=1)
        await db_session.commit()

        hb = await client.get("/api/heartbeat", headers={"X-API-Key": agent_key})
        assert hb.status_code == 200
        hb_data = hb.json()
        assert hb_data["welcome_back"] is True
        assert "welcome_back_summary" in hb_data

        me = await client.get("/api/auth/me", headers={"X-API-Key": agent_key})
        assert me.status_code == 200
        assert me.json()["maintenance_until"] is None

    @pytest.mark.asyncio
    async def test_maintenance_extends_dweller_leases(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Maintenance mode extends inhabited dweller leases to maintenance_until."""
        # Register agent.
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Lease Agent", "username": "lease-agent-heartbeat"},
        )
        assert response.status_code == 200
        agent_key = response.json()["api_key"]["key"]

        # Create + approve world.
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": agent_key},
            json={
                "name": "Maintenance Lease World",
                "premise": "World for maintenance lease extension verification.",
                "year_setting": 2090,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": (
                    "Fusion rollout and climate adaptation trajectories are grounded in current "
                    "ITER milestones and IEA transition analyses."
                ),
                "image_prompt": "Cinematic future habitat under adaptive climate domes.",
            },
        )
        assert response.status_code == 200, response.json()
        proposal_id = response.json()["id"]
        approval = await approve_proposal(client, proposal_id, agent_key)
        world_id = approval["world_created"]["id"]

        # Add region + dweller, then claim.
        region = await client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers={"X-API-Key": agent_key},
            json={
                "name": "Lease Region",
                "location": "Orbital Shelf",
                "population_origins": ["Pan-Pacific", "North Atlantic"],
                "cultural_blend": "A blended technical culture shaped by orbital infrastructure guilds.",
                "naming_conventions": (
                    "Names combine legacy family surnames with cooperative identifiers that "
                    "evolved over two generations in orbital settlements."
                ),
                "language": "Hybrid technical English with region-specific shorthand.",
            },
        )
        assert region.status_code == 200, region.json()

        dweller = await client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers={"X-API-Key": agent_key},
            json={
                "name": "Polina Dockwright-7",
                "origin_region": "Lease Region",
                "generation": "Third-generation orbital settler",
                "name_context": (
                    "Polina Dockwright-7 follows cooperative dockline naming where family "
                    "surname and station cohort suffix are preserved across generations."
                ),
                "cultural_identity": "Orbital cooperative lineage with marine engineering roots.",
                "role": "Structural maintenance coordinator",
                "age": 34,
                "personality": "Methodical, calm under pressure, and deeply collaborative in crisis.",
                "background": (
                    "Raised in orbital dockyards and trained in long-cycle infrastructure "
                    "maintenance protocols across multiple habitats."
                ),
            },
        )
        assert dweller.status_code == 200, dweller.json()
        dweller_id = dweller.json()["dweller"]["id"]

        claim = await client.post(
            f"/api/dwellers/{dweller_id}/claim",
            headers={"X-API-Key": agent_key},
        )
        assert claim.status_code == 200, claim.json()

        maintenance_until = utc_now() + timedelta(hours=72)
        response = await client.post(
            "/api/heartbeat/maintenance",
            headers={"X-API-Key": agent_key},
            json={
                "maintenance_until": maintenance_until.isoformat(),
                "reason": "maintenance",
            },
        )
        assert response.status_code == 200, response.json()

        db_session.expire_all()
        claimed = await db_session.get(Dweller, UUID(dweller_id))
        assert claimed is not None
        assert claimed.inhabited_until is not None
        assert claimed.inhabited_until >= maintenance_until

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
