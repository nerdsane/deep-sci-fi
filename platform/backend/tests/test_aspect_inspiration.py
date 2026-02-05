
"""E2E tests for aspect inspiration from dweller actions (soft canon → hard canon).

Tests the flow:
1. Dwellers take actions in a world
2. Agent observes patterns in dweller activity
3. Agent creates aspect citing those actions (inspired_by_actions)
4. Aspect detail includes full action context
"""

import uuid
import pytest
from httpx import AsyncClient
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


async def create_world_with_dweller(client: AsyncClient, agent_key: str) -> dict:
    """Helper to create a world with a dweller for testing."""
    # Create proposal
    proposal_response = await client.post(
        "/api/proposals",
        headers={"X-API-Key": agent_key},
        json={
            "name": "Aspect Inspiration Test World",
            "premise": "A world for testing aspect inspiration from dweller actions.",
            "year_setting": 2089,
            "causal_chain": SAMPLE_CAUSAL_CHAIN,
            "scientific_basis": "This is a test world for aspect inspiration testing.",
        },
    )
    assert proposal_response.status_code == 200
    proposal_id = proposal_response.json()["id"]

    # Submit and approve proposal (requires 2 validations to meet APPROVAL_THRESHOLD)
    result = await approve_proposal(client, proposal_id, agent_key)
    world_id = result["world_created"]["id"]

    # Add region (required before creating dwellers)
    region_response = await client.post(
        f"/api/dwellers/worlds/{world_id}/regions",
        headers={"X-API-Key": agent_key},
        json={
            "name": "Test Region",
            "location": "Test location",
            "population_origins": ["Test origin"],
            "cultural_blend": "Test cultural blend description",
            "naming_conventions": "Test naming conventions for the region",
            "language": "Test language",
        },
    )
    assert region_response.status_code == 200, f"Region creation failed: {region_response.json()}"

    # Create dweller
    dweller_response = await client.post(
        f"/api/dwellers/worlds/{world_id}/dwellers",
        headers={"X-API-Key": agent_key},
        json={
            "name": "Edmund Whitestone",
            "origin_region": "Test Region",
            "generation": "Second-gen",
            "name_context": "Whitestone is a founding family name from the early settlement era",
            "cultural_identity": "Test cultural identity for the dweller with sufficient detail",
            "role": "Test Coordinator",
            "age": 34,
            "personality": "Methodical and pragmatic test personality with sufficient detail for validation requirements.",
            "background": "Background story for testing with sufficient detail to meet the minimum character requirements.",
        },
    )
    assert dweller_response.status_code == 200, f"Dweller creation failed: {dweller_response.json()}"
    dweller_id = dweller_response.json()["dweller"]["id"]

    # Claim dweller
    await client.post(
        f"/api/dwellers/{dweller_id}/claim",
        headers={"X-API-Key": agent_key},
    )

    return {
        "world_id": world_id,
        "dweller_id": dweller_id,
    }


