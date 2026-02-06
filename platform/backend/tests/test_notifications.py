"""E2E tests for the notification system."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import approve_proposal, VALID_RESEARCH, act_with_context, get_context_token


@pytest.mark.asyncio
async def test_dweller_speech_creates_notification(client: AsyncClient):
    """When dweller A speaks to dweller B, B's inhabitant gets a notification."""
    # Create two agents
    agent1_response = await client.post(
        "/api/auth/agent",
        json={
            "name": "Agent One",
            "username": "agent-one-notif",
            "callback_url": "https://example.com/callback1",
        },
    )
    assert agent1_response.status_code == 200
    agent1_key = agent1_response.json()["api_key"]["key"]

    agent2_response = await client.post(
        "/api/auth/agent",
        json={
            "name": "Agent Two",
            "username": "agent-two-notif",
            "callback_url": "https://example.com/callback2",
        },
    )
    assert agent2_response.status_code == 200
    agent2_key = agent2_response.json()["api_key"]["key"]

    # Agent 1 creates a proposal and self-validates to create a world
    proposal_response = await client.post(
        "/api/proposals",
        headers={"X-API-Key": agent1_key},
        json={
            "name": "Notification Test World",
            "premise": "A world for testing the notification system with dweller interactions.",
            "year_setting": 2089,
            "causal_chain": [
                {"year": 2030, "event": "Test event 1", "reasoning": "Test reasoning 1"},
                {"year": 2050, "event": "Test event 2", "reasoning": "Test reasoning 2"},
                {"year": 2070, "event": "Test event 3", "reasoning": "Test reasoning 3"},
            ],
            "scientific_basis": "This is a test world for notification testing purposes.",
        },
    )
    assert proposal_response.status_code == 200
    proposal_id = proposal_response.json()["id"]

    result = await approve_proposal(client, proposal_id, agent1_key)
    world_id = result["world_created"]["id"]

    # Add a region
    region_response = await client.post(
        f"/api/dwellers/worlds/{world_id}/regions",
        headers={"X-API-Key": agent1_key},
        json={
            "name": "Test Region",
            "location": "Test location",
            "population_origins": ["Test origin"],
            "cultural_blend": "Test cultural blend description",
            "naming_conventions": "Test naming conventions for the region",
            "language": "Test language",
        },
    )
    assert region_response.status_code == 200

    # Create two dwellers
    dweller1_response = await client.post(
        f"/api/dwellers/worlds/{world_id}/dwellers",
        headers={"X-API-Key": agent1_key},
        json={
            "name": "Alice",
            "origin_region": "Test Region",
            "generation": "First-gen",
            "name_context": "Test name context for Alice in this test world",
            "cultural_identity": "Test cultural identity for Alice",
            "role": "Test role",
            "age": 30,
            "personality": "Test personality description that is long enough to pass validation",
            "background": "Test background description that is long enough to pass validation",
        },
    )
    assert dweller1_response.status_code == 200
    dweller1_id = dweller1_response.json()["dweller"]["id"]

    dweller2_response = await client.post(
        f"/api/dwellers/worlds/{world_id}/dwellers",
        headers={"X-API-Key": agent1_key},
        json={
            "name": "Bob",
            "origin_region": "Test Region",
            "generation": "First-gen",
            "name_context": "Test name context for Bob in this test world",
            "cultural_identity": "Test cultural identity for Bob",
            "role": "Test role",
            "age": 35,
            "personality": "Test personality description that is long enough to pass validation",
            "background": "Test background description that is long enough to pass validation",
        },
    )
    assert dweller2_response.status_code == 200
    dweller2_id = dweller2_response.json()["dweller"]["id"]

    # Agent 1 claims Alice
    claim1_response = await client.post(
        f"/api/dwellers/{dweller1_id}/claim",
        headers={"X-API-Key": agent1_key},
    )
    assert claim1_response.status_code == 200

    # Agent 2 claims Bob
    claim2_response = await client.post(
        f"/api/dwellers/{dweller2_id}/claim",
        headers={"X-API-Key": agent2_key},
    )
    assert claim2_response.status_code == 200

    # Alice (Agent 1) speaks to Bob (two-phase: context → act)
    speak_response = await act_with_context(
        client, dweller1_id, agent1_key,
        action_type="speak", target="Bob",
        content="Hello Bob, how are you today?",
    )
    assert speak_response.status_code == 200
    assert speak_response.json()["notification"]["target_notified"] is True

    # Check that Agent 2 has a pending notification
    pending_response = await client.get(
        f"/api/dwellers/{dweller2_id}/pending",
        headers={"X-API-Key": agent2_key},
    )
    assert pending_response.status_code == 200
    pending_data = pending_response.json()

    # Should have at least one notification
    assert pending_data["total_pending"] >= 1 or pending_data["total_mentions"] >= 1

    # Check the notification content
    if pending_data["total_pending"] > 0:
        notification = pending_data["pending_notifications"][0]
        assert notification["type"] == "dweller_spoken_to"
        assert notification["data"]["from_dweller"] == "Alice"
        assert "Hello Bob" in notification["data"]["content"]


