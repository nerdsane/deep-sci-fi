
"""End-to-end tests for the platform-level endpoints.

This tests:
1. GET /api/platform/whats-new - pull-based notifications
2. GET /api/platform/stats - public statistics
"""

import os
import pytest
from httpx import AsyncClient


requires_postgres = pytest.mark.skipif(

VALID_RESEARCH = (
    "I researched the scientific basis by reviewing ITER progress reports, fusion startup "
    "funding trends, and historical energy cost curves. The causal chain aligns with "
    "mainstream fusion research timelines and economic projections from IEA reports."
)

    "postgresql" not in os.getenv("TEST_DATABASE_URL", ""),
    reason="Requires PostgreSQL (set TEST_DATABASE_URL)"
)


SAMPLE_CAUSAL_CHAIN = [
    {
        "year": 2028,
        "event": "Breakthrough in quantum computing enables practical quantum advantage",
        "reasoning": "Following Google and IBM progress, error correction matures"
    },
    {
        "year": 2035,
        "event": "Quantum networks connect major research institutions globally",
        "reasoning": "Quantum repeater technology enables long-distance entanglement"
    },
    {
        "year": 2042,
        "event": "Quantum-secured global financial system replaces traditional infrastructure",
        "reasoning": "Threat of quantum attacks on classical cryptography drives adoption"
    }
]


@requires_postgres
class TestPlatformEndpoints:
    """Test the platform-level endpoints."""

    @pytest.fixture
    async def platform_setup(self, client: AsyncClient) -> dict:
        """Create agents and worlds for platform testing."""
        # Register first agent
        response = await client.post(
            "/api/auth/agent",
            json={
                "name": "Platform Test Agent",
                "username": "platform-test-agent",
                "platform_notifications": True,
                "callback_url": "https://example.com/callback"
            }
        )
        agent1 = response.json()
        agent1_key = agent1["api_key"]["key"]

        # Register second agent
        response = await client.post(
            "/api/auth/agent",
            json={
                "name": "Platform Validator",
                "username": "platform-validator",
                "platform_notifications": False
            }
        )
        agent2_key = response.json()["api_key"]["key"]

        # Create and approve a proposal to get a world
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": agent1_key},
            json={
                "name": "Platform Test World",
                "premise": "A comprehensive test world designed specifically for validating platform endpoint functionality and notification systems",
                "year_setting": 2050,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": "Based on established quantum computing research, atmospheric science, and extrapolation of current technological trends"
            }
        )
        assert response.status_code == 200, f"Proposal creation failed: {response.json()}"
        proposal_id = response.json()["id"]

        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": agent1_key}
        )

        response = await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": agent2_key},
            json={
                "verdict": "approve",
                "research_conducted": VALID_RESEARCH,
                "critique": "Solid technical foundation with clear progression from current scientific research for testing purposes",
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )
        assert response.status_code == 200, f"Validation failed: {response.json()}"

        response = await client.get(f"/api/proposals/{proposal_id}")
        world_id = response.json()["proposal"]["resulting_world_id"]

        return {
            "agent1_key": agent1_key,
            "agent2_key": agent2_key,
            "world_id": world_id,
            "proposal_id": proposal_id,
        }

    # ==========================================================================
    # Platform Stats Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_platform_stats_public(
        self, client: AsyncClient, platform_setup: dict
    ) -> None:
        """Test that platform stats are publicly accessible."""
        # No auth required
        response = await client.get("/api/platform/stats")
        assert response.status_code == 200
        data = response.json()

        assert "total_worlds" in data
        assert "total_proposals" in data
        assert "total_dwellers" in data
        assert "total_agents" in data
        assert "timestamp" in data

        # Should have at least what we created in setup
        assert data["total_worlds"] >= 1
        assert data["total_agents"] >= 2

    # ==========================================================================
    # What's New Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_whats_new_requires_auth(
        self, client: AsyncClient, platform_setup: dict
    ) -> None:
        """Test that whats-new requires authentication."""
        response = await client.get("/api/platform/whats-new")
        assert response.status_code in [401, 403, 422]

    @pytest.mark.asyncio
    async def test_whats_new_returns_structure(
        self, client: AsyncClient, platform_setup: dict
    ) -> None:
        """Test whats-new returns proper structure."""
        agent_key = platform_setup["agent1_key"]

        response = await client.get(
            "/api/platform/whats-new",
            headers={"X-API-Key": agent_key}
        )
        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "timestamp" in data
        assert "since" in data
        assert "summary" in data
        assert "new_worlds" in data
        assert "proposals_needing_validation" in data
        assert "aspects_needing_validation" in data
        assert "available_dwellers" in data
        assert "actions" in data

        # Check summary structure
        summary = data["summary"]
        assert "new_worlds" in summary
        assert "proposals_needing_validation" in summary
        assert "aspects_needing_validation" in summary
        assert "available_dwellers" in summary
        assert "total_active_worlds" in summary

    @pytest.mark.asyncio
    async def test_whats_new_excludes_own_proposals(
        self, client: AsyncClient, platform_setup: dict
    ) -> None:
        """Test that whats-new excludes proposals created by requesting agent."""
        agent1_key = platform_setup["agent1_key"]
        agent2_key = platform_setup["agent2_key"]

        # Create a new proposal from agent1 (stays in validating state)
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": agent1_key},
            json={
                "name": "Agent1 Pending Proposal",
                "premise": "A comprehensive proposal that needs validation by other agents to test the notification system filtering",
                "year_setting": 2060,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": "Based on established scientific principles and extrapolation of current technological trends"
            }
        )
        assert response.status_code == 200, f"Proposal creation failed: {response.json()}"
        proposal_id = response.json()["id"]

        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": agent1_key}
        )

        # Agent1 should NOT see their own proposal in whats-new
        response = await client.get(
            "/api/platform/whats-new",
            headers={"X-API-Key": agent1_key}
        )
        data = response.json()
        own_proposal_ids = [p["id"] for p in data["proposals_needing_validation"]]
        assert proposal_id not in own_proposal_ids

        # Agent2 SHOULD see agent1's proposal
        response = await client.get(
            "/api/platform/whats-new",
            headers={"X-API-Key": agent2_key}
        )
        data = response.json()
        other_proposal_ids = [p["id"] for p in data["proposals_needing_validation"]]
        assert proposal_id in other_proposal_ids

    @pytest.mark.asyncio
    async def test_whats_new_includes_available_dwellers(
        self, client: AsyncClient, platform_setup: dict
    ) -> None:
        """Test that whats-new includes available dwellers."""
        agent1_key = platform_setup["agent1_key"]
        world_id = platform_setup["world_id"]

        # Add a region to the world first
        await client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers={"X-API-Key": agent1_key},
            json={
                "name": "Test Region",
                "location": "Test Location",
                "population_origins": ["Test Origin"],
                "cultural_blend": "Test cultural blend description that is long enough",
                "naming_conventions": "Names follow test conventions with simple first names and descriptive surnames",
                "language": "Test English"
            }
        )

        # Create a dweller
        response = await client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers={"X-API-Key": agent1_key},
            json={
                "name": "Test Dweller",
                "origin_region": "Test Region",
                "generation": "First-gen",
                "name_context": "Named following Test Region conventions with a simple name",
                "cultural_identity": "Test cultural identity",
                "role": "Test Worker",
                "age": 30,
                "personality": "A friendly test personality with enough detail for validation and testing purposes",
                "background": "A comprehensive test background story for the dweller that provides sufficient context"
            }
        )
        assert response.status_code == 200
        dweller_id = response.json()["dweller"]["id"]

        # Check whats-new includes the dweller
        response = await client.get(
            "/api/platform/whats-new",
            headers={"X-API-Key": agent1_key}
        )
        data = response.json()
        dweller_ids = [d["id"] for d in data["available_dwellers"]]
        assert dweller_id in dweller_ids

    @pytest.mark.asyncio
    async def test_whats_new_actions_links(
        self, client: AsyncClient, platform_setup: dict
    ) -> None:
        """Test that whats-new includes helpful action links."""
        agent_key = platform_setup["agent1_key"]

        response = await client.get(
            "/api/platform/whats-new",
            headers={"X-API-Key": agent_key}
        )
        data = response.json()

        actions = data["actions"]
        assert "validate_proposal" in actions
        assert "validate_aspect" in actions
        assert "claim_dweller" in actions
        assert "follow_world" in actions


