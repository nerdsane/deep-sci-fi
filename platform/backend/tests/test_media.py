"""Tests for media generation API endpoints."""

import pytest
import pytest_asyncio
from uuid import uuid4
from unittest.mock import patch, AsyncMock
from datetime import timedelta

from httpx import AsyncClient

from db import MediaGeneration, MediaGenerationStatus, MediaType, User, UserType
from utils.clock import now as utc_now
from tests.conftest import (
    SAMPLE_CAUSAL_CHAIN,
    SAMPLE_REGION,
    SAMPLE_DWELLER,
    approve_proposal,
)


@pytest_asyncio.fixture
async def test_world(client: AsyncClient, test_agent: dict) -> dict:
    """Create a test world (proposal -> approve -> world)."""
    api_key = test_agent["api_key"]

    # Create and approve a proposal to get a world
    proposal_resp = await client.post(
        "/api/proposals",
        headers={"X-API-Key": api_key},
        json={
            "name": "Media Test World",
            "premise": "A world built entirely for testing media generation capabilities and ensuring the platform handles visual content correctly across all endpoints.",
            "year_setting": 2087,
            "causal_chain": SAMPLE_CAUSAL_CHAIN,
            "scientific_basis": "Based on current trends in AI-generated media and the increasing importance of visual content in digital platforms.",
        },
    )
    assert proposal_resp.status_code == 200
    proposal_id = proposal_resp.json()["id"]

    result = await approve_proposal(client, proposal_id, api_key)
    assert result.get("world_created"), f"World not created: {result}"

    return result["world_created"]


@pytest_asyncio.fixture
async def test_story(client: AsyncClient, test_agent: dict, test_world: dict) -> dict:
    """Create a test story in the test world."""
    api_key = test_agent["api_key"]
    world_id = test_world["id"]

    # Add region and create dweller
    await client.post(
        f"/api/dwellers/worlds/{world_id}/regions",
        headers={"X-API-Key": api_key},
        json=SAMPLE_REGION,
    )

    dweller_resp = await client.post(
        f"/api/dwellers/worlds/{world_id}/dwellers",
        headers={"X-API-Key": api_key},
        json=SAMPLE_DWELLER,
    )
    assert dweller_resp.status_code == 200
    dweller_id = dweller_resp.json()["dweller"]["id"]

    # Create story
    story_resp = await client.post(
        "/api/stories",
        headers={"X-API-Key": api_key},
        json={
            "world_id": world_id,
            "title": "Media Test Story",
            "content": "A test story content that is long enough to meet the minimum content length requirements for story creation. It describes events in the test world with sufficient detail to pass validation checks.",
            "perspective": "first_person_dweller",
            "perspective_dweller_id": dweller_id,
        },
    )
    assert story_resp.status_code == 200
    return story_resp.json()["story"]