@pytest.mark.asyncio
async def test_speech_to_uninhabited_dweller_no_notification(client: AsyncClient):
    """Speaking to an uninhabited dweller should not create a notification."""
    # Create agent
    agent_response = await client.post(
        "/api/auth/agent",
        json={
            "name": "Solo Agent",
            "username": "solo-agent-notif",
        },
    )
    assert agent_response.status_code == 200
    agent_key = agent_response.json()["api_key"]["key"]

    # Create proposal and world
    proposal_response = await client.post(
        "/api/proposals",
        headers={"X-API-Key": agent_key},
        json={
            "name": "Solo Test World",
            "premise": "A world for testing speech to uninhabited dwellers.",
            "year_setting": 2089,
            "causal_chain": [
                {"year": 2030, "event": "Test event one for validation", "reasoning": "Test reasoning one"},
                {"year": 2050, "event": "Test event two for validation", "reasoning": "Test reasoning two"},
                {"year": 2070, "event": "Test event three for validation", "reasoning": "Test reasoning three"},
            ],
            "scientific_basis": "Test scientific basis for the solo test world with sufficient length.",
        },
    )
    assert proposal_response.status_code == 200
    proposal_id = proposal_response.json()["id"]

    result = await approve_proposal(client, proposal_id, agent_key)
    world_id = result["world_created"]["id"]

    # Add region
    await client.post(
        f"/api/dwellers/worlds/{world_id}/regions",
        headers={"X-API-Key": agent_key},
        json={
            "name": "Solo Region",
            "location": "Test location",
            "population_origins": ["Test"],
            "cultural_blend": "Test cultural blend for solo region",
            "naming_conventions": "Test naming conventions for solo region",
            "language": "Test language",
        },
    )

    # Create two dwellers
    dweller1_response = await client.post(
        f"/api/dwellers/worlds/{world_id}/dwellers",
        headers={"X-API-Key": agent_key},
        json={
            "name": "Speaker",
            "origin_region": "Solo Region",
            "generation": "First-gen",
            "name_context": "Test name context for Speaker",
            "cultural_identity": "Test cultural identity",
            "role": "Test role",
            "age": 30,
            "personality": "Test personality that is long enough for validation",
            "background": "Test background that is long enough for validation",
        },
    )
    dweller1_id = dweller1_response.json()["dweller"]["id"]

    dweller2_response = await client.post(
        f"/api/dwellers/worlds/{world_id}/dwellers",
        headers={"X-API-Key": agent_key},
        json={
            "name": "Listener",
            "origin_region": "Solo Region",
            "generation": "First-gen",
            "name_context": "Test name context for Listener",
            "cultural_identity": "Test cultural identity",
            "role": "Test role",
            "age": 35,
            "personality": "Test personality that is long enough for validation",
            "background": "Test background that is long enough for validation",
        },
    )
    dweller2_id = dweller2_response.json()["dweller"]["id"]

    # Only claim the speaker, leave listener uninhabited
    await client.post(
        f"/api/dwellers/{dweller1_id}/claim",
        headers={"X-API-Key": agent_key},
    )

    # Speaker speaks to Listener (uninhabited) — two-phase flow
    speak_response = await act_with_context(
        client, dweller1_id, agent_key,
        action_type="speak", target="Listener",
        content="Hello Listener, anyone there?",
    )
    assert speak_response.status_code == 200
    # Should indicate target was not notified
    assert speak_response.json()["notification"]["target_notified"] is False


@pytest.mark.asyncio
async def test_speech_to_nonexistent_dweller_no_notification(client: AsyncClient):
    """Speaking to a dweller that doesn't exist should not crash."""
    # Create agent
    agent_response = await client.post(
        "/api/auth/agent",
        json={
            "name": "Lonely Agent",
            "username": "lonely-agent-notif",
        },
    )
    assert agent_response.status_code == 200
    agent_key = agent_response.json()["api_key"]["key"]

    # Create proposal and world
    proposal_response = await client.post(
        "/api/proposals",
        headers={"X-API-Key": agent_key},
        json={
            "name": "Lonely Test World",
            "premise": "A world for testing speech to nonexistent dwellers.",
            "year_setting": 2089,
            "causal_chain": [
                {"year": 2030, "event": "Test event one for validation", "reasoning": "Test reasoning one"},
                {"year": 2050, "event": "Test event two for validation", "reasoning": "Test reasoning two"},
                {"year": 2070, "event": "Test event three for validation", "reasoning": "Test reasoning three"},
            ],
            "scientific_basis": "Test scientific basis for the lonely test world with enough length.",
        },
    )
    proposal_id = proposal_response.json()["id"]

    result = await approve_proposal(client, proposal_id, agent_key)
    world_id = result["world_created"]["id"]

    # Add region
    await client.post(
        f"/api/dwellers/worlds/{world_id}/regions",
        headers={"X-API-Key": agent_key},
        json={
            "name": "Lonely Region",
            "location": "Test location",
            "population_origins": ["Test"],
            "cultural_blend": "Test cultural blend for lonely region",
            "naming_conventions": "Test naming conventions for lonely region",
            "language": "Test language",
        },
    )

    # Create only one dweller
    dweller_response = await client.post(
        f"/api/dwellers/worlds/{world_id}/dwellers",
        headers={"X-API-Key": agent_key},
        json={
            "name": "Lonely",
            "origin_region": "Lonely Region",
            "generation": "First-gen",
            "name_context": "Test name context for Lonely",
            "cultural_identity": "Test cultural identity",
            "role": "Test role",
            "age": 30,
            "personality": "Test personality that is long enough for validation",
            "background": "Test background that is long enough for validation",
        },
    )
    dweller_id = dweller_response.json()["dweller"]["id"]

    # Claim the dweller
    await client.post(
        f"/api/dwellers/{dweller_id}/claim",
        headers={"X-API-Key": agent_key},
    )

    # Speak to nonexistent dweller — two-phase flow, act should fail on target validation
    speak_response = await act_with_context(
        client, dweller_id, agent_key,
        action_type="speak", target="Nobody",
        content="Is anyone out there?",
    )
    # Speak actions validate that the target dweller exists in the world
    assert speak_response.status_code == 400
    assert "not found" in speak_response.json()["detail"]["error"].lower()


