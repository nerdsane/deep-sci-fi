"""Tests for story revision enforcement gates."""

import os

import pytest
from httpx import AsyncClient

from tests.conftest import (
    SAMPLE_CAUSAL_CHAIN,
    SAMPLE_DWELLER,
    SAMPLE_REGION,
    act_with_context,
    approve_proposal,
)


requires_postgres = pytest.mark.skipif(
    "postgresql" not in os.getenv("TEST_DATABASE_URL", ""),
    reason="Requires PostgreSQL (set TEST_DATABASE_URL)",
)


SAMPLE_STORY_CONTENT = (
    "The corridor lights flickered as the cooling arrays spun up for another night cycle. "
    "Mina traced the numbers on the console and realized the city had crossed another threshold. "
    "What looked like routine maintenance was the hinge point for everything that would follow. "
    "Outside, the district skyline glowed with reactor haze and quiet confidence."
)


SAMPLE_VIDEO_PROMPT = (
    "Year 2164. Tight tracking shot through a maintenance corridor in a fusion citadel, "
    "condensation drifting from coolant pipes. A technician pauses at a holo-console and "
    "runs diagnostics with deliberate hand gestures. Camera orbits slowly to reveal the "
    "reactor chamber beyond reinforced glass. Cold cyan practical lighting, slight lens bloom."
)


@requires_postgres
@pytest.mark.asyncio
async def test_create_story_blocked_until_author_addresses_reviews(client: AsyncClient) -> None:
    """Author cannot create a new story while older stories have unaddressed reviews."""
    author_resp = await client.post(
        "/api/auth/agent",
        json={"name": "Revision Author", "username": "revision-author"},
    )
    assert author_resp.status_code == 200
    author_key = author_resp.json()["api_key"]["key"]

    reviewer_resp = await client.post(
        "/api/auth/agent",
        json={"name": "Revision Reviewer", "username": "revision-reviewer"},
    )
    assert reviewer_resp.status_code == 200
    reviewer_key = reviewer_resp.json()["api_key"]["key"]

    proposal_resp = await client.post(
        "/api/proposals",
        headers={"X-API-Key": author_key},
        json={
            "name": "Revision Gate World",
            "premise": "A city where narrative accountability determines social standing.",
            "year_setting": 2164,
            "causal_chain": SAMPLE_CAUSAL_CHAIN,
            "scientific_basis": (
                "The scenario extrapolates from modern distributed power grids, "
                "urban sensing systems, and social reputation mechanisms with plausible "
                "governance adaptations over multiple decades."
            ),
            "image_prompt": (
                "Cinematic megacity control room, atmospheric haze, layered holographic "
                "interfaces, realistic materials, dramatic but grounded lighting."
            ),
        },
    )
    assert proposal_resp.status_code == 200, f"Proposal creation failed: {proposal_resp.json()}"
    proposal_id = proposal_resp.json()["id"]

    approval = await approve_proposal(client, proposal_id, author_key)
    world_id = approval["world_created"]["id"]

    region_resp = await client.post(
        f"/api/dwellers/worlds/{world_id}/regions",
        headers={"X-API-Key": author_key},
        json=SAMPLE_REGION,
    )
    assert region_resp.status_code == 200, f"Region creation failed: {region_resp.json()}"

    dweller_resp = await client.post(
        f"/api/dwellers/worlds/{world_id}/dwellers",
        headers={"X-API-Key": author_key},
        json=SAMPLE_DWELLER,
    )
    assert dweller_resp.status_code == 200, f"Dweller creation failed: {dweller_resp.json()}"
    dweller_id = dweller_resp.json()["dweller"]["id"]

    claim_resp = await client.post(
        f"/api/dwellers/{dweller_id}/claim",
        headers={"X-API-Key": author_key},
    )
    assert claim_resp.status_code == 200, f"Claim failed: {claim_resp.json()}"

    for i in range(5):
        action_resp = await act_with_context(
            client,
            dweller_id,
            author_key,
            action_type="speak",
            content=f"Action {i}: Calibration pass complete, reporting stable output and clean sensor traces.",
        )
        assert action_resp.status_code == 200, f"Action {i} failed: {action_resp.json()}"

    first_story_resp = await client.post(
        "/api/stories",
        headers={"X-API-Key": author_key},
        json={
            "world_id": world_id,
            "title": "First Chronicle",
            "content": SAMPLE_STORY_CONTENT,
            "video_prompt": SAMPLE_VIDEO_PROMPT,
            "perspective": "first_person_agent",
        },
    )
    assert first_story_resp.status_code == 200, f"First story failed: {first_story_resp.json()}"
    story_id = first_story_resp.json()["story"]["id"]

    review_resp = await client.post(
        f"/api/stories/{story_id}/review",
        headers={"X-API-Key": reviewer_key},
        json={
            "recommend_acclaim": False,
            "improvements": ["Clarify the midpoint transition and consequences."],
            "canon_notes": "Canon alignment is mostly solid, but one transition could be clearer.",
            "event_notes": "Event references are plausible and grounded in observed world activity.",
            "style_notes": "Style and pacing are strong, though one section compresses too much.",
        },
    )
    assert review_resp.status_code == 200, f"Review failed: {review_resp.json()}"
    review_id = review_resp.json()["review"]["id"]

    second_story_payload = {
        "world_id": world_id,
        "title": "Second Chronicle",
        "content": SAMPLE_STORY_CONTENT + " The signal chain now spans the entire district.",
        "video_prompt": SAMPLE_VIDEO_PROMPT,
        "perspective": "first_person_agent",
    }

    blocked_resp = await client.post(
        "/api/stories",
        headers={"X-API-Key": author_key},
        json=second_story_payload,
    )
    assert blocked_resp.status_code == 428
    blocked_detail = blocked_resp.json()["detail"]
    assert blocked_detail["error"] == (
        "You have unaddressed reviews on existing stories. Address them before creating new ones."
    )
    assert "POST /api/stories/{story_id}/reviews/{review_id}/respond" in blocked_detail["how_to_fix"]
    assert "context" in blocked_detail
    assert "unaddressed_stories" in blocked_detail["context"]
    assert blocked_detail["context"]["unaddressed_stories"] == [
        {
            "story_id": story_id,
            "title": "First Chronicle",
            "unaddressed_count": 1,
        }
    ]

    respond_resp = await client.post(
        f"/api/stories/{story_id}/reviews/{review_id}/respond",
        headers={"X-API-Key": author_key},
        json={
            "response": (
                "I addressed the midpoint transition by expanding the causal bridge and "
                "adding clearer consequences for the district grid."
            )
        },
    )
    assert respond_resp.status_code == 200, f"Respond failed: {respond_resp.json()}"

    unblocked_resp = await client.post(
        "/api/stories",
        headers={"X-API-Key": author_key},
        json=second_story_payload,
    )
    assert unblocked_resp.status_code == 200, f"Second story should succeed: {unblocked_resp.json()}"
    assert unblocked_resp.json()["story"]["title"] == "Second Chronicle"
