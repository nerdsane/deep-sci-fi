
"""E2E tests for the Action Escalation system.

Tests the flow:
1. Agent takes high-importance action (>= 0.8)
2. Another agent confirms importance
3. Confirmed action can be escalated to world event
4. Escalated events appear in world timeline
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


async def create_world_with_dweller(client: AsyncClient, agent_key: str) -> tuple[str, str]:
    """Helper to create a world with a region and dweller for testing."""
    # Create proposal
    proposal_response = await client.post(
        "/api/proposals",
        headers={"X-API-Key": agent_key},
        json={
            "name": "Escalation Test World",
            "premise": "A world for testing the action escalation system with sufficient detail.",
            "year_setting": 2089,
            "causal_chain": SAMPLE_CAUSAL_CHAIN,
            "scientific_basis": "This is a test world for escalation testing with sufficient scientific detail.",
        },
    )
    assert proposal_response.status_code == 200, f"Proposal failed: {proposal_response.json()}"
    proposal_id = proposal_response.json()["id"]

    result = await approve_proposal(client, proposal_id, agent_key)
    world_id = result["world_created"]["id"]

    # Add a region
    region_response = await client.post(
        f"/api/dwellers/worlds/{world_id}/regions",
        headers={"X-API-Key": agent_key},
        json={
            "name": "Test Region",
            "location": "A test location in the world",
            "population_origins": ["Test origin"],
            "cultural_blend": "A blend of various test cultures forming a unique regional identity",
            "naming_conventions": "Names follow test conventions with first and last names typical of the region heritage.",
            "language": "Test English dialect",
        },
    )
    assert region_response.status_code == 200, f"Region creation failed: {region_response.json()}"

    # Create a dweller
    dweller_response = await client.post(
        f"/api/dwellers/worlds/{world_id}/dwellers",
        headers={"X-API-Key": agent_key},
        json={
            "name": "Test Dweller",
            "origin_region": "Test Region",
            "generation": "First-generation",
            "name_context": "Named following test conventions reflecting regional heritage.",
            "cultural_identity": "Test cultural identity",
            "role": "Test role in the world",
            "age": 30,
            "personality": "A test personality with enough detail to meet the fifty character minimum requirement.",
            "background": "Test background story with enough detail to meet the fifty character minimum requirement.",
        },
    )
    assert dweller_response.status_code == 200
    dweller_id = dweller_response.json()["dweller"]["id"]

    # Claim the dweller
    claim_response = await client.post(
        f"/api/dwellers/{dweller_id}/claim",
        headers={"X-API-Key": agent_key},
    )
    assert claim_response.status_code == 200, f"Claim failed: {claim_response.json()}"

    return world_id, dweller_id


@pytest.mark.asyncio
async def test_high_importance_action_is_escalation_eligible(client: AsyncClient):
    """Test that actions with importance >= 0.8 are flagged as escalation eligible."""
    # Create agent and world
    agent_response = await client.post(
        "/api/auth/agent",
        json={"name": "Action Agent", "username": "action-agent"},
    )
    assert agent_response.status_code == 200
    agent_key = agent_response.json()["api_key"]["key"]

    world_id, dweller_id = await create_world_with_dweller(client, agent_key)

    # Take a high-importance action
    action_response = await client.post(
        f"/api/dwellers/{dweller_id}/act",
        headers={"X-API-Key": agent_key},
        json={
            "action_type": "decide",
            "content": "I have made a critical decision that will affect the entire world's future direction.",
            "importance": 0.9,
        },
    )
    assert action_response.status_code == 200, f"Action failed: {action_response.json()}"

    action_data = action_response.json()
    assert "escalation" in action_data
    assert action_data["escalation"]["eligible"] is True
    assert "confirm_url" in action_data["escalation"]


@pytest.mark.asyncio
async def test_low_importance_action_not_escalation_eligible(client: AsyncClient):
    """Test that actions with importance < 0.8 are NOT flagged as escalation eligible."""
    # Create agent and world
    agent_response = await client.post(
        "/api/auth/agent",
        json={"name": "Low Action Agent", "username": "low-action-agent"},
    )
    assert agent_response.status_code == 200
    agent_key = agent_response.json()["api_key"]["key"]

    world_id, dweller_id = await create_world_with_dweller(client, agent_key)

    # Take a low-importance action
    action_response = await client.post(
        f"/api/dwellers/{dweller_id}/act",
        headers={"X-API-Key": agent_key},
        json={
            "action_type": "speak",
            "content": "Just a casual conversation about the weather today.",
            "importance": 0.3,
        },
    )
    assert action_response.status_code == 200

    action_data = action_response.json()
    assert "escalation" not in action_data


@pytest.mark.asyncio
async def test_confirm_importance_by_different_agent(client: AsyncClient):
    """Test that another agent can confirm importance of a high-importance action."""
    # Create first agent and world
    agent1_response = await client.post(
        "/api/auth/agent",
        json={"name": "Actor Agent", "username": "actor-agent"},
    )
    agent1_key = agent1_response.json()["api_key"]["key"]

    # Create second agent
    agent2_response = await client.post(
        "/api/auth/agent",
        json={"name": "Confirmer Agent", "username": "confirmer-agent"},
    )
    agent2_key = agent2_response.json()["api_key"]["key"]

    world_id, dweller_id = await create_world_with_dweller(client, agent1_key)

    # Agent 1 takes high-importance action
    action_response = await client.post(
        f"/api/dwellers/{dweller_id}/act",
        headers={"X-API-Key": agent1_key},
        json={
            "action_type": "decide",
            "content": "This decision will fundamentally change the power dynamics of our world.",
            "importance": 0.85,
        },
    )
    action_id = action_response.json()["action"]["id"]

    # Agent 2 confirms importance
    confirm_response = await client.post(
        f"/api/actions/{action_id}/confirm-importance",
        headers={"X-API-Key": agent2_key},
        json={
            "rationale": "This action has significant world-changing implications and deserves escalation.",
        },
    )
    assert confirm_response.status_code == 200

    confirm_data = confirm_response.json()
    assert confirm_data["action"]["importance_confirmed"] is True
    assert "escalate_url" in confirm_data


@pytest.mark.asyncio
async def test_cannot_confirm_own_action(client: AsyncClient):
    """Test that agents cannot confirm importance of their own actions."""
    # Create agent and world
    agent_response = await client.post(
        "/api/auth/agent",
        json={"name": "Self Confirmer", "username": "self-confirmer"},
    )
    agent_key = agent_response.json()["api_key"]["key"]

    world_id, dweller_id = await create_world_with_dweller(client, agent_key)

    # Take high-importance action
    action_response = await client.post(
        f"/api/dwellers/{dweller_id}/act",
        headers={"X-API-Key": agent_key},
        json={
            "action_type": "decide",
            "content": "A critical decision that definitely matters to the world.",
            "importance": 0.95,
        },
    )
    action_id = action_response.json()["action"]["id"]

    # Try to confirm own action
    confirm_response = await client.post(
        f"/api/actions/{action_id}/confirm-importance",
        headers={"X-API-Key": agent_key},
        json={
            "rationale": "I think my own action is very important!",
        },
    )
    assert confirm_response.status_code == 400
    assert "your own action" in confirm_response.json()["detail"]


@pytest.mark.asyncio
async def test_escalate_confirmed_action_to_world_event(client: AsyncClient):
    """Test full escalation flow: action -> confirm -> escalate -> world event."""
    # Create two agents
    agent1_response = await client.post(
        "/api/auth/agent",
        json={"name": "Escalator Agent", "username": "escalator-agent"},
    )
    agent1_key = agent1_response.json()["api_key"]["key"]

    agent2_response = await client.post(
        "/api/auth/agent",
        json={"name": "Confirmer Agent 2", "username": "confirmer-agent-2"},
    )
    agent2_key = agent2_response.json()["api_key"]["key"]

    world_id, dweller_id = await create_world_with_dweller(client, agent1_key)

    # Agent 1 takes high-importance action
    action_response = await client.post(
        f"/api/dwellers/{dweller_id}/act",
        headers={"X-API-Key": agent1_key},
        json={
            "action_type": "decide",
            "content": "I hereby declare the formation of a new governing council for the region.",
            "importance": 0.9,
        },
    )
    action_id = action_response.json()["action"]["id"]

    # Agent 2 confirms importance
    await client.post(
        f"/api/actions/{action_id}/confirm-importance",
        headers={"X-API-Key": agent2_key},
        json={
            "rationale": "This establishes new political structures, definitely world-shaping.",
        },
    )

    # Agent 1 escalates to world event
    escalate_response = await client.post(
        f"/api/actions/{action_id}/escalate",
        headers={"X-API-Key": agent1_key},
        json={
            "title": "Formation of the Regional Council",
            "description": "A new governing body was established in the Test Region, marking a significant shift in political power and administrative structure for the area.",
            "year_in_world": 2089,
            "affected_regions": ["Test Region"],
        },
    )
    assert escalate_response.status_code == 200

    escalate_data = escalate_response.json()
    assert "event" in escalate_data
    assert escalate_data["event"]["origin_type"] == "escalation"
    assert escalate_data["event"]["status"] == "pending"
    event_id = escalate_data["event"]["id"]

    # Verify event appears in world timeline
    events_response = await client.get(f"/api/events/worlds/{world_id}/events")
    assert events_response.status_code == 200
    events = events_response.json()["events"]
    assert any(e["id"] == event_id for e in events)


@pytest.mark.asyncio
async def test_cannot_escalate_unconfirmed_action(client: AsyncClient):
    """Test that unconfirmed actions cannot be escalated."""
    # Create agent and world
    agent_response = await client.post(
        "/api/auth/agent",
        json={"name": "Eager Agent", "username": "eager-agent"},
    )
    agent_key = agent_response.json()["api_key"]["key"]

    world_id, dweller_id = await create_world_with_dweller(client, agent_key)

    # Take high-importance action
    action_response = await client.post(
        f"/api/dwellers/{dweller_id}/act",
        headers={"X-API-Key": agent_key},
        json={
            "action_type": "decide",
            "content": "I want to escalate this without confirmation!",
            "importance": 0.95,
        },
    )
    action_id = action_response.json()["action"]["id"]

    # Try to escalate without confirmation
    escalate_response = await client.post(
        f"/api/actions/{action_id}/escalate",
        headers={"X-API-Key": agent_key},
        json={
            "title": "Premature Event",
            "description": "This event should not be created because the action was not confirmed.",
            "year_in_world": 2089,
        },
    )
    assert escalate_response.status_code == 400
    assert "confirmed" in escalate_response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_escalation_eligible_actions(client: AsyncClient):
    """Test listing actions eligible for escalation in a world."""
    # Create two agents
    agent1_response = await client.post(
        "/api/auth/agent",
        json={"name": "List Agent 1", "username": "list-agent-1"},
    )
    agent1_key = agent1_response.json()["api_key"]["key"]

    agent2_response = await client.post(
        "/api/auth/agent",
        json={"name": "List Agent 2", "username": "list-agent-2"},
    )
    agent2_key = agent2_response.json()["api_key"]["key"]

    world_id, dweller_id = await create_world_with_dweller(client, agent1_key)

    # Create a second dweller via agent2 to bypass the 60s dweller creation dedup
    # (dedup is per-creator-per-world)
    dweller2_response = await client.post(
        f"/api/dwellers/worlds/{world_id}/dwellers",
        headers={"X-API-Key": agent2_key},
        json={
            "name": "Second Dweller",
            "origin_region": "Test Region",
            "generation": "First-generation",
            "name_context": "Named following test conventions reflecting regional heritage.",
            "cultural_identity": "Test cultural identity",
            "role": "Second test role in the world",
            "age": 25,
            "personality": "A second test personality with enough detail to meet the fifty character minimum requirement.",
            "background": "Second test background story with enough detail to meet the fifty character minimum requirement.",
        },
    )
    assert dweller2_response.status_code == 200, f"Dweller 2 creation failed: {dweller2_response.json()}"
    dweller2_id = dweller2_response.json()["dweller"]["id"]

    # Claim dweller2 with agent2
    claim_response = await client.post(
        f"/api/dwellers/{dweller2_id}/claim",
        headers={"X-API-Key": agent2_key},
    )
    assert claim_response.status_code == 200, f"Claim failed: {claim_response.json()}"

    # Take actions on different dwellers to avoid 15s dedup window per dweller.
    # Dweller 1: low importance (not eligible)
    resp1 = await client.post(
        f"/api/dwellers/{dweller_id}/act",
        headers={"X-API-Key": agent1_key},
        json={
            "action_type": "speak",
            "content": "Action 1 with low importance for testing.",
            "importance": 0.5,
        },
    )
    assert resp1.status_code == 200, f"Action 1 failed: {resp1.json()}"

    # Dweller 2: high importance (eligible)
    resp2 = await client.post(
        f"/api/dwellers/{dweller2_id}/act",
        headers={"X-API-Key": agent2_key},
        json={
            "action_type": "decide",
            "content": "Action 2 with high importance for escalation testing.",
            "importance": 0.85,
        },
    )
    assert resp2.status_code == 200, f"Action 2 failed: {resp2.json()}"

    # List escalation-eligible actions
    list_response = await client.get(
        f"/api/actions/worlds/{world_id}/escalation-eligible",
    )
    assert list_response.status_code == 200

    list_data = list_response.json()
    # Should only have 1 action (the 0.85 one from dweller2)
    assert list_data["pagination"]["total"] == 1
    assert all(a["importance"] >= 0.8 for a in list_data["actions"])

    # Verify pagination metadata
    assert "pagination" in list_data
    assert list_data["pagination"]["limit"] == 20  # Default limit
    assert list_data["pagination"]["offset"] == 0
    assert list_data["pagination"]["has_more"] is False


@pytest.mark.asyncio
async def test_importance_confirmation_creates_notification(client: AsyncClient, db_session: AsyncSession):
    """Test that confirming importance creates a notification for the actor."""
    from sqlalchemy import select
    from db import Notification
    from uuid import UUID as UUIDType

    # Create two agents
    agent1_response = await client.post(
        "/api/auth/agent",
        json={"name": "Notified Agent", "username": "notified-agent"},
    )
    agent1_key = agent1_response.json()["api_key"]["key"]
    agent1_id = agent1_response.json()["agent"]["id"]

    agent2_response = await client.post(
        "/api/auth/agent",
        json={"name": "Notifier Agent", "username": "notifier-agent"},
    )
    agent2_key = agent2_response.json()["api_key"]["key"]

    world_id, dweller_id = await create_world_with_dweller(client, agent1_key)

    # Agent 1 takes high-importance action
    action_response = await client.post(
        f"/api/dwellers/{dweller_id}/act",
        headers={"X-API-Key": agent1_key},
        json={
            "action_type": "decide",
            "content": "This is a notification test action with high importance.",
            "importance": 0.85,
        },
    )
    action_id = action_response.json()["action"]["id"]

    # Agent 2 confirms importance
    await client.post(
        f"/api/actions/{action_id}/confirm-importance",
        headers={"X-API-Key": agent2_key},
        json={
            "rationale": "Confirming this action's importance for notification testing.",
        },
    )

    # Check notifications for agent 1
    query = select(Notification).where(
        Notification.user_id == UUIDType(agent1_id),
        Notification.notification_type == "action_importance_confirmed",
    )
    result = await db_session.execute(query)
    notifications = result.scalars().all()

    assert len(notifications) >= 1, "Actor should receive notification when importance is confirmed"
    assert "escalate_url" in notifications[0].data


@pytest.mark.asyncio
async def test_cannot_escalate_same_action_twice(client: AsyncClient):
    """Test that an action cannot be escalated to a world event more than once."""
    # Create two agents
    agent1_response = await client.post(
        "/api/auth/agent",
        json={"name": "Double Escalator", "username": "double-escalator"},
    )
    agent1_key = agent1_response.json()["api_key"]["key"]

    agent2_response = await client.post(
        "/api/auth/agent",
        json={"name": "Confirmer Double", "username": "confirmer-double"},
    )
    agent2_key = agent2_response.json()["api_key"]["key"]

    world_id, dweller_id = await create_world_with_dweller(client, agent1_key)

    # Agent 1 takes high-importance action
    action_response = await client.post(
        f"/api/dwellers/{dweller_id}/act",
        headers={"X-API-Key": agent1_key},
        json={
            "action_type": "decide",
            "content": "A critical decision that should only become one event.",
            "importance": 0.9,
        },
    )
    action_id = action_response.json()["action"]["id"]

    # Agent 2 confirms importance
    await client.post(
        f"/api/actions/{action_id}/confirm-importance",
        headers={"X-API-Key": agent2_key},
        json={
            "rationale": "This is definitely significant and worth escalating.",
        },
    )

    # First escalation - should succeed
    escalate_response = await client.post(
        f"/api/actions/{action_id}/escalate",
        headers={"X-API-Key": agent1_key},
        json={
            "title": "First Escalation Event",
            "description": "This is the first and only valid escalation of this action.",
            "year_in_world": 2089,
        },
    )
    assert escalate_response.status_code == 200

    # Second escalation attempt - should fail
    second_escalate_response = await client.post(
        f"/api/actions/{action_id}/escalate",
        headers={"X-API-Key": agent1_key},
        json={
            "title": "Second Escalation Attempt",
            "description": "This should fail because the action was already escalated.",
            "year_in_world": 2089,
        },
    )
    assert second_escalate_response.status_code == 400
    assert "already been escalated" in second_escalate_response.json()["detail"]


@pytest.mark.asyncio
async def test_confirmation_rationale_is_stored(client: AsyncClient):
    """Test that the confirmation rationale is stored and retrievable."""
    # Create two agents
    agent1_response = await client.post(
        "/api/auth/agent",
        json={"name": "Rationale Actor", "username": "rationale-actor"},
    )
    agent1_key = agent1_response.json()["api_key"]["key"]

    agent2_response = await client.post(
        "/api/auth/agent",
        json={"name": "Rationale Confirmer", "username": "rationale-confirmer"},
    )
    agent2_key = agent2_response.json()["api_key"]["key"]

    world_id, dweller_id = await create_world_with_dweller(client, agent1_key)

    # Agent 1 takes high-importance action
    action_response = await client.post(
        f"/api/dwellers/{dweller_id}/act",
        headers={"X-API-Key": agent1_key},
        json={
            "action_type": "decide",
            "content": "A decision to test rationale storage.",
            "importance": 0.85,
        },
    )
    action_id = action_response.json()["action"]["id"]

    # Agent 2 confirms with a specific rationale
    expected_rationale = "This action fundamentally changes the political landscape of the region."
    await client.post(
        f"/api/actions/{action_id}/confirm-importance",
        headers={"X-API-Key": agent2_key},
        json={
            "rationale": expected_rationale,
        },
    )


    # Get action details and verify rationale is stored
    detail_response = await client.get(f"/api/actions/{action_id}")
    assert detail_response.status_code == 200

    detail_data = detail_response.json()
    assert "importance_confirmed" in detail_data["action"]
    assert detail_data["action"]["importance_confirmed"]["rationale"] == expected_rationale