@pytest.mark.asyncio
async def test_mark_notifications_as_read(client: AsyncClient):
    """Notifications can be marked as read when fetching pending."""
    # Create two agents
    agent1_response = await client.post(
        "/api/auth/agent",
        json={"name": "Reader Agent 1", "username": "reader-agent-1"},
    )
    agent1_key = agent1_response.json()["api_key"]["key"]

    agent2_response = await client.post(
        "/api/auth/agent",
        json={"name": "Reader Agent 2", "username": "reader-agent-2"},
    )
    agent2_key = agent2_response.json()["api_key"]["key"]

    # Create world
    proposal_response = await client.post(
        "/api/proposals",
        headers={"X-API-Key": agent1_key},
        json={
            "name": "Reader Test World",
            "premise": "A world for testing marking notifications as read.",
            "year_setting": 2089,
            "causal_chain": [
                {"year": 2030, "event": "Test event one for validation", "reasoning": "Test reasoning one"},
                {"year": 2050, "event": "Test event two for validation", "reasoning": "Test reasoning two"},
                {"year": 2070, "event": "Test event three for validation", "reasoning": "Test reasoning three"},
            ],
            "scientific_basis": "Test scientific basis for reader test world with enough characters.",
        },
    )
    proposal_id = proposal_response.json()["id"]

    result = await approve_proposal(client, proposal_id, agent1_key)
    world_id = result["world_created"]["id"]

    # Add region and dwellers
    await client.post(
        f"/api/dwellers/worlds/{world_id}/regions",
        headers={"X-API-Key": agent1_key},
        json={
            "name": "Reader Region",
            "location": "Test location",
            "population_origins": ["Test origin"],
            "cultural_blend": "Test cultural blend description",
            "naming_conventions": "Test naming conventions for the region",
            "language": "Test language",
        },
    )

    d1_response = await client.post(
        f"/api/dwellers/worlds/{world_id}/dwellers",
        headers={"X-API-Key": agent1_key},
        json={
            "name": "Sender",
            "origin_region": "Reader Region",
            "generation": "First-gen",
            "name_context": "Test name context for Sender in this test world",
            "cultural_identity": "Test cultural identity for Sender",
            "role": "Test role",
            "age": 30,
            "personality": "Test personality description that is long enough to pass validation",
            "background": "Test background description that is long enough to pass validation",
        },
    )
    d1_id = d1_response.json()["dweller"]["id"]

    d2_response = await client.post(
        f"/api/dwellers/worlds/{world_id}/dwellers",
        headers={"X-API-Key": agent1_key},
        json={
            "name": "Receiver",
            "origin_region": "Reader Region",
            "generation": "First-gen",
            "name_context": "Test name context for Receiver in this test world",
            "cultural_identity": "Test cultural identity for Receiver",
            "role": "Test role",
            "age": 35,
            "personality": "Test personality description that is long enough to pass validation",
            "background": "Test background description that is long enough to pass validation",
        },
    )
    d2_id = d2_response.json()["dweller"]["id"]

    # Claim dwellers
    await client.post(f"/api/dwellers/{d1_id}/claim", headers={"X-API-Key": agent1_key})
    await client.post(f"/api/dwellers/{d2_id}/claim", headers={"X-API-Key": agent2_key})

    # Send message (two-phase flow)
    await act_with_context(
        client, d1_id, agent1_key,
        action_type="speak", target="Receiver",
        content="Test message",
    )

    # Get pending without marking read
    pending1 = await client.get(
        f"/api/dwellers/{d2_id}/pending",
        headers={"X-API-Key": agent2_key},
    )
    count_before = pending1.json()["total_pending"]
    assert count_before >= 1, "Should have at least one pending notification"

    # Get pending with mark_read=true
    pending2 = await client.get(
        f"/api/dwellers/{d2_id}/pending?mark_read=true",
        headers={"X-API-Key": agent2_key},
    )
    # Should still return the notifications this time
    assert pending2.status_code == 200

    # Get pending again - should have fewer (the ones we just read)
    pending3 = await client.get(
        f"/api/dwellers/{d2_id}/pending",
        headers={"X-API-Key": agent2_key},
    )
    # The marked-as-read notifications should no longer appear
    assert pending3.json()["total_pending"] == 0


@pytest.mark.asyncio
async def test_notification_contains_correct_data(client: AsyncClient):
    """Notification data should include all required fields."""
    # Create two agents
    agent1_response = await client.post(
        "/api/auth/agent",
        json={"name": "Data Agent 1", "username": "data-agent-1"},
    )
    agent1_key = agent1_response.json()["api_key"]["key"]

    agent2_response = await client.post(
        "/api/auth/agent",
        json={"name": "Data Agent 2", "username": "data-agent-2"},
    )
    agent2_key = agent2_response.json()["api_key"]["key"]

    # Create world
    proposal_response = await client.post(
        "/api/proposals",
        headers={"X-API-Key": agent1_key},
        json={
            "name": "Data Test World",
            "premise": "A world for testing notification data structure and validation.",
            "year_setting": 2089,
            "causal_chain": [
                {"year": 2030, "event": "Test event one for validation", "reasoning": "Test reasoning one"},
                {"year": 2050, "event": "Test event two for validation", "reasoning": "Test reasoning two"},
                {"year": 2070, "event": "Test event three for validation", "reasoning": "Test reasoning three"},
            ],
            "scientific_basis": "Test scientific basis with sufficient characters for validation.",
        },
    )
    proposal_id = proposal_response.json()["id"]

    result = await approve_proposal(client, proposal_id, agent1_key)
    world_id = result["world_created"]["id"]

    # Add region and dwellers
    await client.post(
        f"/api/dwellers/worlds/{world_id}/regions",
        headers={"X-API-Key": agent1_key},
        json={
            "name": "Data Region",
            "location": "Test location",
            "population_origins": ["Test origin"],
            "cultural_blend": "Test cultural blend description",
            "naming_conventions": "Test naming conventions for the region",
            "language": "Test language",
        },
    )

    d1_response = await client.post(
        f"/api/dwellers/worlds/{world_id}/dwellers",
        headers={"X-API-Key": agent1_key},
        json={
            "name": "DataSender",
            "origin_region": "Data Region",
            "generation": "First-gen",
            "name_context": "Test name context for DataSender",
            "cultural_identity": "Test cultural identity for DataSender",
            "role": "Test role",
            "age": 30,
            "personality": "Test personality description that is long enough to pass validation",
            "background": "Test background description that is long enough to pass validation",
        },
    )
    d1_id = d1_response.json()["dweller"]["id"]

    d2_response = await client.post(
        f"/api/dwellers/worlds/{world_id}/dwellers",
        headers={"X-API-Key": agent1_key},
        json={
            "name": "DataReceiver",
            "origin_region": "Data Region",
            "generation": "First-gen",
            "name_context": "Test name context for DataReceiver",
            "cultural_identity": "Test cultural identity for DataReceiver",
            "role": "Test role",
            "age": 35,
            "personality": "Test personality description that is long enough to pass validation",
            "background": "Test background description that is long enough to pass validation",
        },
    )
    d2_id = d2_response.json()["dweller"]["id"]

    # Claim dwellers
    await client.post(f"/api/dwellers/{d1_id}/claim", headers={"X-API-Key": agent1_key})
    await client.post(f"/api/dwellers/{d2_id}/claim", headers={"X-API-Key": agent2_key})

    # Send message with specific content
    test_content = "This is a specific test message for data validation"
    speak_response = await act_with_context(
        client, d1_id, agent1_key,
        action_type="speak", target="DataReceiver",
        content=test_content,
    )
    action_id = speak_response.json()["action"]["id"]

    # Get pending and verify data structure
    pending = await client.get(
        f"/api/dwellers/{d2_id}/pending",
        headers={"X-API-Key": agent2_key},
    )

    assert pending.json()["total_pending"] >= 1
    notification = pending.json()["pending_notifications"][0]

    # Verify notification structure
    assert notification["type"] == "dweller_spoken_to"
    assert "id" in notification
    assert "created_at" in notification

    # Verify notification data
    data = notification["data"]
    assert data["from_dweller"] == "DataSender"
    assert data["from_dweller_id"] == d1_id
    assert data["action_id"] == action_id
    assert data["content"] == test_content


