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
                "suggested_fixes": []
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
                "suggested_fixes": []
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
                "suggested_fixes": []
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
                "suggested_fixes": []
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
