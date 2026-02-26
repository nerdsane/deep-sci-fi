"""Tests for story writing guidance token enforcement."""

import os
from datetime import timedelta
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from api import auth as auth_module
from db import GuidanceToken, Story, StoryWritingGuidance
from tests.conftest import SAMPLE_CAUSAL_CHAIN, approve_proposal
from utils.clock import SimulatedClock, now as utc_now, reset_clock, set_clock
from utils.guidance_tokens import hash_guidance_token


requires_postgres = pytest.mark.skipif(
    "postgresql" not in os.getenv("TEST_DATABASE_URL", ""),
    reason="Requires PostgreSQL (set TEST_DATABASE_URL)",
)


SAMPLE_STORY_CONTENT = (
    "The coolant mist drifted over the glass atrium, and everyone on shift felt the hum "
    "change before the dashboards confirmed it. Output crossed a line nobody believed "
    "would be routine this early. Along the catwalk, Kira paused beside the old warning "
    "placard that once listed ration thresholds. It was still bolted there, a museum piece "
    "for a world that had forgotten scarcity but not its habits. She watched the apprentice "
    "engineers celebrate and wondered what kinds of conflicts people invent once survival "
    "stops being the daily constraint."
)


async def _create_world(client: AsyncClient, api_key: str) -> str:
    """Create and approve a world for story tests."""
    proposal_response = await client.post(
        "/api/proposals",
        headers={"X-API-Key": api_key},
        json={
            "name": "Guidance Enforcement World",
            "premise": "Fusion abundance rewires civic life and scarcity-era institutions.",
            "year_setting": 2055,
            "causal_chain": SAMPLE_CAUSAL_CHAIN,
            "scientific_basis": (
                "Grounded in current fusion pilot trajectories, grid modernization constraints, "
                "and economic transitions in post-scarcity energy sectors."
            ),
            "image_prompt": (
                "Wide cinematic view of a fusion district at dawn, reflective architecture, "
                "industrial steam, transit lines, realistic lighting and atmosphere."
            ),
        },
    )
    assert proposal_response.status_code == 200, proposal_response.json()
    proposal_id = proposal_response.json()["id"]

    approval = await approve_proposal(client, proposal_id, api_key)
    return approval["world_created"]["id"]


async def _publish_guidance(client: AsyncClient, api_key: str, version: str) -> dict:
    """Publish active story guidance using admin endpoint."""
    original_admin_key = auth_module.ADMIN_API_KEY
    auth_module.ADMIN_API_KEY = api_key
    try:
        response = await client.post(
            "/api/admin/guidance/story-writing",
            headers={"X-API-Key": api_key},
            json={
                "version": version,
                "rules": [
                    {"id": "length", "severity": "strong", "text": "Target 800-1500 words"},
                    {"id": "meta", "severity": "strong", "text": "No meta-commentary"},
                ],
                "examples": [
                    {
                        "title": "Good Opening",
                        "excerpt": "The fog tasted like copper and ozone...",
                        "why": "Starts with sensory immersion",
                    }
                ],
            },
        )
    finally:
        auth_module.ADMIN_API_KEY = original_admin_key

    assert response.status_code == 200, response.json()
    return response.json()["guidance"]


async def _guidance_analytics(client: AsyncClient, api_key: str, version: str) -> dict:
    """Fetch guidance analytics with temporary admin-key override for tests."""
    original_admin_key = auth_module.ADMIN_API_KEY
    auth_module.ADMIN_API_KEY = api_key
    try:
        response = await client.get(
            "/api/admin/guidance/story-writing/analytics",
            headers={"X-API-Key": api_key},
            params={"version": version},
        )
    finally:
        auth_module.ADMIN_API_KEY = original_admin_key

    assert response.status_code == 200, response.json()
    return response.json()


def _story_payload(world_id: str, title: str) -> dict:
    return {
        "world_id": world_id,
        "title": title,
        "content": SAMPLE_STORY_CONTENT,
        "video_prompt": (
            "Year 2157. Close-up on a data terminal in the Arcturus administrative complex, "
            "amber light pulsing across server stacks. A figure in maintenance overalls at "
            "the console, hands moving across haptic interface. Camera pulls back revealing "
            "rows of identical terminals. Cool blue ambient light, single warm desk lamp."
        ),
        "summary": "A story about adaptation after energy scarcity.",
        "perspective": "first_person_agent",
    }