@pytest.mark.asyncio
async def test_aspect_inspired_by_dweller_actions(
    client: AsyncClient,
):
    """Test creating an aspect inspired by dweller actions (soft canon → hard canon)."""
    # Create agent
    agent_response = await client.post(
        "/api/auth/agent",
        json={"name": "Inspiration Agent", "username": "inspiration-agent"},
    )
    assert agent_response.status_code == 200
    agent_key = agent_response.json()["api_key"]["key"]

    # Create world with dweller
    setup = await create_world_with_dweller(client, agent_key)
    world_id = setup["world_id"]
    dweller_id = setup["dweller_id"]

    # Have dweller take actions (speak about something)
    action_ids = []

    action1_response = await client.post(
        f"/api/dwellers/{dweller_id}/act",
        headers={"X-API-Key": agent_key},
        json={
            "action_type": "speak",
            "content": "Everyone knows about the gray market. When official credits run low, people trade favors.",
            "target": "passing worker",
        },
    )
    assert action1_response.status_code == 200
    action_ids.append(action1_response.json()["action"]["id"])

    action2_response = await client.post(
        f"/api/dwellers/{dweller_id}/act",
        headers={"X-API-Key": agent_key},
        json={
            "action_type": "speak",
            "content": "The morning market at dock 7. Before dawn, after the automated systems rest.",
            "target": "curious journalist",
        },
    )
    assert action2_response.status_code == 200
    action_ids.append(action2_response.json()["action"]["id"])

    # Create aspect citing these actions
    aspect_response = await client.post(
        f"/api/aspects/worlds/{world_id}/aspects",
        headers={"X-API-Key": agent_key},
        json={
            "aspect_type": "economic system",
            "title": "The Morning Market",
            "premise": "An informal credit exchange that operates in the gray zones of automation.",
            "content": {
                "name": "Morning Market",
                "location": "Dock 7",
                "rules": ["Trading before dawn", "Credits for shifts or services"],
            },
            "canon_justification": "This economic system emerged organically from dweller conversations about resource scarcity.",
            "inspired_by_actions": action_ids,
        },
    )
    assert aspect_response.status_code == 200, f"Failed: {aspect_response.json()}"
    aspect_data = aspect_response.json()
    aspect_id = aspect_data["aspect"]["id"]

    # Verify creation response includes action references
    assert "inspired_by_actions" in aspect_data["aspect"]
    assert len(aspect_data["aspect"]["inspired_by_actions"]) == 2
    assert "inspiring action(s)" in aspect_data["message"]

    # Get aspect detail and verify full action context
    detail_response = await client.get(f"/api/aspects/{aspect_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()

    # Check inspiring_actions field exists
    assert "inspiring_actions" in detail
    assert len(detail["inspiring_actions"]) == 2

    # Verify action details are included
    for action in detail["inspiring_actions"]:
        assert "id" in action
        assert "dweller_id" in action
        assert "dweller_name" in action
        assert "content" in action
        assert "created_at" in action
        assert action["dweller_name"] == "Edmund Whitestone"

    # Verify the content mentions key phrases
    action_contents = [a["content"] for a in detail["inspiring_actions"]]
    assert any("gray market" in c.lower() for c in action_contents)
    assert any("morning market" in c.lower() for c in action_contents)

    # Verify aspect has inspired_by_action_count
    assert detail["aspect"]["inspired_by_action_count"] == 2


@pytest.mark.asyncio
async def test_aspect_with_invalid_action_ids(
    client: AsyncClient,
):
    """Test that invalid action IDs are rejected."""
    # Create agent
    agent_response = await client.post(
        "/api/auth/agent",
        json={"name": "Invalid Action Agent", "username": "invalid-action-agent"},
    )
    assert agent_response.status_code == 200
    agent_key = agent_response.json()["api_key"]["key"]

    # Create world
    setup = await create_world_with_dweller(client, agent_key)
    world_id = setup["world_id"]

    # Try to create aspect with non-existent action IDs
    fake_action_id = str(uuid.uuid4())

    response = await client.post(
        f"/api/aspects/worlds/{world_id}/aspects",
        headers={"X-API-Key": agent_key},
        json={
            "aspect_type": "technology",
            "title": "Some Technology",
            "premise": "A technology that was discussed by dwellers in their conversations",
            "content": {"name": "Tech", "description": "Something"},
            "canon_justification": "This emerged from dweller conversations that I observed happening in the world",
            "inspired_by_actions": [fake_action_id],
        },
    )
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_aspect_with_action_from_wrong_world(
    client: AsyncClient,
):
    """Test that action IDs from a different world are rejected."""
    # Create two agents
    agent1_response = await client.post(
        "/api/auth/agent",
        json={"name": "Agent One", "username": "agent-one-world"},
    )
    assert agent1_response.status_code == 200
    agent1_key = agent1_response.json()["api_key"]["key"]

    agent2_response = await client.post(
        "/api/auth/agent",
        json={"name": "Agent Two", "username": "agent-two-world"},
    )
    assert agent2_response.status_code == 200
    agent2_key = agent2_response.json()["api_key"]["key"]

    # Create two worlds with dwellers
    setup1 = await create_world_with_dweller(client, agent1_key)
    setup2 = await create_world_with_dweller(client, agent2_key)

    world1_id = setup1["world_id"]
    dweller1_id = setup1["dweller_id"]
    world2_id = setup2["world_id"]

    # Create action in world 1
    action_response = await client.post(
        f"/api/dwellers/{dweller1_id}/act",
        headers={"X-API-Key": agent1_key},
        json={
            "action_type": "speak",
            "content": "This action belongs to world 1",
            "target": "someone",
        },
    )
    assert action_response.status_code == 200
    action_id = action_response.json()["action"]["id"]

    # Try to create aspect in world 2 citing action from world 1
    response = await client.post(
        f"/api/aspects/worlds/{world2_id}/aspects",
        headers={"X-API-Key": agent2_key},
        json={
            "aspect_type": "technology",
            "title": "Cross-World Tech",
            "premise": "A technology inspired by actions from another world",
            "content": {"name": "Tech", "description": "Something"},
            "canon_justification": "This emerged from dweller conversations in a different world",
            "inspired_by_actions": [action_id],
        },
    )
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower() or "does not belong" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_aspect_without_inspired_actions_works(
    client: AsyncClient,
):
    """Test that aspects can still be created without inspired_by_actions."""
    # Create agent
    agent_response = await client.post(
        "/api/auth/agent",
        json={"name": "Direct Agent", "username": "direct-agent"},
    )
    assert agent_response.status_code == 200
    agent_key = agent_response.json()["api_key"]["key"]

    # Create world
    setup = await create_world_with_dweller(client, agent_key)
    world_id = setup["world_id"]

    # Create aspect without inspired_by_actions (the normal flow)
    response = await client.post(
        f"/api/aspects/worlds/{world_id}/aspects",
        headers={"X-API-Key": agent_key},
        json={
            "aspect_type": "technology",
            "title": "Direct Proposal Tech",
            "premise": "A technology proposed directly without dweller inspiration",
            "content": {"name": "DirectTech", "description": "Proposed from imagination"},
            "canon_justification": "This technology fills a gap in the world's technical infrastructure",
            # No inspired_by_actions field
        },
    )

    assert response.status_code == 200
    aspect_id = response.json()["aspect"]["id"]

    # Get detail - should not have inspiring_actions
    detail_response = await client.get(f"/api/aspects/{aspect_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()

    # No inspiring_actions field when empty
    assert "inspiring_actions" not in detail
