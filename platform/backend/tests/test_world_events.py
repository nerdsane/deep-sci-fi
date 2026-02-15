
"""E2E tests for the World Events system.

Tests the flow:
1. Agent proposes a world event
2. Another agent approves/rejects the event
3. Approved events update world canon
4. Event timeline is maintained
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import approve_proposal


VALID_RESEARCH = (
    "I researched the scientific basis by reviewing ITER progress reports, fusion startup "
    "funding trends, and historical energy cost curves. The causal chain aligns with "
    "mainstream fusion research timelines and economic projections from IEA reports."
)

SAMPLE_CAUSAL_CHAIN = [
    {"year": 2030, "event": "Test event 1", "reasoning": "Test reasoning 1"},
    {"year": 2050, "event": "Test event 2", "reasoning": "Test reasoning 2"},
    {"year": 2070, "event": "Test event 3", "reasoning": "Test reasoning 3"},
]


async def create_world(client: AsyncClient, agent_key: str) -> str:
    """Helper to create and approve a world for testing."""
    # Create proposal
    proposal_response = await client.post(
        "/api/proposals",
        headers={"X-API-Key": agent_key},
        json={
            "name": "Event Test World",
            "premise": "A world for testing the world events system functionality with sufficient detail to meet validation requirements.",
            "year_setting": 2089,
            "causal_chain": SAMPLE_CAUSAL_CHAIN,
            "scientific_basis": "This is a test world for event system testing with sufficient scientific detail to pass validation requirements.",
            "image_prompt": (
                "Cinematic wide shot of a futuristic test facility at golden hour. "
                "Advanced technological infrastructure with dramatic lighting. "
                "Photorealistic, sense of scale and scientific wonder."
            ),
        },
    )
    assert proposal_response.status_code == 200, f"Proposal failed: {proposal_response.json()}"
    proposal_id = proposal_response.json()["id"]

    result = await approve_proposal(client, proposal_id, agent_key)
    return result["world_created"]["id"]


@pytest.mark.asyncio
async def test_propose_world_event(client: AsyncClient):
    """Test proposing a new world event."""
    # Create agent and world
    agent_response = await client.post(
        "/api/auth/agent",
        json={"name": "Event Proposer", "username": "event-proposer"},
    )
    assert agent_response.status_code == 200
    agent_key = agent_response.json()["api_key"]["key"]

    world_id = await create_world(client, agent_key)

    # Propose an event
    event_response = await client.post(
        f"/api/events/worlds/{world_id}/events",
        headers={"X-API-Key": agent_key},
        json={
            "title": "The Great Water Crisis of 2075",
            "description": "A severe drought combined with infrastructure failure leads to "
                          "widespread water shortages across the eastern regions. This forces "
                          "mass migration and establishes water as the primary currency.",
            "year_in_world": 2075,
            "affected_regions": ["Eastern Districts", "Central Hub"],
            "canon_justification": "This event explains the water scarcity themes that emerge "
                                  "in later dweller interactions and provides historical "
                                  "context for the world's economy.",
        },
    )
    assert event_response.status_code == 200, f"Failed: {event_response.json()}"

    event_data = event_response.json()
    assert "event" in event_data
    assert event_data["event"]["title"] == "The Great Water Crisis of 2075"
    assert event_data["event"]["status"] == "pending"
    assert event_data["event"]["year_in_world"] == 2075


@pytest.mark.asyncio
async def test_approve_world_event(client: AsyncClient):
    """Test approving a world event and updating canon."""
    # Create two agents
    agent1_response = await client.post(
        "/api/auth/agent",
        json={"name": "Event Proposer", "username": "event-proposer-2"},
    )
    agent1_key = agent1_response.json()["api_key"]["key"]

    agent2_response = await client.post(
        "/api/auth/agent",
        json={"name": "Event Approver", "username": "event-approver"},
    )
    agent2_key = agent2_response.json()["api_key"]["key"]

    # Create world
    world_id = await create_world(client, agent1_key)

    # Agent 1 proposes event
    event_response = await client.post(
        f"/api/events/worlds/{world_id}/events",
        headers={"X-API-Key": agent1_key},
        json={
            "title": "First Contact Protocol Established",
            "description": "After years of debate, world governments agree on a unified "
                          "protocol for potential extraterrestrial contact. This marks "
                          "a new era of global cooperation.",
            "year_in_world": 2065,
            "affected_regions": [],
            "canon_justification": "This event provides context for the world's unified "
                                  "governance structure and technological optimism.",
        },
    )
    event_id = event_response.json()["event"]["id"]

    # Agent 2 approves event
    approve_response = await client.post(
        f"/api/events/{event_id}/approve",
        headers={"X-API-Key": agent2_key},
        json={
            "canon_update": "WORLD TIMELINE:\n"
                           "2065 - First Contact Protocol established, marking global cooperation.\n"
                           "This unified approach shapes future diplomatic and technological decisions.",
        },
    )
    assert approve_response.status_code == 200

    approve_data = approve_response.json()
    assert approve_data["event"]["status"] == "approved"
    assert approve_data["world_updated"]["canon_summary_updated"] is True

    # Verify event is now approved
    detail_response = await client.get(f"/api/events/{event_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["event"]["status"] == "approved"
    assert "approved_by" in detail_response.json()["event"]


@pytest.mark.asyncio
async def test_reject_world_event(client: AsyncClient):
    """Test rejecting a world event."""
    # Create two agents
    agent1_response = await client.post(
        "/api/auth/agent",
        json={"name": "Bad Proposer", "username": "bad-proposer"},
    )
    agent1_key = agent1_response.json()["api_key"]["key"]

    agent2_response = await client.post(
        "/api/auth/agent",
        json={"name": "Critical Reviewer", "username": "critical-reviewer"},
    )
    agent2_key = agent2_response.json()["api_key"]["key"]

    # Create world
    world_id = await create_world(client, agent1_key)

    # Agent 1 proposes a bad event
    event_response = await client.post(
        f"/api/events/worlds/{world_id}/events",
        headers={"X-API-Key": agent1_key},
        json={
            "title": "Magic Discovered in 2080",
            "description": "Scientists discover that magic is real and everyone can now cast "
                          "spells. This completely changes society as we know it.",
            "year_in_world": 2080,
            "affected_regions": ["Everywhere"],
            "canon_justification": "Magic would make the world more interesting and fun for everyone.",
        },
    )
    event_id = event_response.json()["event"]["id"]

    # Agent 2 rejects event
    reject_response = await client.post(
        f"/api/events/{event_id}/reject",
        headers={"X-API-Key": agent2_key},
        json={
            "reason": "This contradicts the scientific basis of the world. The world is "
                     "grounded in plausible near-future technology, not fantasy elements.",
        },
    )
    assert reject_response.status_code == 200

    reject_data = reject_response.json()
    assert reject_data["event"]["status"] == "rejected"
    assert "rejection_reason" in reject_data["event"]


@pytest.mark.asyncio
async def test_cannot_approve_own_event(client: AsyncClient):
    """Test that agents cannot approve their own events (without test_mode)."""
    agent_response = await client.post(
        "/api/auth/agent",
        json={"name": "Solo Agent", "username": "solo-agent"},
    )
    agent_key = agent_response.json()["api_key"]["key"]

    world_id = await create_world(client, agent_key)

    # Propose event
    event_response = await client.post(
        f"/api/events/worlds/{world_id}/events",
        headers={"X-API-Key": agent_key},
        json={
            "title": "Test Event",
            "description": "A test event that needs at least 50 characters in the description.",
            "year_in_world": 2070,
            "canon_justification": "This is a test event with sufficient justification text.",
        },
    )
    event_id = event_response.json()["event"]["id"]

    # Try to approve own event
    approve_response = await client.post(
        f"/api/events/{event_id}/approve",
        headers={"X-API-Key": agent_key},
        json={
            "canon_update": "Updated canon summary with at least 50 characters of content.",
        },
    )
    assert approve_response.status_code == 400
    assert "Cannot approve your own" in approve_response.json()["detail"]


@pytest.mark.asyncio
async def test_list_world_events(client: AsyncClient):
    """Test listing events for a world (timeline)."""
    agent_response = await client.post(
        "/api/auth/agent",
        json={"name": "Timeline Agent", "username": "timeline-agent"},
    )
    agent_key = agent_response.json()["api_key"]["key"]

    world_id = await create_world(client, agent_key)

    # Create multiple events
    events_data = [
        {"title": "Event A", "year_in_world": 2050},
        {"title": "Event B", "year_in_world": 2060},
        {"title": "Event C", "year_in_world": 2040},  # Earlier year
    ]

    for evt in events_data:
        response = await client.post(
            f"/api/events/worlds/{world_id}/events",
            headers={"X-API-Key": agent_key},
            json={
                "title": evt["title"],
                "description": f"Description for {evt['title']} with sufficient length to meet the minimum 50 character validation requirement.",
                "year_in_world": evt["year_in_world"],
                "canon_justification": f"Justification for {evt['title']} with sufficient length to meet the minimum 50 character requirement.",
            },
        )
        assert response.status_code == 200, f"Event creation failed: {response.json()}"

    # List events
    list_response = await client.get(f"/api/events/worlds/{world_id}/events")
    assert list_response.status_code == 200

    events = list_response.json()["events"]
    assert len(events) == 3

    # Verify ordered by year_in_world
    years = [e["year_in_world"] for e in events]
    assert years == sorted(years)  # Should be [2040, 2050, 2060]


@pytest.mark.asyncio
async def test_event_notification_to_world_creator(client: AsyncClient, db_session: AsyncSession):
    """Test that world creator gets notification when event is proposed."""
    from sqlalchemy import select
    from db import Notification
    from uuid import UUID as UUIDType

    # Create world creator
    creator_response = await client.post(
        "/api/auth/agent",
        json={"name": "World Creator", "username": "event-world-creator"},
    )
    creator_key = creator_response.json()["api_key"]["key"]
    creator_id = creator_response.json()["agent"]["id"]

    # Create another agent
    proposer_response = await client.post(
        "/api/auth/agent",
        json={"name": "Event Proposer", "username": "event-notif-proposer"},
    )
    proposer_key = proposer_response.json()["api_key"]["key"]

    # Creator makes world
    world_id = await create_world(client, creator_key)

    # Proposer proposes event
    event_response = await client.post(
        f"/api/events/worlds/{world_id}/events",
        headers={"X-API-Key": proposer_key},
        json={
            "title": "Notification Test Event",
            "description": "An event to test that notifications are sent to world creators with sufficient detail.",
            "year_in_world": 2070,
            "canon_justification": "This tests the notification system for world events with sufficient justification.",
        },
    )
    assert event_response.status_code == 200, f"Event creation failed: {event_response.json()}"

    # Check creator's notifications via database query
    query = select(Notification).where(
        Notification.user_id == UUIDType(creator_id),
        Notification.notification_type == "world_event_proposed",
    )
    result = await db_session.execute(query)
    notifications = result.scalars().all()

    assert len(notifications) >= 1, "World creator should receive notification when event is proposed"

    # Verify notification data
    notif = notifications[0]
    assert notif.data["event_title"] == "Notification Test Event"
    assert "proposed_by" in notif.data


@pytest.mark.asyncio
async def test_event_year_validation_future(client: AsyncClient):
    """Test that events cannot be too far in the future."""
    agent_response = await client.post(
        "/api/auth/agent",
        json={"name": "Future Agent", "username": "future-agent"},
    )
    agent_key = agent_response.json()["api_key"]["key"]

    world_id = await create_world(client, agent_key)  # World is set in 2089

    # Try to create event too far in the future
    event_response = await client.post(
        f"/api/events/worlds/{world_id}/events",
        headers={"X-API-Key": agent_key},
        json={
            "title": "Far Future Event",
            "description": "An event set way too far in the future for this world's timeline.",
            "year_in_world": 2150,  # World is 2089, this is 61 years later
            "canon_justification": "This should fail because it's too far in the future.",
        },
    )
    assert event_response.status_code == 400
    assert "too far in the future" in event_response.json()["detail"]


@pytest.mark.asyncio
async def test_event_year_validation_past(client: AsyncClient):
    """Test that events cannot be before the world's history begins."""
    agent_response = await client.post(
        "/api/auth/agent",
        json={"name": "Past Agent", "username": "past-agent"},
    )
    agent_key = agent_response.json()["api_key"]["key"]

    world_id = await create_world(client, agent_key)  # Causal chain starts at 2030

    # Try to create event before the world's history
    event_response = await client.post(
        f"/api/events/worlds/{world_id}/events",
        headers={"X-API-Key": agent_key},
        json={
            "title": "Ancient Event",
            "description": "An event set way before the world's timeline begins in the causal chain.",
            "year_in_world": 1990,  # Before the causal chain starts at 2030
            "canon_justification": "This should fail because it's before the world's history.",
        },
    )

    assert event_response.status_code == 400
    assert "before the world's history" in event_response.json()["detail"]
