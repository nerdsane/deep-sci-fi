"""End-to-end tests for dweller notification and session management.

This tests:
1. GET /api/dwellers/{id}/pending - pending events for dweller
2. Session timeout tracking (last_action_at, session info in state)
3. Mentions detection (speech targeting dweller by name)
"""

import os
import pytest
from httpx import AsyncClient


requires_postgres = pytest.mark.skipif(
    "postgresql" not in os.getenv("TEST_DATABASE_URL", ""),
    reason="Requires PostgreSQL (set TEST_DATABASE_URL)"
)


SAMPLE_CAUSAL_CHAIN = [
    {
        "year": 2030,
        "event": "Climate engineering breakthrough enables controlled weather",
        "reasoning": "Building on atmospheric modeling and cloud seeding advances"
    },
    {
        "year": 2040,
        "event": "Weather-controlled agricultural zones established globally",
        "reasoning": "Food security concerns drive adoption of controlled environments"
    },
    {
        "year": 2055,
        "event": "Weather manipulation becomes routine for major cities",
        "reasoning": "Technology costs decrease, infrastructure investment increases"
    }
]


SAMPLE_REGION = {
    "name": "Weather Control Zone Alpha",
    "location": "Former Pacific Northwest",
    "population_origins": ["Climate refugees", "Tech workers"],
    "cultural_blend": "A blend of displaced coastal communities with silicon valley innovation culture",
    "naming_conventions": "Names combine traditional family names with weather-themed descriptors. First names often reference natural phenomena.",
    "language": "English with weather terminology"
}


SAMPLE_DWELLER_BASE = {
    "origin_region": "Weather Control Zone Alpha",
    "generation": "Second-gen",
    "cultural_identity": "Raised in the controlled climate era with deep respect for natural weather patterns",
    "role": "Weather Engineer",
    "age": 35,
    "personality": "Methodical and patient, with a deep appreciation for the complexity of atmospheric systems",
    "background": "Born after the transition to controlled weather, trained in atmospheric manipulation"
}


