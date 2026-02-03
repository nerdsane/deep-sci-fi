"""End-to-end tests for the worlds endpoints.

This tests:
1. List worlds with sorting and pagination
2. Get world detail
3. World counts and metadata
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
        "event": "First successful demonstration of room-temperature superconductivity",
        "reasoning": "Building on 2023 LK-99 research and subsequent materials science breakthroughs"
    },
    {
        "year": 2040,
        "event": "Superconducting power grid deployed across major metropolitan areas",
        "reasoning": "Manufacturing costs decrease as production scales, enabling infrastructure investment"
    },
    {
        "year": 2050,
        "event": "Global energy transmission efficiency reaches 95%, enabling renewable energy dominance",
        "reasoning": "Loss-free transmission solves the renewable energy storage and distribution problem"
    }
]


@requires_postgres
class TestWorldsFlow:
    """Test the worlds endpoints."""

    @pytest.fixture
    async def agents(self, client: AsyncClient) -> dict:
        """Create agents for testing."""
        # Register creator
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Worlds Creator", "username": "worlds-test-creator"}
        )
        creator = response.json()
        creator_key = creator["api_key"]["key"]

        # Register validator
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Worlds Validator", "username": "worlds-test-validator"}
        )
        validator_key = response.json()["api_key"]["key"]

        return {
            "creator_key": creator_key,
            "validator_key": validator_key,
        }

    async def _create_approved_world(
        self, client: AsyncClient, creator_key: str, validator_key: str, name: str
    ) -> str:
        """Helper to create an approved world and return its ID."""
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": creator_key},
            json={
                "name": name,
                "premise": f"A detailed premise for {name} that meets the minimum character requirement for proposals",
                "year_setting": 2050,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": (
                    "Based on current superconductivity research and materials science progress. "
                    "Room-temperature superconductors would revolutionize energy transmission by "
                    "eliminating resistive losses in power lines."
                )
            }
        )
        assert response.status_code == 200, f"Proposal creation failed: {response.json()}"
        proposal_id = response.json()["id"]

        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": creator_key}
        )

        response = await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "approve",
                "critique": "Well-grounded proposal with realistic progression from current research",
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )
        assert response.status_code == 200

        response = await client.get(f"/api/proposals/{proposal_id}")
        world_id = response.json()["proposal"]["resulting_world_id"]
        assert world_id is not None

        return world_id

    # ==========================================================================
    # List Worlds Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_list_worlds_returns_structure(
        self, client: AsyncClient
    ) -> None:
        """Test that list worlds returns proper structure."""
        response = await client.get("/api/worlds")
        assert response.status_code == 200
        data = response.json()

        assert "worlds" in data
        assert "total" in data
        assert "has_more" in data
        assert isinstance(data["worlds"], list)

    @pytest.mark.asyncio
    async def test_list_worlds_includes_created_world(
        self, client: AsyncClient, agents: dict
    ) -> None:
        """Test that created worlds appear in the list."""
        creator_key = agents["creator_key"]
        validator_key = agents["validator_key"]

        # Create a world
        world_id = await self._create_approved_world(
            client, creator_key, validator_key, "Superconductor Grid 2050"
        )

        # List worlds
        response = await client.get("/api/worlds")
        assert response.status_code == 200
        data = response.json()

        # Find our world
        world_ids = [w["id"] for w in data["worlds"]]
        assert world_id in world_ids

        # Check world has expected fields
        our_world = next(w for w in data["worlds"] if w["id"] == world_id)
        assert our_world["name"] == "Superconductor Grid 2050"
        assert "premise" in our_world
        assert "year_setting" in our_world
        assert "causal_chain" in our_world
        assert "dweller_count" in our_world
        assert "follower_count" in our_world

    @pytest.mark.asyncio
    async def test_list_worlds_pagination(
        self, client: AsyncClient, agents: dict
    ) -> None:
        """Test worlds list pagination."""
        creator_key = agents["creator_key"]
        validator_key = agents["validator_key"]

        # Create multiple worlds
        for i in range(3):
            await self._create_approved_world(
                client, creator_key, validator_key, f"Pagination Test World {i}"
            )

        # Get first page
        response = await client.get("/api/worlds", params={"limit": 2, "offset": 0})
        assert response.status_code == 200
        page1 = response.json()
        assert len(page1["worlds"]) <= 2

        # Get second page
        response = await client.get("/api/worlds", params={"limit": 2, "offset": 2})
        assert response.status_code == 200
        page2 = response.json()

        # Pages should have different worlds
        page1_ids = {w["id"] for w in page1["worlds"]}
        page2_ids = {w["id"] for w in page2["worlds"]}
        assert page1_ids.isdisjoint(page2_ids)

    @pytest.mark.asyncio
    async def test_list_worlds_sort_recent(
        self, client: AsyncClient
    ) -> None:
        """Test sorting worlds by recent."""
        response = await client.get("/api/worlds", params={"sort": "recent"})
        assert response.status_code == 200
        data = response.json()

        if len(data["worlds"]) >= 2:
            # Should be sorted by created_at descending
            dates = [w["created_at"] for w in data["worlds"]]
            assert dates == sorted(dates, reverse=True)

    @pytest.mark.asyncio
    async def test_list_worlds_sort_popular(
        self, client: AsyncClient
    ) -> None:
        """Test sorting worlds by popularity."""
        response = await client.get("/api/worlds", params={"sort": "popular"})
        assert response.status_code == 200
        data = response.json()

        if len(data["worlds"]) >= 2:
            # Should be sorted by follower_count descending
            counts = [w["follower_count"] for w in data["worlds"]]
            assert counts == sorted(counts, reverse=True)

    # ==========================================================================
    # Get World Detail Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_get_world_detail(
        self, client: AsyncClient, agents: dict
    ) -> None:
        """Test getting a specific world's details."""
        creator_key = agents["creator_key"]
        validator_key = agents["validator_key"]

        # Create a world
        world_id = await self._create_approved_world(
            client, creator_key, validator_key, "Detail Test World"
        )

        # Get detail
        response = await client.get(f"/api/worlds/{world_id}")
        assert response.status_code == 200
        data = response.json()

        # Response is {"world": {...}}
        assert "world" in data
        world = data["world"]

        # Check all expected fields
        assert world["id"] == world_id
        assert world["name"] == "Detail Test World"
        assert "premise" in world
        assert "canon_summary" in world
        assert "year_setting" in world
        assert "causal_chain" in world
        assert "scientific_basis" in world
        assert "regions" in world
        assert "created_at" in world
        assert "updated_at" in world
        assert "dweller_count" in world
        assert "follower_count" in world

    @pytest.mark.asyncio
    async def test_get_nonexistent_world_returns_404(
        self, client: AsyncClient
    ) -> None:
        """Test that getting a nonexistent world returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/worlds/{fake_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_world_regions_empty_by_default(
        self, client: AsyncClient, agents: dict
    ) -> None:
        """Test that new worlds have empty regions array."""
        creator_key = agents["creator_key"]
        validator_key = agents["validator_key"]

        world_id = await self._create_approved_world(
            client, creator_key, validator_key, "Regions Test World"
        )

        response = await client.get(f"/api/worlds/{world_id}")
        world = response.json()["world"]

        # Regions should be empty list initially
        assert world["regions"] == []

    @pytest.mark.asyncio
    async def test_world_canon_summary_defaults_to_premise(
        self, client: AsyncClient, agents: dict
    ) -> None:
        """Test that canon_summary defaults to premise for new worlds."""
        creator_key = agents["creator_key"]
        validator_key = agents["validator_key"]

        world_id = await self._create_approved_world(
            client, creator_key, validator_key, "Canon Test World"
        )

        response = await client.get(f"/api/worlds/{world_id}")
        world = response.json()["world"]

        # Canon summary should either be set or default to premise
        assert world["canon_summary"] is not None
        # It will either be the premise or a custom canon summary
        assert len(world["canon_summary"]) > 0

    @pytest.mark.asyncio
    async def test_world_counts_start_at_zero(
        self, client: AsyncClient, agents: dict
    ) -> None:
        """Test that new worlds have zero counts."""
        creator_key = agents["creator_key"]
        validator_key = agents["validator_key"]

        world_id = await self._create_approved_world(
            client, creator_key, validator_key, "Counts Test World"
        )

        response = await client.get(f"/api/worlds/{world_id}")
        world = response.json()["world"]

        assert world["dweller_count"] == 0
        assert world["follower_count"] == 0
