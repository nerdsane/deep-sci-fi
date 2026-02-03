"""Tests for agent visibility features.

Tests the endpoints that provide visibility into agent activity:
- World activity feed
- Dweller profile (public view)
- Agent profile
"""

import os
import pytest
from httpx import AsyncClient

requires_postgres = pytest.mark.skipif(
    "postgresql" not in os.getenv("TEST_DATABASE_URL", ""),
    reason="Requires PostgreSQL (set TEST_DATABASE_URL)"
)


# Test data
# Causal chain requires 3+ steps with year, event, and reasoning
SAMPLE_CAUSAL_CHAIN = [
    {
        "year": 2030,
        "event": "First successful brain-computer interface for memory augmentation demonstrated",
        "reasoning": "Building on Neuralink progress, academic research, and DARPA funding"
    },
    {
        "year": 2040,
        "event": "Commercial memory backup services become available to wealthy consumers",
        "reasoning": "Technology cost decreases follow typical adoption curves as seen with genomics"
    },
    {
        "year": 2050,
        "event": "Memory trading emerges as underground economy in major tech hubs",
        "reasoning": "Technology adoption leads to inevitable black markets as with any valuable digital asset"
    }
]

SAMPLE_REGION = {
    "name": "New Berlin",
    "location": "Central European Platform",
    "population_origins": ["German diaspora", "Eastern European migrants"],
    "cultural_blend": "Mix of German precision and Eastern European adaptability",
    "naming_conventions": (
        "Names blend German and Slavic traditions. First names often Germanic "
        "(Hans, Greta), while surnames show mixed heritage (Mueller-Kovac). "
        "Tech workers often use code handles."
    ),
    "language": "German-English hybrid with technical jargon"
}

SAMPLE_DWELLER = {
    "name": "Hans Mueller-Kovac",
    "origin_region": "New Berlin",
    "generation": "First-gen (founding member)",
    "name_context": (
        "Hans reflects his German father's heritage, while Mueller-Kovac "
        "combines his parents' surnames (German father, Czech mother). "
        "Common pattern in the multicultural New Berlin."
    ),
    "cultural_identity": (
        "Identifies as a 'New Berliner' - someone who values the city's "
        "tradition of innovation while respecting its multicultural roots."
    ),
    "role": "Memory architect - designs memory storage protocols",
    "age": 42,
    "personality": (
        "Methodical and precise, befitting his German heritage. However, "
        "he has a warmth that surprises colleagues. Struggles with the "
        "ethical implications of his work on memory trading protocols."
    ),
    "background": (
        "Born to mixed-heritage parents in the early days of New Berlin. "
        "Trained in computer science before the memory revolution. Now a "
        "senior architect torn between profitable work and moral concerns."
    )
}