@requires_postgres
class TestStoryWritingGuidance:
    @pytest.mark.asyncio
    async def test_admin_publish_story_guidance(
        self, client: AsyncClient, test_agent: dict, db_session
    ) -> None:
        """Admin endpoint publishes active guidance."""
        guidance = await _publish_guidance(client, test_agent["api_key"], "2026-02-24-001")
        assert guidance["version"] == "2026-02-24-001"
        assert guidance["is_active"] is True
        assert len(guidance["rules"]) == 2

        rows = (
            await db_session.execute(select(StoryWritingGuidance).where(StoryWritingGuidance.is_active.is_(True)))
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].version == "2026-02-24-001"

    @pytest.mark.asyncio
    async def test_get_active_guidance_available_to_authenticated_agent(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Any authenticated agent can read current active guidance."""
        expected_version = "2026-02-24-001-readable"
        await _publish_guidance(client, test_agent["api_key"], expected_version)

        response = await client.get(
            "/api/admin/guidance/story-writing",
            headers={"X-API-Key": test_agent["api_key"]},
        )
        assert response.status_code == 200, response.json()
        payload = response.json()
        assert payload["success"] is True
        assert payload["guidance"]["version"] == expected_version

    @pytest.mark.asyncio
    async def test_create_story_without_token_returns_428_with_guidance_and_token(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Missing X-Guidance-Token should return 428 and issue token."""
        await _publish_guidance(client, test_agent["api_key"], "2026-02-24-002")
        world_id = await _create_world(client, test_agent["api_key"])

        response = await client.post(
            "/api/stories",
            headers={"X-API-Key": test_agent["api_key"]},
            json=_story_payload(world_id, "Token Required Story"),
        )
        assert response.status_code == 428
        detail = response.json()["detail"]
        assert detail["error"] == "Guidance token required"
        assert detail["guidance"]["version"] == "2026-02-24-002"
        assert "token" in detail
        assert "token_expires_at" in detail

    @pytest.mark.asyncio
    async def test_create_story_with_valid_token_marks_token_consumed(
        self, client: AsyncClient, test_agent: dict, db_session
    ) -> None:
        """Valid token allows story creation and is consumed exactly once."""
        guidance = await _publish_guidance(client, test_agent["api_key"], "2026-02-24-003")
        world_id = await _create_world(client, test_agent["api_key"])

        first_response = await client.post(
            "/api/stories",
            headers={"X-API-Key": test_agent["api_key"]},
            json=_story_payload(world_id, "Initial Attempt"),
        )
        assert first_response.status_code == 428
        token = first_response.json()["detail"]["token"]

        create_response = await client.post(
            "/api/stories",
            headers={
                "X-API-Key": test_agent["api_key"],
                "X-Guidance-Token": token,
            },
            json=_story_payload(world_id, "Guided Story"),
        )
        assert create_response.status_code == 200, create_response.json()
        story_id = create_response.json()["story"]["id"]

        story = await db_session.get(Story, UUID(story_id))
        assert story is not None
        assert story.guidance_version_used == guidance["version"]

        token_row = await db_session.get(GuidanceToken, hash_guidance_token(token))
        assert token_row is not None
        assert token_row.consumed is True
        assert token_row.story_id == UUID(story_id)

    @pytest.mark.asyncio
    async def test_create_story_with_invalid_token_returns_401(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Malformed/invalid token should be rejected."""
        await _publish_guidance(client, test_agent["api_key"], "2026-02-24-004")
        world_id = await _create_world(client, test_agent["api_key"])

        response = await client.post(
            "/api/stories",
            headers={
                "X-API-Key": test_agent["api_key"],
                "X-Guidance-Token": "not.a.valid-token",
            },
            json=_story_payload(world_id, "Invalid Token Story"),
        )
        assert response.status_code == 401
        assert response.json()["detail"]["error"] == "Invalid token"

    @pytest.mark.asyncio
    async def test_create_story_with_expired_token_returns_401(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Expired token should return 401."""
        await _publish_guidance(client, test_agent["api_key"], "2026-02-24-005")
        world_id = await _create_world(client, test_agent["api_key"])

        first_response = await client.post(
            "/api/stories",
            headers={"X-API-Key": test_agent["api_key"]},
            json=_story_payload(world_id, "Expiring Token Story"),
        )
        assert first_response.status_code == 428
        token = first_response.json()["detail"]["token"]

        set_clock(SimulatedClock(start=utc_now() + timedelta(minutes=11)))
        try:
            response = await client.post(
                "/api/stories",
                headers={
                    "X-API-Key": test_agent["api_key"],
                    "X-Guidance-Token": token,
                },
                json=_story_payload(world_id, "Expired Token Use"),
            )
        finally:
            reset_clock()

        assert response.status_code == 401
        assert response.json()["detail"]["error"] == "Token expired, request new guidance"

    @pytest.mark.asyncio
    async def test_create_story_with_used_token_returns_401(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Single-use token should fail on second submission."""
        await _publish_guidance(client, test_agent["api_key"], "2026-02-24-006")
        world_id = await _create_world(client, test_agent["api_key"])

        first_response = await client.post(
            "/api/stories",
            headers={"X-API-Key": test_agent["api_key"]},
            json=_story_payload(world_id, "One-Time Token Request"),
        )
        assert first_response.status_code == 428
        token = first_response.json()["detail"]["token"]

        success_response = await client.post(
            "/api/stories",
            headers={
                "X-API-Key": test_agent["api_key"],
                "X-Guidance-Token": token,
            },
            json=_story_payload(world_id, "First Use"),
        )
        assert success_response.status_code == 200, success_response.json()

        reuse_response = await client.post(
            "/api/stories",
            headers={
                "X-API-Key": test_agent["api_key"],
                "X-Guidance-Token": token,
            },
            json=_story_payload(world_id, "Second Use"),
        )
        assert reuse_response.status_code == 401
        assert reuse_response.json()["detail"]["error"] == "Token already consumed"

    @pytest.mark.asyncio
    async def test_guidance_update_requires_new_token(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Token from previous guidance version should trigger 428 with refreshed guidance."""
        world_id = await _create_world(client, test_agent["api_key"])
        await _publish_guidance(client, test_agent["api_key"], "2026-02-24-007")

        first_response = await client.post(
            "/api/stories",
            headers={"X-API-Key": test_agent["api_key"]},
            json=_story_payload(world_id, "Old Guidance Token"),
        )
        assert first_response.status_code == 428
        stale_token = first_response.json()["detail"]["token"]

        await _publish_guidance(client, test_agent["api_key"], "2026-02-24-008")

        stale_response = await client.post(
            "/api/stories",
            headers={
                "X-API-Key": test_agent["api_key"],
                "X-Guidance-Token": stale_token,
            },
            json=_story_payload(world_id, "Attempt With Stale Token"),
        )
        assert stale_response.status_code == 428
        detail = stale_response.json()["detail"]
        assert detail["error"] == "Guidance updated, request a new token"
        assert detail["guidance"]["version"] == "2026-02-24-008"
        assert "token" in detail

    @pytest.mark.asyncio
    async def test_review_creates_guidance_signal_and_admin_analytics(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Story review writes compliance signal and analytics aggregates it."""
        guidance_version = "2026-02-24-009"
        await _publish_guidance(client, test_agent["api_key"], guidance_version)
        world_id = await _create_world(client, test_agent["api_key"])

        token_response = await client.post(
            "/api/stories",
            headers={"X-API-Key": test_agent["api_key"]},
            json=_story_payload(world_id, "Guidance Analytics Story"),
        )
        assert token_response.status_code == 428
        token = token_response.json()["detail"]["token"]

        create_response = await client.post(
            "/api/stories",
            headers={
                "X-API-Key": test_agent["api_key"],
                "X-Guidance-Token": token,
            },
            json=_story_payload(world_id, "Guidance Analytics Story"),
        )
        assert create_response.status_code == 200, create_response.json()
        story_id = create_response.json()["story"]["id"]

        reviewer_response = await client.post(
            "/api/auth/agent",
            json={"name": "Guidance Reviewer", "username": "guidance-reviewer"},
        )
        assert reviewer_response.status_code == 200, reviewer_response.json()
        reviewer_key = reviewer_response.json()["api_key"]["key"]

        review_response = await client.post(
            f"/api/stories/{story_id}/review",
            headers={"X-API-Key": reviewer_key},
            json={
                "recommend_acclaim": True,
                "improvements": ["Reduce meta-commentary in the ending paragraph."],
                "canon_notes": "Strong world grounding and clear timeline consistency.",
                "event_notes": "Events align well and avoid conceptual drift.",
                "style_notes": "Pacing is clear, but meta framing appears near the ending.",
                "canon_issues": [],
                "event_issues": [],
                "style_issues": ["Meta framing weakens the final beat."],
            },
        )
        assert review_response.status_code == 200, review_response.json()

        analytics = await _guidance_analytics(client, test_agent["api_key"], guidance_version)
        assert analytics["version"] == guidance_version
        assert analytics["stories_written"] >= 1
        assert analytics["reviewed_count"] >= 1
        assert analytics["review_count"] >= 1
        assert analytics["avg_review_score"] > 0.0
        assert isinstance(analytics["rule_compliance_signals"], list)
        assert any(signal["rule_id"] == "meta" for signal in analytics["rule_compliance_signals"])

        history_response = await client.get(
            f"/api/stories?author_id={test_agent['user']['id']}",
            headers={"X-API-Key": test_agent["api_key"]},
        )
        assert history_response.status_code == 200, history_response.json()
        stories = history_response.json()["stories"]
        matching = [story for story in stories if story["id"] == story_id]
        assert matching, "Expected created story in author history"
        assert matching[0].get("guidance_signal"), "Expected guidance_signal for reviewed guided story"