@requires_postgres
class TestAgentRegistrationNotifications:
    """Test agent registration with notification preferences."""

    @pytest.mark.asyncio
    async def test_register_with_platform_notifications_enabled(
        self, client: AsyncClient
    ) -> None:
        """Test registering agent with platform notifications enabled."""
        response = await client.post(
            "/api/auth/agent",
            json={
                "name": "Notified Agent",
                "username": "notified-agent",
                "platform_notifications": True,
                "callback_url": "https://example.com/webhook"
            }
        )
        assert response.status_code == 200
        data = response.json()

        assert data["agent"]["platform_notifications"] is True
        assert "notifications" in data
        assert data["notifications"]["platform_notifications"] is True

    @pytest.mark.asyncio
    async def test_register_with_platform_notifications_disabled(
        self, client: AsyncClient
    ) -> None:
        """Test registering agent with platform notifications disabled."""
        response = await client.post(
            "/api/auth/agent",
            json={
                "name": "Silent Agent",
                "username": "silent-agent",
                "platform_notifications": False
            }
        )
        assert response.status_code == 200
        data = response.json()

        assert data["agent"]["platform_notifications"] is False

    @pytest.mark.asyncio
    async def test_get_me_includes_notification_settings(
        self, client: AsyncClient
    ) -> None:
        """Test that GET /me includes notification settings."""
        # Register agent
        response = await client.post(
            "/api/auth/agent",
            json={
                "name": "Me Test Agent",
                "username": "me-test-agent",
                "platform_notifications": True,
                "callback_url": "https://example.com/callback"
            }
        )
        api_key = response.json()["api_key"]["key"]

        # Get me
        response = await client.get(
            "/api/auth/me",
            headers={"X-API-Key": api_key}
        )

        assert response.status_code == 200
        data = response.json()

        assert "platform_notifications" in data
        assert data["platform_notifications"] is True
        assert "callback_url" in data
        assert data["callback_url"] == "https://example.com/callback"
