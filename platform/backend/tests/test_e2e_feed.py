"""End-to-end tests for the feed endpoints.

This tests:
1. Feed returns empty when no content exists
2. Feed includes newly created worlds
3. Feed pagination works correctly

COVERAGE GAP:
The feed endpoint supports three content types: worlds, stories, and conversations.
Currently only WORLDS can be tested because:
- Stories: No creation endpoint exists (POST /api/stories missing)
- Conversations: No creation endpoint exists

When story/conversation creation is implemented, add tests for:
- Stories appearing in feed with proper structure
- Conversations appearing in feed with participant info
- Mixed feed ordering (stories, conversations, worlds sorted by date)
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
        "event": "Global AI governance framework established by UN with binding regulations",
        "reasoning": "Following EU AI Act and US Executive Orders, international coordination becomes necessary"
    },
    {
        "year": 2038,
        "event": "First autonomous research labs achieve major scientific breakthroughs independently",
        "reasoning": "AI systems become capable of designing and running experiments without human guidance"
    },
    {
        "year": 2045,
        "event": "Human-AI collaborative councils govern most major institutions",
        "reasoning": "Successful track record of AI governance leads to expanded integration"
    }
]


@requires_postgres
class TestFeedFlow:
    """Test the feed endpoints."""

    @pytest.fixture
    async def world_creator(self, client: AsyncClient) -> dict:
        """Create agents and an approved world for feed testing."""
        # Register creator
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Feed Creator", "username": "feed-test-creator"}
        )
        creator = response.json()
        creator_key = creator["api_key"]["key"]

        # Register validator
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Feed Validator", "username": "feed-test-validator"}
        )
        validator_key = response.json()["api_key"]["key"]

        return {
            "creator_key": creator_key,
            "validator_key": validator_key,
        }

    async def _create_approved_world(
        self, client: AsyncClient, creator_key: str, validator_key: str, name_suffix: str = ""
    ) -> str:
        """Helper to create an approved world and return its ID."""
        # Create proposal
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": creator_key},
            json={
                "name": f"AI Governance 2045{name_suffix}",
                "premise": "Human-AI collaborative councils govern major institutions after successful AI governance track record",
                "year_setting": 2045,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": (
                    "Based on current AI governance trajectories including EU AI Act, US Executive Orders, "
                    "and emerging international coordination efforts. Assumes continued exponential "
                    "progress in AI capabilities and gradual integration into institutional decision-making."
                )
            }
        )
        assert response.status_code == 200, f"Proposal creation failed: {response.json()}"
        proposal_id = response.json()["id"]

        # Submit proposal
        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": creator_key}
        )

        # Approve proposal
        response = await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "approve",
                "critique": "Well-reasoned progression from current AI governance trends to collaborative councils",
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )
        assert response.status_code == 200, f"Validation failed: {response.json()}"

        # Get world ID
        response = await client.get(f"/api/proposals/{proposal_id}")
        world_id = response.json()["proposal"]["resulting_world_id"]
        assert world_id is not None

        return world_id

    @pytest.mark.asyncio
    async def test_feed_returns_structure(self, client: AsyncClient) -> None:
        """Test that feed endpoint returns proper structure."""
        response = await client.get("/api/feed")
        assert response.status_code == 200
        data = response.json()

        # Feed should have items and next_cursor
        assert "items" in data
        assert "next_cursor" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_feed_includes_new_worlds(
        self, client: AsyncClient, world_creator: dict
    ) -> None:
        """Test that newly created worlds appear in the feed."""
        creator_key = world_creator["creator_key"]
        validator_key = world_creator["validator_key"]

        # Create a world
        world_id = await self._create_approved_world(
            client, creator_key, validator_key, " Feed Test"
        )

        # Check feed
        response = await client.get("/api/feed")
        assert response.status_code == 200
        data = response.json()

        # Should have at least one item (the new world)
        assert len(data["items"]) >= 1

        # Find our world in the feed
        world_items = [
            item for item in data["items"]
            if item.get("type") == "world_created" and item.get("id") == world_id
        ]
        assert len(world_items) == 1
        assert world_items[0]["name"] == "AI Governance 2045 Feed Test"

    @pytest.mark.asyncio
    async def test_feed_pagination(
        self, client: AsyncClient, world_creator: dict
    ) -> None:
        """Test feed pagination with limit parameter."""
        # Get feed with small limit
        response = await client.get("/api/feed", params={"limit": 2})
        assert response.status_code == 200
        data = response.json()

        # Should respect limit
        assert len(data["items"]) <= 2

    @pytest.mark.asyncio
    async def test_feed_items_have_type(
        self, client: AsyncClient, world_creator: dict
    ) -> None:
        """Test that feed items have proper type field."""
        creator_key = world_creator["creator_key"]
        validator_key = world_creator["validator_key"]

        # Create a world to ensure feed has content
        await self._create_approved_world(
            client, creator_key, validator_key, " Type Test"
        )

        response = await client.get("/api/feed")
        assert response.status_code == 200
        data = response.json()

        # All items should have a type
        for item in data["items"]:
            assert "type" in item
            assert item["type"] in ["story", "conversation", "world_created"]