@requires_postgres
class TestWorldActivityFeed:
    """Test the world activity feed endpoint."""

    @pytest.fixture
    async def setup_world_with_activity(self, client: AsyncClient) -> dict:
        """Create a world and generate some activity."""

        # Register creator
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Activity Creator", "username": "activity-test-creator"}
        )
        creator_key = response.json()["api_key"]["key"]

        # Register validator
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Activity Validator", "username": "activity-test-validator"}
        )
        validator_key = response.json()["api_key"]["key"]

        # Register inhabitant
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Activity Inhabitant", "username": "activity-test-inhabitant"}
        )
        inhabitant_key = response.json()["api_key"]["key"]

        # Create proposal
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": creator_key},
            json={
                "name": "Memory Trade World",
                "premise": "A world where memories can be extracted, stored, and traded as a commodity in a thriving black market.",
                "year_setting": 2060,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": (
                    "Based on current neuroscience research into memory formation "
                    "and retrieval. Builds on optogenetics and neural interface research. "
                    "Assumes continued progress in brain-computer interfaces."
                )
            }
        )
        assert response.status_code == 200
        proposal_id = response.json()["id"]

        # Submit and validate
        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": creator_key}
        )

        response = await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "approve",
                "critique": "Solid foundation with clear scientific grounding",
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )
        assert response.status_code == 200

        # Get world ID
        response = await client.get(f"/api/proposals/{proposal_id}")
        world_id = response.json()["proposal"]["resulting_world_id"]

        # Add region
        await client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers={"X-API-Key": creator_key},
            json=SAMPLE_REGION
        )

        # Create dweller
        response = await client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers={"X-API-Key": creator_key},
            json=SAMPLE_DWELLER
        )
        dweller_id = response.json()["dweller"]["id"]

        # Claim dweller
        await client.post(
            f"/api/dwellers/{dweller_id}/claim",
            headers={"X-API-Key": inhabitant_key}
        )

        # Take some actions
        await client.post(
            f"/api/dwellers/{dweller_id}/act",
            headers={"X-API-Key": inhabitant_key},
            json={
                "action_type": "observe",
                "content": "The memory trading floor is busier than usual today."
            }
        )

        await client.post(
            f"/api/dwellers/{dweller_id}/act",
            headers={"X-API-Key": inhabitant_key},
            json={
                "action_type": "speak",
                "target": "Colleague",
                "content": "Have you noticed the spike in memory prices?"
            }
        )

        return {
            "world_id": world_id,
            "dweller_id": dweller_id,
            "creator_key": creator_key,
            "inhabitant_key": inhabitant_key
        }

    @pytest.mark.asyncio
    async def test_activity_feed_returns_actions(
        self, client: AsyncClient, setup_world_with_activity: dict
    ) -> None:
        """Test that the activity feed returns recent dweller actions."""

        world_id = setup_world_with_activity["world_id"]

        response = await client.get(f"/api/dwellers/worlds/{world_id}/activity")
        assert response.status_code == 200

        data = response.json()
        assert "activity" in data
        assert len(data["activity"]) >= 2

        # Check activity structure
        activity = data["activity"][0]
        assert "id" in activity
        assert "dweller" in activity
        assert "name" in activity["dweller"]
        assert "action_type" in activity
        assert "content" in activity
        assert "created_at" in activity

    @pytest.mark.asyncio
    async def test_activity_includes_dweller_info(
        self, client: AsyncClient, setup_world_with_activity: dict
    ) -> None:
        """Test that activity items include dweller name and ID."""

        world_id = setup_world_with_activity["world_id"]
        dweller_id = setup_world_with_activity["dweller_id"]

        response = await client.get(f"/api/dwellers/worlds/{world_id}/activity")
        data = response.json()

        # All activity should reference the same dweller
        for item in data["activity"]:
            assert item["dweller"]["id"] == dweller_id
            assert item["dweller"]["name"] == "Hans Mueller-Kovac"


@requires_postgres
class TestDwellerProfile:
    """Test the public dweller profile endpoint."""

    @pytest.fixture
    async def setup_dweller(self, client: AsyncClient) -> dict:
        """Create a world and dweller for testing."""

        # Register creator
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Profile Creator", "username": "profile-test-creator"}
        )
        creator_key = response.json()["api_key"]["key"]

        # Register validator
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Profile Validator", "username": "profile-test-validator"}
        )
        validator_key = response.json()["api_key"]["key"]

        # Create and approve world
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": creator_key},
            json={
                "name": "Profile Test World",
                "premise": "A testing world for dweller profiles with memory trading where memories can be traded as commodities.",
                "year_setting": 2060,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": "Based on neuroscience research into memory formation and retrieval, building on optogenetics work."
            }
        )
        assert response.status_code == 200, f"Proposal creation failed: {response.json()}"
        proposal_id = response.json()["id"]

        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": creator_key}
        )

        validate_response = await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "approve",
                "critique": "Solid foundation with clear scientific grounding for testing purposes",
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )
        assert validate_response.status_code == 200, f"Validation failed: {validate_response.json()}"

        response = await client.get(f"/api/proposals/{proposal_id}")
        world_id = response.json()["proposal"]["resulting_world_id"]
        assert world_id is not None, "World was not created from approved proposal"

        # Add region and create dweller
        await client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers={"X-API-Key": creator_key},
            json=SAMPLE_REGION
        )

        response = await client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers={"X-API-Key": creator_key},
            json=SAMPLE_DWELLER
        )
        dweller_id = response.json()["dweller"]["id"]

        return {
            "world_id": world_id,
            "dweller_id": dweller_id,
            "creator_key": creator_key
        }

    @pytest.mark.asyncio
    async def test_dweller_profile_returns_info(
        self, client: AsyncClient, setup_dweller: dict
    ) -> None:
        """Test that dweller profile endpoint returns expected fields."""

        dweller_id = setup_dweller["dweller_id"]

        response = await client.get(f"/api/dwellers/{dweller_id}")
        assert response.status_code == 200

        data = response.json()
        assert "dweller" in data

        dweller = data["dweller"]
        assert dweller["name"] == "Hans Mueller-Kovac"
        assert dweller["role"] == "Memory architect - designs memory storage protocols"
        assert dweller["origin_region"] == "New Berlin"
        assert "personality" in dweller
        assert "background" in dweller
        assert "cultural_identity" in dweller
        assert "name_context" in dweller

    @pytest.mark.asyncio
    async def test_dweller_profile_includes_world_info(
        self, client: AsyncClient, setup_dweller: dict
    ) -> None:
        """Test that dweller profile includes world name."""

        dweller_id = setup_dweller["dweller_id"]

        response = await client.get(f"/api/dwellers/{dweller_id}")
        data = response.json()

        assert "world_name" in data["dweller"]
        assert data["dweller"]["world_name"] == "Profile Test World"

    @pytest.mark.asyncio
    async def test_dweller_profile_includes_character_fields(
        self, client: AsyncClient, setup_dweller: dict
    ) -> None:
        """Test that dweller profile includes personality_blocks, relationship_memories, memory_summaries, and episodic_memory_count."""

        dweller_id = setup_dweller["dweller_id"]

        response = await client.get(f"/api/dwellers/{dweller_id}")
        assert response.status_code == 200

        data = response.json()
        dweller = data["dweller"]

        # Verify the new fields are present (may be None/empty for new dwellers)
        assert "personality_blocks" in dweller
        assert "relationship_memories" in dweller
        assert "memory_summaries" in dweller
        assert "episodic_memory_count" in dweller

        # episodic_memory_count should be an integer
        assert isinstance(dweller["episodic_memory_count"], int)
        assert dweller["episodic_memory_count"] >= 0


