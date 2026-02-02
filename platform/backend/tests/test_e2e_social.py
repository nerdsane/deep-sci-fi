"""End-to-end tests for the social interaction endpoints.

This tests:
1. Reactions (add, toggle, update)
2. Follow/unfollow worlds
3. Comments (add, list)
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
        "year": 2028,
        "event": "Breakthrough in quantum computing enables practical quantum advantage for optimization",
        "reasoning": "Following Google and IBM progress, error correction techniques mature"
    },
    {
        "year": 2035,
        "event": "Quantum networks connect major research institutions globally",
        "reasoning": "Quantum repeater technology enables long-distance entanglement distribution"
    },
    {
        "year": 2042,
        "event": "Quantum-secured global financial system replaces traditional infrastructure",
        "reasoning": "Threat of quantum attacks on classical cryptography drives adoption"
    }
]


@requires_postgres
class TestSocialFlow:
    """Test the social interaction endpoints."""

    @pytest.fixture
    async def world_setup(self, client: AsyncClient) -> dict:
        """Create agents and an approved world for social testing."""
        # Register creator
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Social Creator", "username": "social-test-creator"}
        )
        creator = response.json()
        creator_key = creator["api_key"]["key"]

        # Register validator
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Social Validator", "username": "social-test-validator"}
        )
        validator_key = response.json()["api_key"]["key"]

        # Create and approve proposal
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": creator_key},
            json={
                "name": "Quantum Finance 2042",
                "premise": "Quantum-secured global financial system replaces traditional banking infrastructure",
                "year_setting": 2042,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": (
                    "Based on current quantum computing progress from Google, IBM, and academic institutions. "
                    "Quantum networks follow established protocols like BB84 and E91. Financial system "
                    "migration driven by threat of Shor's algorithm breaking RSA encryption."
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
                "critique": "Solid technical foundation with clear progression from current quantum research",
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )
        assert response.status_code == 200, f"Validation failed: {response.json()}"

        response = await client.get(f"/api/proposals/{proposal_id}")
        world_id = response.json()["proposal"]["resulting_world_id"]

        return {
            "world_id": world_id,
            "creator_key": creator_key,
            "validator_key": validator_key,
        }

    # ==========================================================================
    # Reaction Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_add_reaction_to_world(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test adding a reaction to a world."""
        world_id = world_setup["world_id"]
        creator_key = world_setup["creator_key"]

        response = await client.post(
            "/api/social/react",
            headers={"X-API-Key": creator_key},
            json={
                "target_type": "world",
                "target_id": world_id,
                "reaction_type": "fire"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "added"
        assert data["reaction_type"] == "fire"

    @pytest.mark.asyncio
    async def test_toggle_reaction_removes_it(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test that reacting twice with same type toggles it off."""
        world_id = world_setup["world_id"]
        creator_key = world_setup["creator_key"]

        # Add reaction
        response = await client.post(
            "/api/social/react",
            headers={"X-API-Key": creator_key},
            json={
                "target_type": "world",
                "target_id": world_id,
                "reaction_type": "mind"
            }
        )
        assert response.json()["action"] == "added"

        # Toggle off
        response = await client.post(
            "/api/social/react",
            headers={"X-API-Key": creator_key},
            json={
                "target_type": "world",
                "target_id": world_id,
                "reaction_type": "mind"
            }
        )
        assert response.status_code == 200
        assert response.json()["action"] == "removed"

    @pytest.mark.asyncio
    async def test_change_reaction_type(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test changing reaction from one type to another."""
        world_id = world_setup["world_id"]
        creator_key = world_setup["creator_key"]

        # Add heart reaction
        response = await client.post(
            "/api/social/react",
            headers={"X-API-Key": creator_key},
            json={
                "target_type": "world",
                "target_id": world_id,
                "reaction_type": "heart"
            }
        )
        assert response.json()["action"] == "added"

        # Change to thinking
        response = await client.post(
            "/api/social/react",
            headers={"X-API-Key": creator_key},
            json={
                "target_type": "world",
                "target_id": world_id,
                "reaction_type": "thinking"
            }
        )
        assert response.status_code == 200
        assert response.json()["action"] == "updated"
        assert response.json()["reaction_type"] == "thinking"

    @pytest.mark.asyncio
    async def test_react_to_nonexistent_world(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test that reacting to nonexistent world returns 404."""
        creator_key = world_setup["creator_key"]

        response = await client.post(
            "/api/social/react",
            headers={"X-API-Key": creator_key},
            json={
                "target_type": "world",
                "target_id": "00000000-0000-0000-0000-000000000000",
                "reaction_type": "fire"
            }
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_react_requires_auth(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test that reacting requires authentication."""
        world_id = world_setup["world_id"]

        response = await client.post(
            "/api/social/react",
            json={
                "target_type": "world",
                "target_id": world_id,
                "reaction_type": "fire"
            }
        )
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403, 422]

    # ==========================================================================
    # Follow Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_follow_world(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test following a world."""
        world_id = world_setup["world_id"]
        creator_key = world_setup["creator_key"]

        response = await client.post(
            "/api/social/follow",
            headers={"X-API-Key": creator_key},
            json={
                "target_type": "world",
                "target_id": world_id
            }
        )
        assert response.status_code == 200
        assert response.json()["action"] == "followed"

    @pytest.mark.asyncio
    async def test_follow_already_following(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test that following twice returns already_following."""
        world_id = world_setup["world_id"]
        creator_key = world_setup["creator_key"]

        # Follow first time
        await client.post(
            "/api/social/follow",
            headers={"X-API-Key": creator_key},
            json={
                "target_type": "world",
                "target_id": world_id
            }
        )

        # Follow second time
        response = await client.post(
            "/api/social/follow",
            headers={"X-API-Key": creator_key},
            json={
                "target_type": "world",
                "target_id": world_id
            }
        )
        assert response.status_code == 200
        assert response.json()["action"] == "already_following"

    @pytest.mark.asyncio
    async def test_unfollow_world(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test unfollowing a world."""
        world_id = world_setup["world_id"]
        creator_key = world_setup["creator_key"]

        # Follow first
        await client.post(
            "/api/social/follow",
            headers={"X-API-Key": creator_key},
            json={
                "target_type": "world",
                "target_id": world_id
            }
        )

        # Unfollow
        response = await client.post(
            "/api/social/unfollow",
            headers={"X-API-Key": creator_key},
            json={
                "target_type": "world",
                "target_id": world_id
            }
        )
        assert response.status_code == 200
        assert response.json()["action"] == "unfollowed"

    @pytest.mark.asyncio
    async def test_unfollow_not_following(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test unfollowing when not following returns not_following."""
        world_id = world_setup["world_id"]
        validator_key = world_setup["validator_key"]

        response = await client.post(
            "/api/social/unfollow",
            headers={"X-API-Key": validator_key},
            json={
                "target_type": "world",
                "target_id": world_id
            }
        )
        assert response.status_code == 200
        assert response.json()["action"] == "not_following"

    # ==========================================================================
    # Comment Tests
    # ==========================================================================

    @pytest.mark.asyncio
    async def test_add_comment_to_world(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test adding a comment to a world."""
        world_id = world_setup["world_id"]
        creator_key = world_setup["creator_key"]

        response = await client.post(
            "/api/social/comment",
            headers={"X-API-Key": creator_key},
            json={
                "target_type": "world",
                "target_id": world_id,
                "content": "This quantum finance concept is fascinating!"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "commented"
        assert "comment" in data
        assert data["comment"]["content"] == "This quantum finance concept is fascinating!"
        assert "id" in data["comment"]
        assert "created_at" in data["comment"]

    @pytest.mark.asyncio
    async def test_get_comments_for_world(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test listing comments for a world."""
        world_id = world_setup["world_id"]
        creator_key = world_setup["creator_key"]
        validator_key = world_setup["validator_key"]

        # Add comments from different users
        await client.post(
            "/api/social/comment",
            headers={"X-API-Key": creator_key},
            json={
                "target_type": "world",
                "target_id": world_id,
                "content": "First comment from creator"
            }
        )

        await client.post(
            "/api/social/comment",
            headers={"X-API-Key": validator_key},
            json={
                "target_type": "world",
                "target_id": world_id,
                "content": "Second comment from validator"
            }
        )

        # Get comments
        response = await client.get(f"/api/social/comments/world/{world_id}")
        assert response.status_code == 200
        data = response.json()
        assert "comments" in data
        assert len(data["comments"]) >= 2

        # Comments should have proper structure
        for comment in data["comments"]:
            assert "id" in comment
            assert "content" in comment
            assert "created_at" in comment
            assert "user" in comment

    @pytest.mark.asyncio
    async def test_comment_requires_auth(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test that commenting requires authentication."""
        world_id = world_setup["world_id"]

        response = await client.post(
            "/api/social/comment",
            json={
                "target_type": "world",
                "target_id": world_id,
                "content": "Unauthorized comment"
            }
        )
        assert response.status_code in [401, 403, 422]

    @pytest.mark.asyncio
    async def test_comments_empty_for_new_world(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test that a new world has no comments initially (before we add any)."""
        # Create a new world to ensure it has no comments
        creator_key = world_setup["creator_key"]
        validator_key = world_setup["validator_key"]

        # Create new proposal
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": creator_key},
            json={
                "name": "Comment Test World",
                "premise": "A world specifically created to test that new worlds have no comments",
                "year_setting": 2050,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": "Based on established quantum computing research and cryptography"
            }
        )
        proposal_id = response.json()["id"]

        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": creator_key}
        )

        await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "approve",
                "critique": "Acceptable world for testing comment functionality",
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )

        response = await client.get(f"/api/proposals/{proposal_id}")
        new_world_id = response.json()["proposal"]["resulting_world_id"]

        # Get comments for new world
        response = await client.get(f"/api/social/comments/world/{new_world_id}")
        assert response.status_code == 200
        assert response.json()["comments"] == []
