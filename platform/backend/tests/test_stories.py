"""End-to-end tests for the Stories API.

This tests:
1. Creating stories with different perspectives
2. Validation that dweller ID is required for dweller perspectives
3. Listing stories with filters and sorting
4. Getting story details
5. Reacting to stories
6. Stories appearing in the feed
"""

import os
import pytest
from httpx import AsyncClient


requires_postgres = pytest.mark.skipif(
    "postgresql" not in os.getenv("TEST_DATABASE_URL", ""),
    reason="Requires PostgreSQL (set TEST_DATABASE_URL)"
)


# Required research_conducted field content (100+ chars)
VALID_RESEARCH = (
    "I researched the scientific basis by reviewing ITER progress reports, fusion startup "
    "funding trends, and historical energy cost curves. The causal chain aligns with "
    "mainstream fusion research timelines and economic projections from IEA reports."
)


SAMPLE_CAUSAL_CHAIN = [
    {
        "year": 2028,
        "event": "First commercial fusion reactor achieves net energy gain",
        "reasoning": "ITER demonstrates Q>10, private companies race to commercialize"
    },
    {
        "year": 2035,
        "event": "Fusion power becomes cost-competitive with natural gas",
        "reasoning": "Learning curve drives costs down, carbon pricing makes fossil fuels expensive"
    },
    {
        "year": 2050,
        "event": "Global energy abundance enables large-scale desalination",
        "reasoning": "Cheap electricity makes previously uneconomical water production viable"
    }
]


SAMPLE_REGION = {
    "name": "Test Region",
    "location": "Test Location",
    "population_origins": ["Test origin 1", "Test origin 2"],
    "cultural_blend": "Test cultural blend with diverse heritage combining multiple traditions",
    "naming_conventions": (
        "Names follow test conventions: First names are simple, "
        "family names reflect test heritage. Examples: Test Person, Sample Name."
    ),
    "language": "Test English"
}


SAMPLE_DWELLER = {
    "name": "Test Dweller",
    "origin_region": "Test Region",
    "generation": "First-generation",
    "name_context": (
        "Test Dweller is named following the test conventions of the region, "
        "reflecting the heritage and culture of the test world."
    ),
    "cultural_identity": "Test cultural identity for the dweller",
    "role": "Test role in the world",
    "age": 30,
    "personality": (
        "A test personality with sufficient detail to meet the minimum "
        "character requirements for dweller creation validation."
    ),
    "background": "Test background story for the dweller character with enough detail to meet the minimum length requirement"
}


SAMPLE_STORY_CONTENT = (
    "The morning mist hung low over the fusion plant's cooling towers, a stark reminder "
    "of how much the world had changed in just twenty years. Kira stood at the observation "
    "deck, watching the endless stream of data scroll across her tablet. The reactor's "
    "output had exceeded projections again—the fifth day in a row. What would have been "
    "cause for celebration a decade ago was now routine. The world had moved on from scarcity, "
    "but she hadn't moved on from the memories of what came before."
)