@pytest.mark.asyncio
class TestGenerateWorldCover:
    """Tests for POST /api/media/worlds/{world_id}/cover-image"""

    async def test_generates_world_cover(self, client: AsyncClient, test_agent: dict, test_world: dict):
        """Should create a pending generation and return generation_id."""
        resp = await client.post(
            f"/api/media/worlds/{test_world['id']}/cover-image",
            headers={"X-API-Key": test_agent["api_key"]},
            json={"image_prompt": "A cinematic sci-fi landscape for testing purposes"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert "generation_id" in data
        assert "poll_url" in data
        assert data["estimated_seconds"] > 0

    async def test_rejects_invalid_world(self, client: AsyncClient, test_agent: dict):
        """Should return 404 for non-existent world."""
        resp = await client.post(
            f"/api/media/worlds/{uuid4()}/cover-image",
            headers={"X-API-Key": test_agent["api_key"]},
            json={"image_prompt": "A cinematic sci-fi landscape for testing purposes"},
        )
        assert resp.status_code == 404

    async def test_rejects_short_prompt(self, client: AsyncClient, test_agent: dict, test_world: dict):
        """Should reject prompts shorter than 10 characters."""
        resp = await client.post(
            f"/api/media/worlds/{test_world['id']}/cover-image",
            headers={"X-API-Key": test_agent["api_key"]},
            json={"image_prompt": "short"},
        )
        assert resp.status_code == 422

    async def test_requires_auth(self, client: AsyncClient, test_world: dict):
        """Should require authentication."""
        resp = await client.post(
            f"/api/media/worlds/{test_world['id']}/cover-image",
            json={"image_prompt": "A cinematic sci-fi landscape for testing purposes"},
        )
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
class TestGenerateStoryCover:
    """Tests for POST /api/media/stories/{story_id}/cover-image"""

    async def test_generates_story_cover(self, client: AsyncClient, test_agent: dict, test_story: dict):
        """Should create a pending generation for story cover."""
        resp = await client.post(
            f"/api/media/stories/{test_story['id']}/cover-image",
            headers={"X-API-Key": test_agent["api_key"]},
            json={"image_prompt": "A dramatic scene from a futuristic world"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert "generation_id" in data

    async def test_rejects_invalid_story(self, client: AsyncClient, test_agent: dict):
        """Should return 404 for non-existent story."""
        resp = await client.post(
            f"/api/media/stories/{uuid4()}/cover-image",
            headers={"X-API-Key": test_agent["api_key"]},
            json={"image_prompt": "A dramatic scene from a futuristic world"},
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestGenerateStoryVideo:
    """Tests for POST /api/media/stories/{story_id}/video"""

    async def test_generates_story_video(self, client: AsyncClient, test_agent: dict, test_story: dict):
        """Should create a pending video generation."""
        resp = await client.post(
            f"/api/media/stories/{test_story['id']}/video",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "video_prompt": "A sweeping aerial shot of a futuristic landscape",
                "duration_seconds": 10,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert "estimated_cost_usd" in data

    async def test_rejects_long_duration(self, client: AsyncClient, test_agent: dict, test_story: dict):
        """Should reject duration over 15 seconds."""
        resp = await client.post(
            f"/api/media/stories/{test_story['id']}/video",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "video_prompt": "A sweeping aerial shot of a futuristic landscape",
                "duration_seconds": 30,
            },
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestGetGenerationStatus:
    """Tests for GET /api/media/{generation_id}/status"""

    async def test_returns_pending_status(self, client: AsyncClient, test_agent: dict, test_world: dict):
        """Should return pending status for new generation."""
        # Create a generation
        resp = await client.post(
            f"/api/media/worlds/{test_world['id']}/cover-image",
            headers={"X-API-Key": test_agent["api_key"]},
            json={"image_prompt": "A cinematic sci-fi landscape for testing purposes"},
        )
        gen_id = resp.json()["generation_id"]

        # Check status — background task may complete before we poll
        status_resp = await client.get(f"/api/media/{gen_id}/status")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["status"].upper() in ("PENDING", "GENERATING", "COMPLETED")
        assert data["target_type"] == "world"

    async def test_returns_404_for_invalid_id(self, client: AsyncClient):
        """Should return 404 for non-existent generation."""
        resp = await client.get(f"/api/media/{uuid4()}/status")
        assert resp.status_code == 404

    async def test_stale_recovery(self, client: AsyncClient, test_agent: dict, test_world: dict, db_session):
        """Should mark stale generations as failed."""
        # Create a user for the FK constraint
        user = User(name="Stale User", username=f"stale-{uuid4().hex[:8]}", type=UserType.AGENT)
        db_session.add(user)
        await db_session.flush()

        # Create a generation stuck in GENERATING
        gen = MediaGeneration(
            requested_by=user.id,
            target_type="world",
            target_id=uuid4(),
            media_type=MediaType.COVER_IMAGE,
            prompt="test",
            provider="test",
            status=MediaGenerationStatus.GENERATING,
            started_at=utc_now() - timedelta(minutes=15),
        )
        db_session.add(gen)
        await db_session.commit()

        # Poll status — should detect staleness
        status_resp = await client.get(f"/api/media/{gen.id}/status")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["status"].upper() == "FAILED"
        assert "timed out" in data.get("error_message", "").lower()


@pytest.mark.asyncio
class TestGetBudget:
    """Tests for GET /api/media/budget"""

    async def test_returns_budget(self, client: AsyncClient, test_agent: dict):
        """Should return budget summary."""
        resp = await client.get(
            "/api/media/budget",
            headers={"X-API-Key": test_agent["api_key"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "monthly_budget_usd" in data
        assert "monthly_spend_usd" in data
        assert "daily_image_limit" in data
        assert "daily_video_limit" in data

    async def test_requires_auth(self, client: AsyncClient):
        """Should require authentication."""
        resp = await client.get("/api/media/budget")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
class TestDailyLimitEnforcement:
    """Tests for rate limiting via API endpoints."""

    async def test_blocks_after_image_limit(self, client: AsyncClient, test_agent: dict, test_world: dict):
        """Should return 429 after daily image limit is reached."""
        api_key = test_agent["api_key"]

        # Generate images up to the limit
        for i in range(5):
            resp = await client.post(
                f"/api/media/worlds/{test_world['id']}/cover-image",
                headers={"X-API-Key": api_key},
                json={"image_prompt": f"Test image prompt number {i} for limit testing"},
            )
            assert resp.status_code == 200, f"Generation {i} failed: {resp.json()}"

        # Next one should be blocked
        resp = await client.post(
            f"/api/media/worlds/{test_world['id']}/cover-image",
            headers={"X-API-Key": api_key},
            json={"image_prompt": "This should be blocked by the daily limit"},
        )
        assert resp.status_code == 429


@pytest.mark.asyncio
class TestWorldCoverInResponse:
    """Tests that cover_image_url appears in world API responses."""

    async def test_list_worlds_includes_cover(self, client: AsyncClient, test_world: dict):
        """World listing should include cover_image_url field."""
        resp = await client.get("/api/worlds")
        assert resp.status_code == 200
        worlds = resp.json()["worlds"]
        # Find our test world
        world = next((w for w in worlds if w["id"] == test_world["id"]), None)
        assert world is not None
        assert "cover_image_url" in world

    async def test_get_world_includes_cover(self, client: AsyncClient, test_world: dict):
        """World detail should include cover_image_url field."""
        resp = await client.get(f"/api/worlds/{test_world['id']}")
        assert resp.status_code == 200
        world = resp.json()["world"]
        assert "cover_image_url" in world


@pytest.mark.asyncio
class TestStoryCoverInResponse:
    """Tests that media fields appear in story API responses."""

    async def test_get_story_includes_media_fields(self, client: AsyncClient, test_agent: dict, test_story: dict):
        """Story detail should include media fields."""
        resp = await client.get(
            f"/api/stories/{test_story['id']}",
            headers={"X-API-Key": test_agent["api_key"]},
        )
        assert resp.status_code == 200
        story = resp.json()["story"]
        assert "cover_image_url" in story
        assert "video_url" in story
        assert "thumbnail_url" in story
