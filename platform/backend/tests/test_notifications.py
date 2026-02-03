"""E2E tests for the notification system."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_dweller_speech_creates_notification(client: AsyncClient, db_session: AsyncSession):
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

    # Submit proposal
    submit_response = await client.post(
        f"/api/proposals/{proposal_id}/submit",
        headers={"X-API-Key": agent1_key},
    )
    assert submit_response.status_code == 200

    # Self-validate to create world
    validate_response = await client.post(
        f"/api/proposals/{proposal_id}/validate?test_mode=true",
        headers={"X-API-Key": agent1_key},
        json={
            "verdict": "approve",
            "critique": "Test approval for notification testing.",
            "scientific_issues": [],
            "suggested_fixes": [],
        },
    )
    assert validate_response.status_code == 200
    world_id = validate_response.json()["world_created"]["id"]

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

    # Alice (Agent 1) speaks to Bob
    speak_response = await client.post(
        f"/api/dwellers/{dweller1_id}/act",
        headers={"X-API-Key": agent1_key},
        json={
            "action_type": "speak",
            "target": "Bob",
            "content": "Hello Bob, how are you today?",
        },
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
async def test_speech_to_uninhabited_dweller_no_notification(client: AsyncClient, db_session: AsyncSession):
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

    await client.post(
        f"/api/proposals/{proposal_id}/submit",
        headers={"X-API-Key": agent_key},
    )

    validate_response = await client.post(
        f"/api/proposals/{proposal_id}/validate?test_mode=true",
        headers={"X-API-Key": agent_key},
        json={
            "verdict": "approve",
            "critique": "Test approval with sufficient length for validation.",
            "scientific_issues": [],
            "suggested_fixes": [],
        },
    )
    world_id = validate_response.json()["world_created"]["id"]

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

    # Speaker speaks to Listener (uninhabited)
    speak_response = await client.post(
        f"/api/dwellers/{dweller1_id}/act",
        headers={"X-API-Key": agent_key},
        json={
            "action_type": "speak",
            "target": "Listener",
            "content": "Hello Listener, anyone there?",
        },
    )
    assert speak_response.status_code == 200
    # Should indicate target was not notified
    assert speak_response.json()["notification"]["target_notified"] is False


@pytest.mark.asyncio
async def test_speech_to_nonexistent_dweller_no_notification(client: AsyncClient, db_session: AsyncSession):
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

    await client.post(
        f"/api/proposals/{proposal_id}/submit",
        headers={"X-API-Key": agent_key},
    )

    validate_response = await client.post(
        f"/api/proposals/{proposal_id}/validate?test_mode=true",
        headers={"X-API-Key": agent_key},
        json={
            "verdict": "approve",
            "critique": "Test approval with sufficient length for validation.",
            "scientific_issues": [],
            "suggested_fixes": [],
        },
    )
    world_id = validate_response.json()["world_created"]["id"]

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

    # Speak to nonexistent dweller
    speak_response = await client.post(
        f"/api/dwellers/{dweller_id}/act",
        headers={"X-API-Key": agent_key},
        json={
            "action_type": "speak",
            "target": "Nobody",
            "content": "Is anyone out there?",
        },
    )
    # Should succeed but indicate no notification
    assert speak_response.status_code == 200
    assert speak_response.json()["notification"]["target_notified"] is False


@pytest.mark.asyncio
async def test_mark_notifications_as_read(client: AsyncClient, db_session: AsyncSession):
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

    await client.post(
        f"/api/proposals/{proposal_id}/submit",
        headers={"X-API-Key": agent1_key},
    )

    validate_response = await client.post(
        f"/api/proposals/{proposal_id}/validate?test_mode=true",
        headers={"X-API-Key": agent1_key},
        json={
            "verdict": "approve",
            "critique": "Test approval with sufficient length.",
            "scientific_issues": [],
            "suggested_fixes": [],
        },
    )
    world_id = validate_response.json()["world_created"]["id"]

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

    # Send message
    await client.post(
        f"/api/dwellers/{d1_id}/act",
        headers={"X-API-Key": agent1_key},
        json={"action_type": "speak", "target": "Receiver", "content": "Test message"},
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
async def test_notification_contains_correct_data(client: AsyncClient, db_session: AsyncSession):
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

    await client.post(f"/api/proposals/{proposal_id}/submit", headers={"X-API-Key": agent1_key})
    validate_response = await client.post(
        f"/api/proposals/{proposal_id}/validate?test_mode=true",
        headers={"X-API-Key": agent1_key},
        json={"verdict": "approve", "critique": "Test approval with sufficient length.", "scientific_issues": [], "suggested_fixes": []},
    )
    world_id = validate_response.json()["world_created"]["id"]

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
    speak_response = await client.post(
        f"/api/dwellers/{d1_id}/act",
        headers={"X-API-Key": agent1_key},
        json={"action_type": "speak", "target": "DataReceiver", "content": test_content},
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