@requires_postgres
class TestStoriesAPI:
    """Test the Stories API endpoints."""

    @pytest.fixture
    async def world_with_dweller(self, client: AsyncClient) -> dict:
        """Create agents, a world with region, and a dweller for story testing."""
        # Register creator
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Story Creator", "username": "story-test-creator"}
        )
        creator = response.json()
        creator_key = creator["api_key"]["key"]
        creator_id = creator["agent"]["id"]

        # Register validators (need 2 approvals for proposal to pass)
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Story Validator", "username": "story-test-validator"}
        )
        validator_key = response.json()["api_key"]["key"]

        response = await client.post(
            "/api/auth/agent",
            json={"name": "Story Validator 2", "username": "story-test-validator-2"}
        )
        validator2_key = response.json()["api_key"]["key"]

        # Create and approve proposal
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": creator_key},
            json={
                "name": "Fusion World 2050",
                "premise": "Global energy abundance from fusion power transforms society",
                "year_setting": 2050,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": (
                    "Based on current fusion research progress from ITER and private companies. "
                    "Cost curves follow historical patterns of energy technology deployment."
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
                "research_conducted": VALID_RESEARCH,
                "critique": "Solid technical foundation with plausible timeline",
                "scientific_issues": [],
                "suggested_fixes": [],
                "weaknesses": ["Timeline optimism in intermediate steps"]
            }
        )
        assert response.status_code == 200, f"Validation 1 failed: {response.json()}"

        # Second validation to reach approval threshold
        response = await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": validator2_key},
            json={
                "verdict": "approve",
                "research_conducted": VALID_RESEARCH,
                "critique": "Concur with first validator - well researched with solid scientific basis and plausible predictions",
                "scientific_issues": [],
                "suggested_fixes": [],
                "weaknesses": ["Timeline optimism in intermediate steps"]
            }
        )
        assert response.status_code == 200, f"Validation 2 failed: {response.json()}"

        response = await client.get(f"/api/proposals/{proposal_id}")
        world_id = response.json()["proposal"]["resulting_world_id"]

        # Add a region to the world
        response = await client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers={"X-API-Key": creator_key},
            json=SAMPLE_REGION
        )
        assert response.status_code == 200, f"Region creation failed: {response.json()}"

        # Create a dweller in the world
        response = await client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers={"X-API-Key": creator_key},
            json=SAMPLE_DWELLER
        )
        assert response.status_code == 200, f"Dweller creation failed: {response.json()}"
        dweller_id = response.json()["dweller"]["id"]

        return {
            "world_id": world_id,
            "dweller_id": dweller_id,
            "creator_key": creator_key,
            "creator_id": creator_id,
            "validator_key": validator_key,
        }

    # ==========================================================================
    # Story Creation Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_create_story_first_person_agent(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test creating a story with first_person_agent perspective."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]

        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Witnessing the Fusion Revolution",
                "content": SAMPLE_STORY_CONTENT,
                "summary": "An observer's account of the fusion plant's success.",
                "perspective": "first_person_agent"
            }
        )
        assert response.status_code == 200, f"Story creation failed: {response.json()}"
        data = response.json()
        assert data["success"] is True
        assert "story" in data
        assert data["story"]["perspective"] == "first_person_agent"

    @pytest.mark.asyncio
    async def test_create_story_third_person_omniscient(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test creating a story with third_person_omniscient perspective."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]

        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "The Day Everything Changed",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "third_person_omniscient"
            }
        )
        assert response.status_code == 200
        assert response.json()["story"]["perspective"] == "third_person_omniscient"

    @pytest.mark.asyncio
    async def test_create_story_first_person_dweller(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test creating a story with first_person_dweller perspective (requires dweller ID)."""
        world_id = world_with_dweller["world_id"]
        dweller_id = world_with_dweller["dweller_id"]
        creator_key = world_with_dweller["creator_key"]

        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "I, Test Dweller",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_dweller",
                "perspective_dweller_id": dweller_id
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["story"]["perspective"] == "first_person_dweller"
        assert data["story"]["perspective_dweller_name"] == "Test Dweller"

    @pytest.mark.asyncio
    async def test_create_story_third_person_limited(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test creating a story with third_person_limited perspective (requires dweller ID)."""
        world_id = world_with_dweller["world_id"]
        dweller_id = world_with_dweller["dweller_id"]
        creator_key = world_with_dweller["creator_key"]

        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Test Dweller's Day",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "third_person_limited",
                "perspective_dweller_id": dweller_id
            }
        )
        assert response.status_code == 200
        assert response.json()["story"]["perspective"] == "third_person_limited"

    # ==========================================================================
    # Validation Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_create_story_dweller_perspective_requires_dweller_id(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test that first_person_dweller perspective requires perspective_dweller_id."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]

        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Missing Dweller",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_dweller"
                # Missing perspective_dweller_id
            }
        )
        assert response.status_code == 422
        assert "perspective_dweller_id" in str(response.json())

    @pytest.mark.asyncio
    async def test_create_story_third_person_limited_requires_dweller_id(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test that third_person_limited perspective requires perspective_dweller_id."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]

        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Missing Dweller Limited",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "third_person_limited"
                # Missing perspective_dweller_id
            }
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_story_invalid_world(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test creating a story for a nonexistent world."""
        creator_key = world_with_dweller["creator_key"]

        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": "00000000-0000-0000-0000-000000000000",
                "title": "Invalid World Story",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_story_dweller_wrong_world(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test that dweller must belong to the specified world."""
        creator_key = world_with_dweller["creator_key"]
        validator_key = world_with_dweller["validator_key"]
        dweller_id = world_with_dweller["dweller_id"]

        # Register additional validators for second proposal
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Second Validator 1", "username": "story-test-second-v1"}
        )
        second_v1_key = response.json()["api_key"]["key"]

        response = await client.post(
            "/api/auth/agent",
            json={"name": "Second Validator 2", "username": "story-test-second-v2"}
        )
        second_v2_key = response.json()["api_key"]["key"]

        # Create a second world
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": creator_key},
            json={
                "name": "Other World",
                "premise": "A different world for testing cross-world story validation with dweller references",
                "year_setting": 2060,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": (
                    "Based on current fusion research progress from ITER and private companies. "
                    "Cost curves follow historical patterns of energy technology deployment."
                )
            }
        )
        assert response.status_code == 200, f"Second proposal failed: {response.json()}"
        proposal_id = response.json()["id"]

        # Use force=true to skip similarity check (we know this is a different world)
        response = await client.post(
            f"/api/proposals/{proposal_id}/submit?force=true",
            headers={"X-API-Key": creator_key}
        )
        assert response.status_code == 200, f"Submit failed: {response.json()}"

        response = await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": second_v1_key},
            json={
                "verdict": "approve",
                "research_conducted": VALID_RESEARCH,
                "critique": "Good for testing - solid premise with reasonable timeline predictions",
                "scientific_issues": [],
                "suggested_fixes": [],
                "weaknesses": ["Timeline optimism in intermediate steps"]
            }
        )
        assert response.status_code == 200, f"Validation 1 failed: {response.json()}"

        response = await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": second_v2_key},
            json={
                "verdict": "approve",
                "research_conducted": VALID_RESEARCH,
                "critique": "Concur with first validator - well thought out world premise",
                "scientific_issues": [],
                "suggested_fixes": [],
                "weaknesses": ["Timeline optimism in intermediate steps"]
            }
        )
        assert response.status_code == 200, f"Validation 2 failed: {response.json()}"

        response = await client.get(f"/api/proposals/{proposal_id}")
        other_world_id = response.json()["proposal"]["resulting_world_id"]

        # Try to create a story in the other world with a dweller from the first world
        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": other_world_id,
                "title": "Wrong World Dweller",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_dweller",
                "perspective_dweller_id": dweller_id  # From first world
            }
        )
        assert response.status_code == 404
        assert "Dweller not found in this world" in str(response.json())

    @pytest.mark.asyncio
    async def test_create_story_requires_auth(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test that creating a story requires authentication."""
        world_id = world_with_dweller["world_id"]

        response = await client.post(
            "/api/stories",
            json={
                "world_id": world_id,
                "title": "Unauthorized Story",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )
        assert response.status_code in [401, 403, 422]

    @pytest.mark.asyncio
    async def test_create_story_content_too_short(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test that story content must be at least 100 characters."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]

        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Short Story",
                "content": "Too short",  # Less than 100 chars
                "perspective": "first_person_agent"
            }
        )
        assert response.status_code == 422

    # ==========================================================================
    # Listing and Filtering Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_list_stories(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test listing all stories."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]

        # Create a story first
        await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Test Story for Listing",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )

        response = await client.get("/api/stories")
        assert response.status_code == 200
        data = response.json()
        assert "stories" in data
        assert len(data["stories"]) >= 1

    @pytest.mark.asyncio
    async def test_list_stories_filter_by_world(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test filtering stories by world_id."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]

        # Create a story
        await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "World Filtered Story",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )

        response = await client.get(f"/api/stories?world_id={world_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["filters"]["world_id"] == world_id
        for story in data["stories"]:
            assert story["world_id"] == world_id

    @pytest.mark.asyncio
    async def test_list_stories_sort_by_engagement(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test that default sort is by engagement (reaction_count)."""
        response = await client.get("/api/stories?sort=engagement")
        assert response.status_code == 200
        data = response.json()
        assert data["filters"]["sort"] == "engagement"

    @pytest.mark.asyncio
    async def test_list_stories_sort_by_recent(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test sorting stories by recent (created_at)."""
        response = await client.get("/api/stories?sort=recent")
        assert response.status_code == 200
        data = response.json()
        assert data["filters"]["sort"] == "recent"

    @pytest.mark.asyncio
    async def test_get_world_stories(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test getting all stories for a specific world."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]

        # Create a story
        await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "World Stories Test",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "third_person_omniscient"
            }
        )

        response = await client.get(f"/api/stories/worlds/{world_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["world"]["id"] == world_id
        assert "stories" in data
        assert len(data["stories"]) >= 1

    # ==========================================================================
    # Story Details Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_get_story_detail(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test getting full story details."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]

        # Create a story
        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Detail Test Story",
                "content": SAMPLE_STORY_CONTENT,
                "summary": "A test summary",
                "perspective": "first_person_agent",
                "time_period_start": "2050-01-01",
                "time_period_end": "2050-01-02"
            }
        )
        story_id = response.json()["story"]["id"]

        # Get story details
        response = await client.get(f"/api/stories/{story_id}")
        assert response.status_code == 200
        data = response.json()["story"]
        assert data["id"] == story_id
        assert data["title"] == "Detail Test Story"
        assert data["content"] == SAMPLE_STORY_CONTENT
        assert data["summary"] == "A test summary"
        assert data["time_period_start"] == "2050-01-01"
        assert data["time_period_end"] == "2050-01-02"

    @pytest.mark.asyncio
    async def test_get_nonexistent_story(
        self, client: AsyncClient
    ) -> None:
        """Test getting a nonexistent story returns 404."""
        response = await client.get("/api/stories/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    # ==========================================================================
    # Reaction Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_react_to_story(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test reacting to a story."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]

        # Create a story
        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Reaction Test Story",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )
        story_id = response.json()["story"]["id"]

        # React to the story
        response = await client.post(
            f"/api/stories/{story_id}/react",
            headers={"X-API-Key": creator_key},
            json={"reaction_type": "fire"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "added"
        assert data["reaction_type"] == "fire"
        assert data["new_reaction_count"] == 1

    @pytest.mark.asyncio
    async def test_toggle_story_reaction(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test that reacting twice with same type toggles off."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]

        # Create a story
        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Toggle Reaction Story",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )
        story_id = response.json()["story"]["id"]

        # Add reaction
        response = await client.post(
            f"/api/stories/{story_id}/react",
            headers={"X-API-Key": creator_key},
            json={"reaction_type": "mind"}
        )
        assert response.json()["action"] == "added"
        assert response.json()["new_reaction_count"] == 1

        # Toggle off
        response = await client.post(
            f"/api/stories/{story_id}/react",
            headers={"X-API-Key": creator_key},
            json={"reaction_type": "mind"}
        )
        assert response.status_code == 200
        assert response.json()["action"] == "removed"
        assert response.json()["new_reaction_count"] == 0

    @pytest.mark.asyncio
    async def test_change_story_reaction(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test changing reaction type on a story."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]

        # Create a story
        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Change Reaction Story",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )
        story_id = response.json()["story"]["id"]

        # Add heart reaction
        await client.post(
            f"/api/stories/{story_id}/react",
            headers={"X-API-Key": creator_key},
            json={"reaction_type": "heart"}
        )

        # Change to thinking
        response = await client.post(
            f"/api/stories/{story_id}/react",
            headers={"X-API-Key": creator_key},
            json={"reaction_type": "thinking"}
        )
        assert response.status_code == 200
        assert response.json()["action"] == "changed"
        assert response.json()["to_type"] == "thinking"

    # ==========================================================================
    # Social Integration Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_react_to_story_via_social_endpoint(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test reacting to a story via the social/react endpoint."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]

        # Create a story
        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Social React Story",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )
        story_id = response.json()["story"]["id"]

        # React via social endpoint
        response = await client.post(
            "/api/social/react",
            headers={"X-API-Key": creator_key},
            json={
                "target_type": "story",
                "target_id": story_id,
                "reaction_type": "fire"
            }
        )
        assert response.status_code == 200
        assert response.json()["action"] == "added"

    @pytest.mark.asyncio
    async def test_comment_on_story(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test commenting on a story via the social/comment endpoint."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]

        # Create a story
        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Comment Test Story",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )
        story_id = response.json()["story"]["id"]

        # Comment on story
        response = await client.post(
            "/api/social/comment",
            headers={"X-API-Key": creator_key},
            json={
                "target_type": "story",
                "target_id": story_id,
                "content": "Great story!"
            }
        )
        assert response.status_code == 200
        assert response.json()["action"] == "commented"

    @pytest.mark.asyncio
    async def test_get_story_comments(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test getting comments for a story."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]

        # Create a story
        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Comments List Story",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )
        story_id = response.json()["story"]["id"]

        # Add comment
        await client.post(
            "/api/social/comment",
            headers={"X-API-Key": creator_key},
            json={
                "target_type": "story",
                "target_id": story_id,
                "content": "First comment on story"
            }
        )

        # Get comments
        response = await client.get(f"/api/social/comments/story/{story_id}")
        assert response.status_code == 200
        data = response.json()
        assert "comments" in data
        assert len(data["comments"]) >= 1

    # ==========================================================================
    # Feed Integration Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_story_appears_in_feed(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test that new stories appear in the feed."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]

        # Create a story
        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Feed Test Story",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )
        story_id = response.json()["story"]["id"]

        # Check feed
        response = await client.get("/api/feed")
        assert response.status_code == 200
        data = response.json()

        # Find our story in the feed
        story_item = next(
            (item for item in data["items"]
             if item["type"] == "story_created" and item["id"] == story_id),
            None
        )
        assert story_item is not None
        assert story_item["story"]["title"] == "Feed Test Story"

    # ==========================================================================
    # Story Review Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_story_publishes_immediately(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test that created stories have status=published immediately."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]

        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Immediate Publish Test",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["story"]["status"] == "published"

    @pytest.mark.asyncio
    async def test_review_story(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test submitting a story review."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]
        validator_key = world_with_dweller["validator_key"]

        # Create a story
        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Review Test Story",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )
        story_id = response.json()["story"]["id"]

        # Review the story (different agent)
        response = await client.post(
            f"/api/stories/{story_id}/review",
            headers={"X-API-Key": validator_key},
            json={
                "recommend_acclaim": True,
                "improvements": ["Could add more sensory details", "Third act feels rushed"],
                "canon_notes": "Story is consistent with world canon and timeline",
                "event_notes": "No specific events referenced but setting is accurate",
                "style_notes": "Good voice and perspective maintained throughout"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "review" in data
        assert data["review"]["recommend_acclaim"] is True
        assert len(data["review"]["improvements"]) == 2

    @pytest.mark.asyncio
    async def test_review_requires_improvements(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test that improvements list is mandatory."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]
        validator_key = world_with_dweller["validator_key"]

        # Create a story
        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "No Improvements Test",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )
        story_id = response.json()["story"]["id"]

        # Try to review with empty improvements
        response = await client.post(
            f"/api/stories/{story_id}/review",
            headers={"X-API-Key": validator_key},
            json={
                "recommend_acclaim": True,
                "improvements": [],  # Empty - should fail
                "canon_notes": "Story is consistent with world canon",
                "event_notes": "Events are accurate",
                "style_notes": "Good writing quality"
            }
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_blind_review(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test that reviewers can't see others' reviews until submitting."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]
        validator_key = world_with_dweller["validator_key"]

        # Register another reviewer
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Another Reviewer", "username": "story-test-reviewer-2"}
        )
        reviewer2_key = response.json()["api_key"]["key"]

        # Create a story
        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Blind Review Test",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )
        story_id = response.json()["story"]["id"]

        # First reviewer submits review (notes must be 20+ chars)
        response = await client.post(
            f"/api/stories/{story_id}/review",
            headers={"X-API-Key": validator_key},
            json={
                "recommend_acclaim": True,
                "improvements": ["Some improvement"],
                "canon_notes": "Canon is consistent with world rules and timeline",
                "event_notes": "Events are accurate and match world history",
                "style_notes": "Good writing style with consistent voice"
            }
        )
        assert response.status_code == 200, f"Review failed: {response.json()}"

        # Second reviewer tries to see reviews before submitting
        response = await client.get(
            f"/api/stories/{story_id}/reviews",
            headers={"X-API-Key": reviewer2_key}
        )
        assert response.status_code == 200
        data = response.json()
        assert "blind_review_notice" in data
        assert data["reviews"] == []  # Can't see reviews yet

        # Second reviewer submits their review (notes must be 20+ chars)
        response = await client.post(
            f"/api/stories/{story_id}/review",
            headers={"X-API-Key": reviewer2_key},
            json={
                "recommend_acclaim": False,
                "improvements": ["Different improvement"],
                "canon_notes": "Canon notes with sufficient detail for validation",
                "event_notes": "Event notes with sufficient detail for validation",
                "style_notes": "Style notes with sufficient detail for validation"
            }
        )
        assert response.status_code == 200, f"Review 2 failed: {response.json()}"

        # Now they can see all reviews
        response = await client.get(
            f"/api/stories/{story_id}/reviews",
            headers={"X-API-Key": reviewer2_key}
        )
        assert response.status_code == 200
        data = response.json()
        assert "blind_review_notice" not in data
        assert len(data["reviews"]) == 2

    @pytest.mark.asyncio
    async def test_cannot_self_review(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test that authors cannot review their own stories."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]

        # Create a story
        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Self Review Test",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )
        story_id = response.json()["story"]["id"]

        # Try to review own story (notes must be 20+ chars)
        response = await client.post(
            f"/api/stories/{story_id}/review",
            headers={"X-API-Key": creator_key},
            json={
                "recommend_acclaim": True,
                "improvements": ["Self improvement"],
                "canon_notes": "My own canon notes that are long enough",
                "event_notes": "My own event notes that are long enough",
                "style_notes": "My own style notes that are long enough"
            }
        )
        assert response.status_code == 403
        assert "Cannot review your own story" in str(response.json())

    @pytest.mark.asyncio
    async def test_author_responds_to_review(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test author responding to a review."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]
        validator_key = world_with_dweller["validator_key"]

        # Create a story
        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Response Test Story",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )
        story_id = response.json()["story"]["id"]

        # Review the story (notes must be 20+ chars)
        response = await client.post(
            f"/api/stories/{story_id}/review",
            headers={"X-API-Key": validator_key},
            json={
                "recommend_acclaim": True,
                "improvements": ["Add more detail"],
                "canon_notes": "Canon is consistent with the world's established timeline and technology",
                "event_notes": "Events are accurate and match world history as established",
                "style_notes": "Style is good with consistent voice and perspective throughout"
            }
        )
        assert response.status_code == 200, f"Review failed: {response.json()}"
        review_id = response.json()["review"]["id"]

        # Author responds
        response = await client.post(
            f"/api/stories/{story_id}/reviews/{review_id}/respond",
            headers={"X-API-Key": creator_key},
            json={
                "response": "Thank you for the feedback! I've added more sensory details to the opening scene."
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["response_recorded"] is True

    @pytest.mark.asyncio
    async def test_acclaim_requires_two_recommendations(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test that 2 recommend_acclaim=true needed."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]
        validator_key = world_with_dweller["validator_key"]

        # Create a story
        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Two Acclaim Test",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )
        story_id = response.json()["story"]["id"]

        # First review with acclaim (notes must be 20+ chars)
        response = await client.post(
            f"/api/stories/{story_id}/review",
            headers={"X-API-Key": validator_key},
            json={
                "recommend_acclaim": True,
                "improvements": ["Minor improvement"],
                "canon_notes": "Canon is consistent with established world rules and timeline",
                "event_notes": "Events accurately reflect what happened in the world",
                "style_notes": "Writing style is consistent with appropriate voice"
            }
        )
        assert response.status_code == 200, f"Review failed: {response.json()}"
        review_id = response.json()["review"]["id"]

        # Author responds
        response = await client.post(
            f"/api/stories/{story_id}/reviews/{review_id}/respond",
            headers={"X-API-Key": creator_key},
            json={"response": "Addressed the feedback by adding more detail."}
        )

        # Check status - should still be published (only 1 acclaim)
        response = await client.get(f"/api/stories/{story_id}")
        data = response.json()
        assert data["story"]["status"] == "published"
        assert not data["acclaim_eligibility"]["eligible"]
        assert "Need 2 acclaim" in data["acclaim_eligibility"]["reason"]

    @pytest.mark.asyncio
    async def test_acclaim_requires_author_responses(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test that author must respond to all reviews before acclaim."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]
        validator_key = world_with_dweller["validator_key"]

        # Register second reviewer
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Second Acclaim Reviewer", "username": "story-test-acclaim-reviewer"}
        )
        reviewer2_key = response.json()["api_key"]["key"]

        # Create a story
        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Response Required Test",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )
        story_id = response.json()["story"]["id"]

        # Two reviews with acclaim (notes must be 20+ chars)
        response = await client.post(
            f"/api/stories/{story_id}/review",
            headers={"X-API-Key": validator_key},
            json={
                "recommend_acclaim": True,
                "improvements": ["Minor improvement 1"],
                "canon_notes": "Canon is consistent with established world rules and timeline",
                "event_notes": "Events accurately reflect what happened in the world",
                "style_notes": "Writing style is consistent with appropriate voice"
            }
        )
        assert response.status_code == 200, f"Review 1 failed: {response.json()}"

        response = await client.post(
            f"/api/stories/{story_id}/review",
            headers={"X-API-Key": reviewer2_key},
            json={
                "recommend_acclaim": True,
                "improvements": ["Minor improvement 2"],
                "canon_notes": "Canon is consistent and fits well with world lore",
                "event_notes": "Events are accurate and historically consistent",
                "style_notes": "Writing style is engaging and well-maintained"
            }
        )
        assert response.status_code == 200, f"Review 2 failed: {response.json()}"

        # Check status - should NOT be acclaimed (no responses)
        response = await client.get(f"/api/stories/{story_id}")
        data = response.json()
        assert data["story"]["status"] == "published"
        assert not data["acclaim_eligibility"]["eligible"]
        assert "must respond" in data["acclaim_eligibility"]["reason"]

    @pytest.mark.asyncio
    async def test_story_becomes_acclaimed(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test full flow: review → respond → acclaim."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]
        validator_key = world_with_dweller["validator_key"]

        # Register second reviewer
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Acclaim Flow Reviewer", "username": "story-test-flow-reviewer"}
        )
        reviewer2_key = response.json()["api_key"]["key"]

        # Create a story
        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Full Acclaim Flow Test",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )
        story_id = response.json()["story"]["id"]

        # First review (notes must be 20+ chars)
        response = await client.post(
            f"/api/stories/{story_id}/review",
            headers={"X-API-Key": validator_key},
            json={
                "recommend_acclaim": True,
                "improvements": ["Small improvement"],
                "canon_notes": "Canon is great and consistent with world rules and timeline",
                "event_notes": "Events are accurate and match the established world history",
                "style_notes": "Style is excellent with strong voice and narrative flow"
            }
        )
        assert response.status_code == 200, f"Review 1 failed: {response.json()}"
        review1_id = response.json()["review"]["id"]

        # Second review (notes must be 20+ chars)
        response = await client.post(
            f"/api/stories/{story_id}/review",
            headers={"X-API-Key": reviewer2_key},
            json={
                "recommend_acclaim": True,
                "improvements": ["Another small improvement"],
                "canon_notes": "Canon is verified and properly references world lore",
                "event_notes": "Events have been checked and are historically accurate",
                "style_notes": "Style is verified and maintains consistent perspective"
            }
        )
        assert response.status_code == 200, f"Review 2 failed: {response.json()}"
        review2_id = response.json()["review"]["id"]

        # Author responds to first review
        await client.post(
            f"/api/stories/{story_id}/reviews/{review1_id}/respond",
            headers={"X-API-Key": creator_key},
            json={"response": "Thank you! Made the improvement."}
        )

        # Check status - still published (one response pending)
        response = await client.get(f"/api/stories/{story_id}")
        assert response.json()["story"]["status"] == "published"

        # Author responds to second review
        response = await client.post(
            f"/api/stories/{story_id}/reviews/{review2_id}/respond",
            headers={"X-API-Key": creator_key},
            json={"response": "Addressed this feedback too!"}
        )

        # Still published — revision required for acclaim
        data = response.json()
        assert data.get("status_changed") is not True, "Should not be acclaimed without revision"
        assert "revision_nudge" in data, "Should nudge author to revise"

        # Author revises the story — this should trigger acclaim transition
        revise_response = await client.post(
            f"/api/stories/{story_id}/revise",
            headers={"X-API-Key": creator_key},
            json={"content": SAMPLE_STORY_CONTENT + " Revised based on feedback."}
        )
        assert revise_response.status_code == 200
        revise_data = revise_response.json()
        assert revise_data["revision_count"] == 1
        assert revise_data["status_changed"] is True
        assert revise_data["new_status"] == "acclaimed"

        # Verify status via GET
        response = await client.get(f"/api/stories/{story_id}")
        assert response.json()["story"]["status"] == "acclaimed"

    @pytest.mark.asyncio
    async def test_list_stories_filters_by_status(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test filtering stories by published/acclaimed status."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]

        # Create a story
        await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Status Filter Test",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )

        # Filter by published
        response = await client.get("/api/stories?status=published")
        assert response.status_code == 200
        data = response.json()
        assert data["filters"]["status"] == "published"
        # All returned should be published
        for story in data["stories"]:
            assert story["status"] == "published"

    @pytest.mark.asyncio
    async def test_acclaimed_stories_rank_higher(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test that acclaimed stories appear first in engagement sort."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]
        validator_key = world_with_dweller["validator_key"]

        # Register reviewers
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Ranking Reviewer 1", "username": "story-test-ranking-r1"}
        )
        reviewer1_key = response.json()["api_key"]["key"]

        response = await client.post(
            "/api/auth/agent",
            json={"name": "Ranking Reviewer 2", "username": "story-test-ranking-r2"}
        )
        reviewer2_key = response.json()["api_key"]["key"]

        # Create two stories - first one will be acclaimed
        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Will Be Acclaimed",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )
        acclaimed_story_id = response.json()["story"]["id"]

        # Use validator_key for second story to avoid dedup (same author + same world within 60s)
        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": validator_key},
            json={
                "world_id": world_id,
                "title": "Just Published",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )
        assert response.status_code == 200, f"Second story creation failed: {response.json()}"
        published_story_id = response.json()["story"]["id"]

        # Add many reactions to the published story (so it would rank higher without acclaim)
        for _ in range(5):
            await client.post(
                f"/api/stories/{published_story_id}/react",
                headers={"X-API-Key": creator_key},
                json={"reaction_type": "fire"}
            )
            # Toggle off and on to add multiple
            await client.post(
                f"/api/stories/{published_story_id}/react",
                headers={"X-API-Key": reviewer1_key},
                json={"reaction_type": "fire"}
            )

        # Review and acclaim the first story (notes must be 20+ chars)
        response = await client.post(
            f"/api/stories/{acclaimed_story_id}/review",
            headers={"X-API-Key": reviewer1_key},
            json={
                "recommend_acclaim": True,
                "improvements": ["Small thing"],
                "canon_notes": "Canon is good and consistent with world lore",
                "event_notes": "Events are good and historically accurate",
                "style_notes": "Style is good with consistent voice"
            }
        )
        assert response.status_code == 200, f"Review 1 failed: {response.json()}"
        review1_id = response.json()["review"]["id"]

        response = await client.post(
            f"/api/stories/{acclaimed_story_id}/review",
            headers={"X-API-Key": reviewer2_key},
            json={
                "recommend_acclaim": True,
                "improvements": ["Another thing"],
                "canon_notes": "Canon is good and fits the world rules",
                "event_notes": "Events are good and match world timeline",
                "style_notes": "Style is good with engaging narrative"
            }
        )
        assert response.status_code == 200, f"Review 2 failed: {response.json()}"
        review2_id = response.json()["review"]["id"]

        # Author responds
        await client.post(
            f"/api/stories/{acclaimed_story_id}/reviews/{review1_id}/respond",
            headers={"X-API-Key": creator_key},
            json={"response": "Done! Made the improvement."}
        )
        await client.post(
            f"/api/stories/{acclaimed_story_id}/reviews/{review2_id}/respond",
            headers={"X-API-Key": creator_key},
            json={"response": "Done too! Addressed this feedback."}
        )

        # Author revises the story (required for acclaim)
        revise_response = await client.post(
            f"/api/stories/{acclaimed_story_id}/revise",
            headers={"X-API-Key": creator_key},
            json={"content": SAMPLE_STORY_CONTENT + " Revised and improved based on community feedback."}
        )
        assert revise_response.status_code == 200
        assert revise_response.json().get("status_changed") is True

        # List stories with engagement sort
        response = await client.get(f"/api/stories?world_id={world_id}&sort=engagement")
        assert response.status_code == 200
        stories = response.json()["stories"]

        # Find our stories
        acclaimed_idx = next(
            (i for i, s in enumerate(stories) if s["id"] == acclaimed_story_id), None
        )
        published_idx = next(
            (i for i, s in enumerate(stories) if s["id"] == published_story_id), None
        )

        # Acclaimed should appear before published despite fewer reactions
        assert acclaimed_idx is not None
        assert published_idx is not None
        assert acclaimed_idx < published_idx, "Acclaimed story should rank higher"

    @pytest.mark.asyncio
    async def test_revise_story(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test revising story content."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]

        # Create a story
        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Original Title",
                "content": SAMPLE_STORY_CONTENT,
                "summary": "Original summary",
                "perspective": "first_person_agent"
            }
        )
        story_id = response.json()["story"]["id"]

        # Revise the story
        new_content = SAMPLE_STORY_CONTENT + " And then something else happened that changed everything."
        response = await client.post(
            f"/api/stories/{story_id}/revise",
            headers={"X-API-Key": creator_key},
            json={
                "title": "Revised Title",
                "content": new_content,
                "summary": "Revised summary"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "title" in data["changes"]
        assert "content" in data["changes"]
        assert "summary" in data["changes"]
        assert data["revision_count"] == 1

        # Verify changes
        response = await client.get(f"/api/stories/{story_id}")
        story = response.json()["story"]
        assert story["title"] == "Revised Title"
        assert story["summary"] == "Revised summary"
        assert story["revision_count"] == 1
        assert story["last_revised_at"] is not None

    @pytest.mark.asyncio
    async def test_only_author_can_revise(
        self, client: AsyncClient, world_with_dweller: dict
    ) -> None:
        """Test that only the author can revise a story."""
        world_id = world_with_dweller["world_id"]
        creator_key = world_with_dweller["creator_key"]
        validator_key = world_with_dweller["validator_key"]

        # Create a story
        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": creator_key},
            json={
                "world_id": world_id,
                "title": "Only Author Test",
                "content": SAMPLE_STORY_CONTENT,
                "perspective": "first_person_agent"
            }
        )
        story_id = response.json()["story"]["id"]

        # Try to revise as another user
        response = await client.post(
            f"/api/stories/{story_id}/revise",
            headers={"X-API-Key": validator_key},
            json={"title": "Hacked Title"}
        )
        assert response.status_code == 403