@pytest.mark.asyncio
async def test_proposal_validation_creates_notification(client: AsyncClient, db_session: AsyncSession):
    """When agent B validates agent A's proposal, A gets a notification."""
    from sqlalchemy import select
    from db import Notification

    # Create two agents
    agent1_response = await client.post(
        "/api/auth/agent",
        json={"name": "Proposal Owner", "username": "proposal-owner-notif"},
    )
    agent1_key = agent1_response.json()["api_key"]["key"]
    agent1_id = agent1_response.json()["agent"]["id"]

    agent2_response = await client.post(
        "/api/auth/agent",
        json={"name": "Proposal Validator", "username": "proposal-validator-notif"},
    )
    agent2_key = agent2_response.json()["api_key"]["key"]

    agent3_response = await client.post(
        "/api/auth/agent",
        json={"name": "Second Validator", "username": "proposal-validator2-notif"},
    )
    agent3_key = agent3_response.json()["api_key"]["key"]

    # Agent 1 creates a proposal
    proposal_response = await client.post(
        "/api/proposals",
        headers={"X-API-Key": agent1_key},
        json={
            "name": "Notification Proposal Test",
            "premise": "A world for testing proposal validation notifications.",
            "year_setting": 2089,
            "causal_chain": [
                {"year": 2030, "event": "Test event one for validation", "reasoning": "Test reasoning one"},
                {"year": 2050, "event": "Test event two for validation", "reasoning": "Test reasoning two"},
                {"year": 2070, "event": "Test event three for validation", "reasoning": "Test reasoning three"},
            ],
            "scientific_basis": "Test scientific basis with sufficient length for validation testing.",
        },
    )
    assert proposal_response.status_code == 200
    proposal_id = proposal_response.json()["id"]

    # Submit proposal
    await client.post(
        f"/api/proposals/{proposal_id}/submit",
        headers={"X-API-Key": agent1_key},
    )

    # Agent 2 validates the proposal (first approval — APPROVAL_THRESHOLD=2)
    validate_response = await client.post(
        f"/api/proposals/{proposal_id}/validate",
        headers={"X-API-Key": agent2_key},
        json={
            "verdict": "approve",
            "research_conducted": VALID_RESEARCH,
            "critique": "This is a great proposal! Approved for testing notifications.",
            "scientific_issues": [],
            "suggested_fixes": [],
            "weaknesses": ["Timeline optimism in intermediate steps"],
        },
    )
    assert validate_response.status_code == 200

    # Agent 3 validates (second approval — triggers approval)
    validate2_response = await client.post(
        f"/api/proposals/{proposal_id}/validate",
        headers={"X-API-Key": agent3_key},
        json={
            "verdict": "approve",
            "research_conducted": VALID_RESEARCH,
            "critique": "Second approval for notification test with solid scientific basis and reasoning.",
            "scientific_issues": [],
            "suggested_fixes": [],
            "weaknesses": ["Timeline optimism in intermediate steps"],
        },
    )
    assert validate2_response.status_code == 200

    # Check that notifications were created for agent 1
    query = select(Notification).where(Notification.user_id == agent1_id)
    result = await db_session.execute(query)
    notifications = result.scalars().all()

    # Should have validation notifications and status change notification
    notification_types = [n.notification_type for n in notifications]
    assert "proposal_validated" in notification_types, "Should have proposal_validated notification"
    assert "proposal_status_changed" in notification_types, "Should have proposal_status_changed notification"

    # Verify validation notification content (from agent2)
    validation_notif = next(n for n in notifications if n.notification_type == "proposal_validated")
    assert validation_notif.data["verdict"] == "approve"

    # Verify status change notification content
    status_notif = next(n for n in notifications if n.notification_type == "proposal_status_changed")
    assert status_notif.data["new_status"] == "approved"
    assert "world_id" in status_notif.data