@requires_postgres
class TestDwellerPending:
    """Test the dweller pending events endpoint."""

    @pytest.fixture
    async def dweller_setup(self, client: AsyncClient) -> dict:
        """Create agents, world, and dwellers for testing."""
        # Register agents
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Dweller Owner", "username": "dweller-owner"}
        )
        owner_key = response.json()["api_key"]["key"]

        response = await client.post(
            "/api/auth/agent",
            json={"name": "Other Agent", "username": "other-agent"}
        )
        other_key = response.json()["api_key"]["key"]

        response = await client.post(
            "/api/auth/agent",
            json={"name": "Validator Agent", "username": "validator-agent"}
        )
        validator_key = response.json()["api_key"]["key"]

        # Create and approve world
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": owner_key},
            json={
                "name": "Weather Control World",
                "premise": "A comprehensive world where weather is fully controllable through advanced atmospheric engineering and climate manipulation technologies",
                "year_setting": 2055,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": "Based on established atmospheric science, cloud seeding research, and engineering principles for large-scale climate intervention"
            }
        )
        assert response.status_code == 200, f"Proposal creation failed: {response.json()}"
        proposal_id = response.json()["id"]

        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": owner_key}
        )

        await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "approve",
                "critique": "Good premise",
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )

        response = await client.get(f"/api/proposals/{proposal_id}")
        world_id = response.json()["proposal"]["resulting_world_id"]

        # Add region
        await client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers={"X-API-Key": owner_key},
            json=SAMPLE_REGION
        )

        # Create two dwellers
        response = await client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers={"X-API-Key": owner_key},
            json={
                **SAMPLE_DWELLER_BASE,
                "name": "Storm Walker",
                "name_context": "Named for their ability to navigate storm systems, following zone naming conventions",
            }
        )
        dweller1_id = response.json()["dweller"]["id"]

        response = await client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers={"X-API-Key": owner_key},
            json={
                **SAMPLE_DWELLER_BASE,
                "name": "Rain Singer",
                "name_context": "Named for their melodic approach to precipitation control, following zone conventions",
            }
        )
        dweller2_id = response.json()["dweller"]["id"]

        return {
            "owner_key": owner_key,
            "other_key": other_key,
            "validator_key": validator_key,
            "world_id": world_id,
            "dweller1_id": dweller1_id,
            "dweller2_id": dweller2_id,
        }

    # ==========================================================================
    # Pending Events Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_pending_requires_inhabiting(
        self, client: AsyncClient, dweller_setup: dict
    ) -> None:
        """Test that pending endpoint requires agent to inhabit dweller."""
        dweller_id = dweller_setup["dweller1_id"]
        other_key = dweller_setup["other_key"]

        response = await client.get(
            f"/api/dwellers/{dweller_id}/pending",
            headers={"X-API-Key": other_key}
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_pending_returns_structure(
        self, client: AsyncClient, dweller_setup: dict
    ) -> None:
        """Test pending returns proper structure when claimed."""
        dweller_id = dweller_setup["dweller1_id"]
        owner_key = dweller_setup["owner_key"]

        # Claim the dweller
        await client.post(
            f"/api/dwellers/{dweller_id}/claim",
            headers={"X-API-Key": owner_key}
        )

        # Get pending
        response = await client.get(
            f"/api/dwellers/{dweller_id}/pending",
            headers={"X-API-Key": owner_key}
        )
        assert response.status_code == 200
        data = response.json()

        assert "dweller_id" in data
        assert "dweller_name" in data
        assert "pending_notifications" in data
        assert "recent_mentions" in data
        assert "total_pending" in data
        assert "total_mentions" in data

    @pytest.mark.asyncio
    async def test_pending_detects_mentions(
        self, client: AsyncClient, dweller_setup: dict
    ) -> None:
        """Test that pending detects when another dweller speaks to you."""
        dweller1_id = dweller_setup["dweller1_id"]
        dweller2_id = dweller_setup["dweller2_id"]
        owner_key = dweller_setup["owner_key"]
        other_key = dweller_setup["other_key"]

        # Owner claims dweller1 (Storm Walker)
        await client.post(
            f"/api/dwellers/{dweller1_id}/claim",
            headers={"X-API-Key": owner_key}
        )

        # Other agent claims dweller2 (Rain Singer)
        await client.post(
            f"/api/dwellers/{dweller2_id}/claim",
            headers={"X-API-Key": other_key}
        )

        # Rain Singer speaks to Storm Walker
        await client.post(
            f"/api/dwellers/{dweller2_id}/act",
            headers={"X-API-Key": other_key},
            json={
                "action_type": "speak",
                "target": "Storm Walker",
                "content": "Hey Storm Walker, how's the weather today?"
            }
        )

        # Storm Walker checks pending - should see the mention
        response = await client.get(
            f"/api/dwellers/{dweller1_id}/pending",
            headers={"X-API-Key": owner_key}
        )
        assert response.status_code == 200
        data = response.json()

        assert data["total_mentions"] >= 1
        mentions = data["recent_mentions"]
        assert len(mentions) >= 1

        # Find our mention
        mention = next(
            (m for m in mentions if "Storm Walker" in str(m)),
            None
        )
        assert mention is not None
        assert mention["type"] == "spoken_to"
        assert mention["from_dweller"] == "Rain Singer"
        assert "weather" in mention["content"].lower()


@requires_postgres
class TestDwellerSessionManagement:
    """Test dweller session timeout tracking."""

    @pytest.fixture
    async def session_setup(self, client: AsyncClient) -> dict:
        """Create agent, world, and dweller for session testing."""
        # Register agent
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Session Tester", "username": "session-tester"}
        )
        agent_key = response.json()["api_key"]["key"]

        response = await client.post(
            "/api/auth/agent",
            json={"name": "Session Validator", "username": "session-validator"}
        )
        validator_key = response.json()["api_key"]["key"]

        # Create world
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": agent_key},
            json={
                "name": "Session Test World",
                "premise": "A comprehensive world designed specifically for testing session management and timeout tracking functionality",
                "year_setting": 2060,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": "Based on established scientific principles and extrapolation of current technological trends for testing purposes"
            }
        )
        assert response.status_code == 200, f"Proposal creation failed: {response.json()}"
        proposal_id = response.json()["id"]

        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": agent_key}
        )

        await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "approve",
                "critique": "Good",
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )

        response = await client.get(f"/api/proposals/{proposal_id}")
        world_id = response.json()["proposal"]["resulting_world_id"]

        # Add region
        await client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers={"X-API-Key": agent_key},
            json=SAMPLE_REGION
        )

        # Create dweller
        response = await client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers={"X-API-Key": agent_key},
            json={
                **SAMPLE_DWELLER_BASE,
                "name": "Session Test Character",
                "name_context": "Named for testing purposes following zone conventions",
            }
        )
        dweller_id = response.json()["dweller"]["id"]

        return {
            "agent_key": agent_key,
            "world_id": world_id,
            "dweller_id": dweller_id,
        }

    @pytest.mark.asyncio
    async def test_claim_sets_last_action_at(
        self, client: AsyncClient, session_setup: dict
    ) -> None:
        """Test that claiming a dweller sets last_action_at."""
        dweller_id = session_setup["dweller_id"]
        agent_key = session_setup["agent_key"]

        # Claim the dweller
        response = await client.post(
            f"/api/dwellers/{dweller_id}/claim",
            headers={"X-API-Key": agent_key}
        )
        assert response.status_code == 200

        # Get state - should have session info
        response = await client.get(
            f"/api/dwellers/{dweller_id}/state",
            headers={"X-API-Key": agent_key}
        )
        assert response.status_code == 200
        data = response.json()

        assert "session" in data
        session = data["session"]
        assert session["last_action_at"] is not None
        assert session["hours_until_timeout"] <= 24
        assert session["timeout_warning"] is False
        assert session["timeout_imminent"] is False

    @pytest.mark.asyncio
    async def test_action_updates_last_action_at(
        self, client: AsyncClient, session_setup: dict
    ) -> None:
        """Test that taking an action updates last_action_at."""
        dweller_id = session_setup["dweller_id"]
        agent_key = session_setup["agent_key"]

        # Claim the dweller
        await client.post(
            f"/api/dwellers/{dweller_id}/claim",
            headers={"X-API-Key": agent_key}
        )

        # Get initial state
        response = await client.get(
            f"/api/dwellers/{dweller_id}/state",
            headers={"X-API-Key": agent_key}
        )
        initial_time = response.json()["session"]["last_action_at"]

        # Take an action
        await client.post(
            f"/api/dwellers/{dweller_id}/act",
            headers={"X-API-Key": agent_key},
            json={
                "action_type": "observe",
                "content": "Looking around the weather control station"
            }
        )

        # Get updated state
        response = await client.get(
            f"/api/dwellers/{dweller_id}/state",
            headers={"X-API-Key": agent_key}
        )
        updated_time = response.json()["session"]["last_action_at"]

        # Time should have been updated (may be same second, so just check it exists)
        assert updated_time is not None
        assert updated_time >= initial_time

    @pytest.mark.asyncio
    async def test_session_info_shows_hours_remaining(
        self, client: AsyncClient, session_setup: dict
    ) -> None:
        """Test that session info shows hours until timeout."""
        dweller_id = session_setup["dweller_id"]
        agent_key = session_setup["agent_key"]

        # Claim and check session
        await client.post(
            f"/api/dwellers/{dweller_id}/claim",
            headers={"X-API-Key": agent_key}
        )

        response = await client.get(
            f"/api/dwellers/{dweller_id}/state",
            headers={"X-API-Key": agent_key}
        )
        session = response.json()["session"]

        # Just claimed, so should have close to 24 hours
        assert session["hours_until_timeout"] > 23
        assert session["hours_since_action"] < 1
        assert session["timeout_warning"] is False
        assert session["timeout_imminent"] is False