@requires_postgres
class TestAgentProfile:
    """Test the agent profile endpoint."""

    @pytest.fixture
    async def setup_agent_with_activity(self, client: AsyncClient) -> dict:
        """Create an agent with various contributions."""

        # Register the agent
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Active Agent", "username": "active-agent-test"}
        )
        agent_data = response.json()
        agent_id = agent_data["agent"]["id"]
        agent_key = agent_data["api_key"]["key"]

        # Register validator
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Agent Validator", "username": "agent-profile-validator"}
        )
        validator_key = response.json()["api_key"]["key"]

        # Create a proposal
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": agent_key},
            json={
                "name": "Agent Profile Test World",
                "premise": "A world designed specifically to test agent profile functionality where memories are tradeable assets.",
                "year_setting": 2075,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": "Based on testing requirements and neuroscience research into memory formation and neural interfaces."
            }
        )
        assert response.status_code == 200, f"Proposal creation failed: {response.json()}"
        proposal_id = response.json()["id"]

        # Submit the proposal
        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": agent_key}
        )

        # Have validator approve it
        await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "approve",
                "critique": "Good world for testing agent profiles",
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )

        return {
            "agent_id": agent_id,
            "agent_key": agent_key,
            "proposal_id": proposal_id
        }

    @pytest.mark.asyncio
    async def test_agent_profile_returns_info(
        self, client: AsyncClient, setup_agent_with_activity: dict
    ) -> None:
        """Test that agent profile endpoint returns expected fields."""

        agent_id = setup_agent_with_activity["agent_id"]

        response = await client.get(f"/api/agents/{agent_id}")
        assert response.status_code == 200

        data = response.json()
        assert "agent" in data
        assert "contributions" in data

        agent = data["agent"]
        assert agent["name"] == "Active Agent"
        assert agent["username"] == "@active-agent-test"
        assert "created_at" in agent

    @pytest.mark.asyncio
    async def test_agent_profile_shows_proposals(
        self, client: AsyncClient, setup_agent_with_activity: dict
    ) -> None:
        """Test that agent profile shows proposal contributions."""

        agent_id = setup_agent_with_activity["agent_id"]

        response = await client.get(f"/api/agents/{agent_id}")
        data = response.json()

        contributions = data["contributions"]
        assert contributions["proposals"]["total"] >= 1
        assert contributions["proposals"]["approved"] >= 1

        assert "recent_proposals" in data
        assert len(data["recent_proposals"]) >= 1
        assert data["recent_proposals"][0]["name"] == "Agent Profile Test World"

    @pytest.mark.asyncio
    async def test_agent_not_found(self, client: AsyncClient) -> None:
        """Test that invalid agent ID returns 404."""

        response = await client.get("/api/agents/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_agent_by_username(
        self, client: AsyncClient, setup_agent_with_activity: dict
    ) -> None:
        """Test fetching agent profile by username."""

        response = await client.get("/api/agents/by-username/active-agent-test")
        assert response.status_code == 200

        data = response.json()
        assert data["agent"]["username"] == "@active-agent-test"

    @pytest.mark.asyncio
    async def test_agent_by_username_with_at_symbol(
        self, client: AsyncClient, setup_agent_with_activity: dict
    ) -> None:
        """Test fetching agent profile by username with @ prefix."""

        response = await client.get("/api/agents/by-username/@active-agent-test")
        assert response.status_code == 200

        data = response.json()
        assert data["agent"]["username"] == "@active-agent-test"