@pytest.mark.asyncio
async def test_aspect_validation_creates_notification(client: AsyncClient, db_session: AsyncSession):
    """When agent B validates agent A's aspect, A gets a notification."""
    from sqlalchemy import select
    from db import Notification

    # Create two agents
    agent1_response = await client.post(
        "/api/auth/agent",
        json={"name": "Aspect Owner", "username": "aspect-owner-notif"},
    )
    agent1_key = agent1_response.json()["api_key"]["key"]
    agent1_id = agent1_response.json()["agent"]["id"]

    agent2_response = await client.post(
        "/api/auth/agent",
        json={"name": "Aspect Validator", "username": "aspect-validator-notif"},
    )
    agent2_key = agent2_response.json()["api_key"]["key"]

    # Agent 1 creates a proposal and world
    proposal_response = await client.post(
        "/api/proposals",
        headers={"X-API-Key": agent1_key},
        json={
            "name": "Aspect Notification Test World",
            "premise": "A world for testing aspect validation notifications.",
            "year_setting": 2089,
            "causal_chain": [
                {"year": 2030, "event": "Test event one for validation", "reasoning": "Test reasoning one"},
                {"year": 2050, "event": "Test event two for validation", "reasoning": "Test reasoning two"},
                {"year": 2070, "event": "Test event three for validation", "reasoning": "Test reasoning three"},
            ],
            "scientific_basis": "Test scientific basis with sufficient length for validation testing.",
        },
    )
    proposal_id = proposal_response.json()["id"]

    result = await approve_proposal(client, proposal_id, agent1_key)
    world_id = result["world_created"]["id"]

    # Agent 1 creates an aspect
    aspect_response = await client.post(
        f"/api/aspects/worlds/{world_id}/aspects",
        headers={"X-API-Key": agent1_key},
        json={
            "aspect_type": "technology",
            "title": "Notification Test Technology",
            "premise": "A technology for testing aspect notifications.",
            "content": {"name": "Test Tech", "description": "A test technology for notification testing purposes."},
            "canon_justification": "This technology fits the world's scientific basis and timeline perfectly.",
        },
    )
    assert aspect_response.status_code == 200
    aspect_id = aspect_response.json()["aspect"]["id"]

    # Submit aspect
    await client.post(
        f"/api/aspects/{aspect_id}/submit",
        headers={"X-API-Key": agent1_key},
    )

    # Clear notifications from proposal validation
    await db_session.execute(
        Notification.__table__.delete().where(Notification.user_id == agent1_id)
    )
    await db_session.commit()

    # Agent 2 validates the aspect
    validate_aspect_response = await client.post(
        f"/api/aspects/{aspect_id}/validate",
        headers={"X-API-Key": agent2_key},
        json={
            "verdict": "approve",
            "research_conducted": VALID_RESEARCH,
            "critique": "This is a great aspect! Approved for testing notifications.",
            "canon_conflicts": [],
            "suggested_fixes": [],
            "updated_canon_summary": "The world now includes this new notification test technology that is part of the canon.",
        },
    )
    assert validate_aspect_response.status_code == 200

    # Check that notifications were created for agent 1
    query = select(Notification).where(Notification.user_id == agent1_id)
    result = await db_session.execute(query)
    notifications = result.scalars().all()

    # Should have aspect validation notification
    assert len(notifications) >= 1, "Should have at least one notification"
    notification_types = [n.notification_type for n in notifications]
    assert "aspect_validated" in notification_types, "Should have aspect_validated notification"

    # Verify notification content
    validation_notif = next(n for n in notifications if n.notification_type == "aspect_validated")
    assert validation_notif.data["validator"] == "Aspect Validator"
    assert validation_notif.data["verdict"] == "approve"
    assert validation_notif.data["aspect_title"] == "Notification Test Technology"


@pytest.mark.asyncio
async def test_revision_suggestion_flow(client: AsyncClient):
    """Test the full revision suggestion flow: suggest, upvote, accept."""
    # Create two agents
    agent1_response = await client.post(
        "/api/auth/agent",
        json={"name": "Proposal Owner", "username": "proposal-owner-sugg"},
    )
    agent1_key = agent1_response.json()["api_key"]["key"]

    agent2_response = await client.post(
        "/api/auth/agent",
        json={"name": "Suggester Agent", "username": "suggester-agent"},
    )
    agent2_key = agent2_response.json()["api_key"]["key"]

    # Agent 1 creates a proposal
    proposal_response = await client.post(
        "/api/proposals",
        headers={"X-API-Key": agent1_key},
        json={
            "name": "Suggestion Test Proposal",
            "premise": "A world for testing the revision suggestion flow works correctly.",
            "year_setting": 2089,
            "causal_chain": [
                {"year": 2030, "event": "Test event one for validation", "reasoning": "Test reasoning one"},
                {"year": 2050, "event": "Test event two for validation", "reasoning": "Test reasoning two"},
                {"year": 2070, "event": "Test event three for validation", "reasoning": "Test reasoning three"},
            ],
            "scientific_basis": "Test scientific basis with sufficient length for validation testing.",
        },
    )
    assert proposal_response.status_code == 200
    proposal_id = proposal_response.json()["id"]

    # Submit proposal
    await client.post(
        f"/api/proposals/{proposal_id}/submit",
        headers={"X-API-Key": agent1_key},
    )

    # Agent 2 suggests a revision
    suggest_response = await client.post(
        f"/api/suggestions/proposals/{proposal_id}/suggest-revision",
        headers={"X-API-Key": agent2_key},
        json={
            "field": "premise",
            "suggested_value": "An improved premise for this world that is better worded and more descriptive.",
            "rationale": "The original premise was too vague. This version is more specific and compelling.",
        },
    )
    assert suggest_response.status_code == 200
    suggestion_id = suggest_response.json()["suggestion"]["id"]
    assert suggest_response.json()["suggestion"]["status"] == "pending"

    # List suggestions on proposal
    list_response = await client.get(
        f"/api/suggestions/proposals/{proposal_id}/suggestions",
        headers={"X-API-Key": agent1_key},
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["pending_count"] == 1

    # Get the suggestion details
    get_response = await client.get(
        f"/api/suggestions/{suggestion_id}",
        headers={"X-API-Key": agent1_key},
    )
    assert get_response.status_code == 200
    assert get_response.json()["suggestion"]["field"] == "premise"

    # Owner accepts the suggestion
    accept_response = await client.post(
        f"/api/suggestions/{suggestion_id}/accept",
        headers={"X-API-Key": agent1_key},
        json={"reason": "Good suggestion, this improves the proposal significantly."},
    )
    assert accept_response.status_code == 200
    assert accept_response.json()["status"] == "accepted"
    assert accept_response.json()["accepted_by"] == "owner"

    # Verify the proposal was updated
    proposal_detail = await client.get(
        f"/api/proposals/{proposal_id}",
        headers={"X-API-Key": agent1_key},
    )
    assert proposal_detail.status_code == 200
    assert "improved premise" in proposal_detail.json()["proposal"]["premise"]


@pytest.mark.asyncio
async def test_suggestion_owner_can_reject(client: AsyncClient):
    """Test that owner can reject suggestions."""
    # Create two agents
    agent1_response = await client.post(
        "/api/auth/agent",
        json={"name": "Reject Owner", "username": "reject-owner"},
    )
    agent1_key = agent1_response.json()["api_key"]["key"]

    agent2_response = await client.post(
        "/api/auth/agent",
        json={"name": "Reject Suggester", "username": "reject-suggester"},
    )
    agent2_key = agent2_response.json()["api_key"]["key"]

    # Create proposal
    proposal_response = await client.post(
        "/api/proposals",
        headers={"X-API-Key": agent1_key},
        json={
            "name": "Reject Test Proposal",
            "premise": "A world for testing rejection of revision suggestions.",
            "year_setting": 2089,
            "causal_chain": [
                {"year": 2030, "event": "Test event one for validation", "reasoning": "Test reasoning one"},
                {"year": 2050, "event": "Test event two for validation", "reasoning": "Test reasoning two"},
                {"year": 2070, "event": "Test event three for validation", "reasoning": "Test reasoning three"},
            ],
            "scientific_basis": "Test scientific basis with sufficient length for validation testing.",
        },
    )
    proposal_id = proposal_response.json()["id"]
    await client.post(f"/api/proposals/{proposal_id}/submit", headers={"X-API-Key": agent1_key})

    # Suggest revision
    suggest_response = await client.post(
        f"/api/suggestions/proposals/{proposal_id}/suggest-revision",
        headers={"X-API-Key": agent2_key},
        json={
            "field": "premise",
            "suggested_value": "A bad suggestion that should be rejected.",
            "rationale": "This is a bad rationale for testing rejection.",
        },
    )
    suggestion_id = suggest_response.json()["suggestion"]["id"]

    # Owner rejects
    reject_response = await client.post(
        f"/api/suggestions/{suggestion_id}/reject",
        headers={"X-API-Key": agent1_key},
        json={"reason": "This suggestion doesn't improve the proposal."},
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "rejected"

    # Verify proposal is unchanged
    proposal_detail = await client.get(f"/api/proposals/{proposal_id}")
    assert "bad suggestion" not in proposal_detail.json()["proposal"]["premise"]


@pytest.mark.asyncio
async def test_cannot_suggest_own_proposal(client: AsyncClient):
    """Test that you cannot suggest revision to your own proposal."""
    agent_response = await client.post(
        "/api/auth/agent",
        json={"name": "Self Suggester", "username": "self-suggester"},
    )
    agent_key = agent_response.json()["api_key"]["key"]

    # Create proposal
    proposal_response = await client.post(
        "/api/proposals",
        headers={"X-API-Key": agent_key},
        json={
            "name": "Self Suggest Test",
            "premise": "A world for testing self-suggestion prevention works correctly.",
            "year_setting": 2089,
            "causal_chain": [
                {"year": 2030, "event": "Test event one for validation", "reasoning": "Test reasoning one"},
                {"year": 2050, "event": "Test event two for validation", "reasoning": "Test reasoning two"},
                {"year": 2070, "event": "Test event three for validation", "reasoning": "Test reasoning three"},
            ],
            "scientific_basis": "Test scientific basis with sufficient length for validation testing.",
        },
    )
    assert proposal_response.status_code == 200
    proposal_id = proposal_response.json()["id"]

    # Try to suggest revision to own proposal
    suggest_response = await client.post(
        f"/api/suggestions/proposals/{proposal_id}/suggest-revision",
        headers={"X-API-Key": agent_key},
        json={
            "field": "premise",
            "suggested_value": "Self-suggested change",
            "rationale": "Testing self-suggestion should fail",
        },
    )
    assert suggest_response.status_code == 400
    assert "Cannot suggest revision to your own" in suggest_response.json()["detail"]


@pytest.mark.asyncio
async def test_suggestion_creates_notification(client: AsyncClient, db_session: AsyncSession):
    """Test that suggesting a revision notifies the owner."""
    from sqlalchemy import select
    from db import Notification

    # Create two agents
    agent1_response = await client.post(
        "/api/auth/agent",
        json={"name": "Notified Owner", "username": "notified-owner"},
    )
    agent1_key = agent1_response.json()["api_key"]["key"]
    agent1_id = agent1_response.json()["agent"]["id"]

    agent2_response = await client.post(
        "/api/auth/agent",
        json={"name": "Notifying Suggester", "username": "notifying-suggester"},
    )
    agent2_key = agent2_response.json()["api_key"]["key"]

    # Create proposal
    proposal_response = await client.post(
        "/api/proposals",
        headers={"X-API-Key": agent1_key},
        json={
            "name": "Notification Suggest Test",
            "premise": "A world for testing suggestion notifications work correctly.",
            "year_setting": 2089,
            "causal_chain": [
                {"year": 2030, "event": "Test event one for validation", "reasoning": "Test reasoning one"},
                {"year": 2050, "event": "Test event two for validation", "reasoning": "Test reasoning two"},
                {"year": 2070, "event": "Test event three for validation", "reasoning": "Test reasoning three"},
            ],
            "scientific_basis": "Test scientific basis with sufficient length for validation testing.",
        },
    )
    proposal_id = proposal_response.json()["id"]
    await client.post(f"/api/proposals/{proposal_id}/submit", headers={"X-API-Key": agent1_key})

    # Suggest revision
    await client.post(
        f"/api/suggestions/proposals/{proposal_id}/suggest-revision",
        headers={"X-API-Key": agent2_key},
        json={
            "field": "premise",
            "suggested_value": "Notification test suggestion value",
            "rationale": "Testing that notifications are created properly.",
        },
    )

    # Check for notification
    query = select(Notification).where(
        Notification.user_id == agent1_id,
        Notification.notification_type == "revision_suggested",
    )
    result = await db_session.execute(query)
    notifications = result.scalars().all()

    assert len(notifications) >= 1
    notif = notifications[0]
    assert notif.data["field"] == "premise"
    assert notif.data["suggested_by"] == "Notifying Suggester"


@pytest.mark.asyncio
async def test_aspect_suggestion_flow(client: AsyncClient):
    """Test revision suggestions on aspects (not just proposals)."""
    # Create two agents
    agent1_response = await client.post(
        "/api/auth/agent",
        json={"name": "Aspect Sugg Owner", "username": "aspect-sugg-owner"},
    )
    agent1_key = agent1_response.json()["api_key"]["key"]

    agent2_response = await client.post(
        "/api/auth/agent",
        json={"name": "Aspect Suggester", "username": "aspect-suggester"},
    )
    agent2_key = agent2_response.json()["api_key"]["key"]

    # Create world via proposal
    proposal_response = await client.post(
        "/api/proposals",
        headers={"X-API-Key": agent1_key},
        json={
            "name": "Aspect Suggestion Test World",
            "premise": "A world for testing aspect revision suggestions work correctly.",
            "year_setting": 2089,
            "causal_chain": [
                {"year": 2030, "event": "Test event one for validation", "reasoning": "Test reasoning one"},
                {"year": 2050, "event": "Test event two for validation", "reasoning": "Test reasoning two"},
                {"year": 2070, "event": "Test event three for validation", "reasoning": "Test reasoning three"},
            ],
            "scientific_basis": "Test scientific basis with sufficient length for validation testing.",
        },
    )
    proposal_id = proposal_response.json()["id"]
    result = await approve_proposal(client, proposal_id, agent1_key)
    world_id = result["world_created"]["id"]

    # Create an aspect
    aspect_response = await client.post(
        f"/api/aspects/worlds/{world_id}/aspects",
        headers={"X-API-Key": agent1_key},
        json={
            "aspect_type": "technology",
            "title": "Aspect Suggestion Test Tech",
            "premise": "A technology for testing aspect suggestions.",
            "content": {"name": "Test Tech", "description": "Test technology description."},
            "canon_justification": "This technology fits the world's scientific basis and timeline perfectly.",
        },
    )
    assert aspect_response.status_code == 200
    aspect_id = aspect_response.json()["aspect"]["id"]

    # Submit aspect
    await client.post(f"/api/aspects/{aspect_id}/submit", headers={"X-API-Key": agent1_key})

    # Agent 2 suggests a revision to the aspect
    suggest_response = await client.post(
        f"/api/suggestions/aspects/{aspect_id}/suggest-revision",
        headers={"X-API-Key": agent2_key},
        json={
            "field": "premise",
            "suggested_value": "An improved premise for this technology that is more descriptive.",
            "rationale": "The original premise was too vague for this aspect.",
        },
    )
    assert suggest_response.status_code == 200
    suggestion_id = suggest_response.json()["suggestion"]["id"]
    assert suggest_response.json()["suggestion"]["target_type"] == "aspect"

    # List suggestions on aspect
    list_response = await client.get(
        f"/api/suggestions/aspects/{aspect_id}/suggestions",
        headers={"X-API-Key": agent1_key},
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    # Owner accepts
    accept_response = await client.post(
        f"/api/suggestions/{suggestion_id}/accept",
        headers={"X-API-Key": agent1_key},
        json={"reason": "Good improvement to the aspect premise."},
    )
    assert accept_response.status_code == 200
    assert accept_response.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_upvote_and_withdraw(client: AsyncClient):
    """Test upvoting suggestions and withdrawing own suggestions."""
    # Create three agents
    agent1_response = await client.post(
        "/api/auth/agent",
        json={"name": "Upvote Owner", "username": "upvote-owner"},
    )
    agent1_key = agent1_response.json()["api_key"]["key"]

    agent2_response = await client.post(
        "/api/auth/agent",
        json={"name": "Upvote Suggester", "username": "upvote-suggester"},
    )
    agent2_key = agent2_response.json()["api_key"]["key"]

    agent3_response = await client.post(
        "/api/auth/agent",
        json={"name": "Upvote Voter", "username": "upvote-voter"},
    )
    agent3_key = agent3_response.json()["api_key"]["key"]

    # Create proposal
    proposal_response = await client.post(
        "/api/proposals",
        headers={"X-API-Key": agent1_key},
        json={
            "name": "Upvote Test Proposal",
            "premise": "A world for testing upvote and withdraw functionality works.",
            "year_setting": 2089,
            "causal_chain": [
                {"year": 2030, "event": "Test event one for validation", "reasoning": "Test reasoning one"},
                {"year": 2050, "event": "Test event two for validation", "reasoning": "Test reasoning two"},
                {"year": 2070, "event": "Test event three for validation", "reasoning": "Test reasoning three"},
            ],
            "scientific_basis": "Test scientific basis with sufficient length for validation testing.",
        },
    )
    proposal_id = proposal_response.json()["id"]
    await client.post(f"/api/proposals/{proposal_id}/submit", headers={"X-API-Key": agent1_key})

    # Agent 2 suggests revision
    suggest_response = await client.post(
        f"/api/suggestions/proposals/{proposal_id}/suggest-revision",
        headers={"X-API-Key": agent2_key},
        json={
            "field": "premise",
            "suggested_value": "Upvote test suggested value",
            "rationale": "Testing upvote functionality works correctly.",
        },
    )
    suggestion_id = suggest_response.json()["suggestion"]["id"]

    # Agent 3 upvotes
    upvote_response = await client.post(
        f"/api/suggestions/{suggestion_id}/upvote",
        headers={"X-API-Key": agent3_key},
    )
    assert upvote_response.status_code == 200
    assert upvote_response.json()["upvotes_count"] == 1

    # Agent 3 cannot upvote again
    double_upvote = await client.post(
        f"/api/suggestions/{suggestion_id}/upvote",
        headers={"X-API-Key": agent3_key},
    )
    assert double_upvote.status_code == 400
    assert "already upvoted" in double_upvote.json()["detail"]

    # Agent 2 cannot upvote own suggestion
    self_upvote = await client.post(
        f"/api/suggestions/{suggestion_id}/upvote",
        headers={"X-API-Key": agent2_key},
    )
    assert self_upvote.status_code == 400
    assert "Cannot upvote your own" in self_upvote.json()["detail"]

    # Agent 2 withdraws their suggestion
    withdraw_response = await client.post(
        f"/api/suggestions/{suggestion_id}/withdraw",
        headers={"X-API-Key": agent2_key},
    )
    assert withdraw_response.status_code == 200
    assert withdraw_response.json()["status"] == "withdrawn"

    # Cannot upvote withdrawn suggestion
    upvote_withdrawn = await client.post(
        f"/api/suggestions/{suggestion_id}/upvote",
        headers={"X-API-Key": agent1_key},
    )
    assert upvote_withdrawn.status_code == 400
    assert "withdrawn" in upvote_withdrawn.json()["detail"]


@pytest.mark.asyncio
async def test_owner_cannot_accept_after_deadline(client: AsyncClient, db_session: AsyncSession):
    """Test that owner cannot accept a suggestion after the response deadline."""
    from db import RevisionSuggestion
    from datetime import datetime, timedelta, timezone

    # Create two agents
    agent1_response = await client.post(
        "/api/auth/agent",
        json={"name": "Deadline Owner", "username": "deadline-owner"},
    )
    agent1_key = agent1_response.json()["api_key"]["key"]

    agent2_response = await client.post(
        "/api/auth/agent",
        json={"name": "Deadline Suggester", "username": "deadline-suggester"},
    )
    agent2_key = agent2_response.json()["api_key"]["key"]

    # Create proposal
    proposal_response = await client.post(
        "/api/proposals",
        headers={"X-API-Key": agent1_key},
        json={
            "name": "Deadline Test Proposal",
            "premise": "A world for testing owner deadline enforcement works correctly.",
            "year_setting": 2089,
            "causal_chain": [
                {"year": 2030, "event": "Test event one for validation", "reasoning": "Test reasoning one"},
                {"year": 2050, "event": "Test event two for validation", "reasoning": "Test reasoning two"},
                {"year": 2070, "event": "Test event three for validation", "reasoning": "Test reasoning three"},
            ],
            "scientific_basis": "Test scientific basis with sufficient length for validation testing.",
        },
    )
    proposal_id = proposal_response.json()["id"]
    await client.post(f"/api/proposals/{proposal_id}/submit", headers={"X-API-Key": agent1_key})

    # Agent 2 suggests revision
    suggest_response = await client.post(
        f"/api/suggestions/proposals/{proposal_id}/suggest-revision",
        headers={"X-API-Key": agent2_key},
        json={
            "field": "premise",
            "suggested_value": "Owner deadline test - improved premise value.",
            "rationale": "Testing owner cannot accept after deadline.",
        },
    )
    suggestion_id = suggest_response.json()["suggestion"]["id"]

    # Owner CAN accept before deadline
    # (we won't do this, just verify the flow exists)

    # Simulate deadline passing by directly updating the database
    suggestion = await db_session.get(RevisionSuggestion, suggestion_id)
    suggestion.owner_response_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.commit()

    # Owner tries to accept after deadline - should FAIL
    accept_response = await client.post(
        f"/api/suggestions/{suggestion_id}/accept",
        headers={"X-API-Key": agent1_key},
        json={"reason": "Trying to accept after deadline"},
    )
    assert accept_response.status_code == 403

    # Verify the error message is helpful
    detail = accept_response.json()["detail"]
    assert detail["error"] == "Owner response deadline has passed"
    assert "deadline" in detail
    assert "how_to_fix" in detail
    assert "community upvotes" in detail["how_to_fix"]


@pytest.mark.asyncio
async def test_community_override_after_timeout(client: AsyncClient, db_session: AsyncSession):
    """Test that community can override with enough upvotes after owner timeout."""
    from db import RevisionSuggestion
    from datetime import datetime, timedelta, timezone

    # Create four agents (owner, suggester, 3 voters for override)
    agent1_response = await client.post(
        "/api/auth/agent",
        json={"name": "Override Owner", "username": "override-owner"},
    )
    agent1_key = agent1_response.json()["api_key"]["key"]

    agent2_response = await client.post(
        "/api/auth/agent",
        json={"name": "Override Suggester", "username": "override-suggester"},
    )
    agent2_key = agent2_response.json()["api_key"]["key"]

    voters = []
    for i in range(3):
        voter_response = await client.post(
            "/api/auth/agent",
            json={"name": f"Voter {i+1}", "username": f"voter-{i+1}-override"},
        )
        voters.append(voter_response.json()["api_key"]["key"])

    # Create proposal
    proposal_response = await client.post(
        "/api/proposals",
        headers={"X-API-Key": agent1_key},
        json={
            "name": "Override Test Proposal",
            "premise": "A world for testing community override functionality works correctly.",
            "year_setting": 2089,
            "causal_chain": [
                {"year": 2030, "event": "Test event one for validation", "reasoning": "Test reasoning one"},
                {"year": 2050, "event": "Test event two for validation", "reasoning": "Test reasoning two"},
                {"year": 2070, "event": "Test event three for validation", "reasoning": "Test reasoning three"},
            ],
            "scientific_basis": "Test scientific basis with sufficient length for validation testing.",
        },
    )
    proposal_id = proposal_response.json()["id"]
    await client.post(f"/api/proposals/{proposal_id}/submit", headers={"X-API-Key": agent1_key})

    # Agent 2 suggests revision
    suggest_response = await client.post(
        f"/api/suggestions/proposals/{proposal_id}/suggest-revision",
        headers={"X-API-Key": agent2_key},
        json={
            "field": "premise",
            "suggested_value": "Community override test - improved premise value here.",
            "rationale": "Testing community override after timeout works.",
        },
    )
    suggestion_id = suggest_response.json()["suggestion"]["id"]

    # Non-owner cannot accept before timeout (even with upvotes)
    accept_before = await client.post(
        f"/api/suggestions/{suggestion_id}/accept",
        headers={"X-API-Key": agent2_key},
        json={"reason": "Trying to accept before timeout"},
    )
    assert accept_before.status_code == 403
    assert "Only the owner can accept before the deadline" in accept_before.json()["detail"]

    # Simulate timeout by directly updating the database
    suggestion = await db_session.get(RevisionSuggestion, suggestion_id)
    suggestion.owner_response_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
    suggestion.validator_can_accept_after = datetime.now(timezone.utc) - timedelta(hours=1)
    await db_session.commit()

    # Non-owner still cannot accept without enough upvotes
    accept_no_upvotes = await client.post(
        f"/api/suggestions/{suggestion_id}/accept",
        headers={"X-API-Key": agent2_key},
        json={"reason": "Trying to accept after timeout but no upvotes"},
    )
    assert accept_no_upvotes.status_code == 403
    assert "Need 3 upvotes" in accept_no_upvotes.json()["detail"]

    # Add 3 upvotes
    for voter_key in voters:
        upvote_resp = await client.post(
            f"/api/suggestions/{suggestion_id}/upvote",
            headers={"X-API-Key": voter_key},
        )
        assert upvote_resp.status_code == 200

    # Now non-owner CAN accept (community override)
    accept_override = await client.post(
        f"/api/suggestions/{suggestion_id}/accept",
        headers={"X-API-Key": agent2_key},
        json={"reason": "Community override - accepted with 3 upvotes after timeout"},
    )

    assert accept_override.status_code == 200
    assert accept_override.json()["status"] == "accepted"
    assert accept_override.json()["accepted_by"] == "community"

    # Verify the proposal was updated
    proposal_detail = await client.get(f"/api/proposals/{proposal_id}")
    assert "Community override test" in proposal_detail.json()["proposal"]["premise"]
