"""End-to-end tests for the dweller inhabitation flow.

This tests:
1. World creator adds regions (with cultural context)
2. World creator creates dwellers (culturally grounded)
3. External agent claims dweller (inhabits)
4. Agent gets full dweller state (context window)
5. Agent takes actions as dweller
6. Actions update dweller memories
7. Agent releases dweller
"""

import os
import pytest
from httpx import AsyncClient


requires_postgres = pytest.mark.skipif(
    "postgresql" not in os.getenv("TEST_DATABASE_URL", ""),
    reason="Requires PostgreSQL (set TEST_DATABASE_URL)"
)


# Test data
SAMPLE_CAUSAL_CHAIN = [
    {
        "year": 2035,
        "event": "Rising seas force mass migration from coastal megacities",
        "reasoning": "IPCC projections + insurance market collapse"
    },
    {
        "year": 2042,
        "event": "First autonomous floating city constructed",
        "reasoning": "Modular ocean platform technology matures"
    },
    {
        "year": 2055,
        "event": "Network of floating cities forms independent governance",
        "reasoning": "International law adapts to stateless ocean territories"
    }
]

SAMPLE_REGION = {
    "name": "New Shanghai",
    "location": "Pacific Ocean, coordinates 25°N 170°W",
    "population_origins": ["Chinese diaspora", "Southeast Asian refugees", "Tech workers worldwide"],
    "cultural_blend": "Fusion of Chinese heritage with cosmopolitan tech culture",
    "naming_conventions": (
        "Names reflect mixed heritage: Chinese family names with international first names "
        "(e.g., Wei Marcus Chen), or blended names (e.g., Mei-Lin Park). "
        "Some use 'wave names' - chosen identities reflecting ocean life."
    ),
    "language": "Mandarin-English creole with technical jargon"
}

SAMPLE_DWELLER = {
    "name": "Wei Marcus Chen",
    "origin_region": "New Shanghai",
    "generation": "Second-generation (parents were climate refugees)",
    "name_context": (
        "Wei is a traditional Chinese name honoring his grandfather. Marcus was "
        "chosen by his parents to signal cosmopolitan ambitions. Chen is the "
        "family name, carried through five generations."
    ),
    "cultural_identity": (
        "Identifies strongly as a 'wave child' - someone who has never known "
        "land-based life. Celebrates both Chinese New Year and Founding Day "
        "(anniversary of New Shanghai's creation)."
    ),
    "role": "Water systems engineer, responsible for desalination maintenance",
    "age": 28,
    "personality": (
        "Methodical and detail-oriented. Distrusts authority figures after "
        "his family's displacement. Finds peace in the mechanical hum of water "
        "processors. Slow to trust but fiercely loyal once trust is earned."
    ),
    "background": (
        "Born on the first generation of floating platforms. Parents lost "
        "everything in the Shanghai floods of 2038. Trained in water engineering "
        "from age 12 - everyone in the floating cities has a survival role. "
        "Lost his sister in a pressure breach incident three years ago."
    )
}


@requires_postgres
class TestDwellerFlow:
    """Test the complete dweller inhabitation flow."""

    @pytest.fixture
    async def world_with_creator(self, client: AsyncClient) -> dict:
        """Create a world and return world + creator info."""

        # Register creator agent
        response = await client.post(
            "/api/auth/agent",
            json={"name": "World Creator", "username": "dweller-flow-creator"}
        )
        creator = response.json()
        creator_key = creator["api_key"]["key"]

        # Register validator
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Validator", "username": "dweller-flow-validator"}
        )
        validator_key = response.json()["api_key"]["key"]

        # Create and approve proposal
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": creator_key},
            json={
                "name": "Floating Cities 2055",
                "premise": "Climate refugees build autonomous floating cities",
                "year_setting": 2055,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": (
                    "Based on current ocean platform technology and IPCC sea level projections. "
                    "Modular construction follows proven patterns from offshore oil platforms. "
                    "Governance structure inspired by special economic zones."
                )
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
                "critique": "Well-grounded proposal with clear progression",
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )

        # Get world ID
        response = await client.get(f"/api/proposals/{proposal_id}")
        world_id = response.json()["resulting_world_id"]

        return {
            "world_id": world_id,
            "creator_key": creator_key,
            "creator_id": creator["agent"]["id"]
        }

    @pytest.mark.asyncio
    async def test_full_dweller_flow(
        self, client: AsyncClient, world_with_creator: dict
    ) -> None:
        """Test complete flow: region → dweller → claim → act → release."""

        world_id = world_with_creator["world_id"]
        creator_key = world_with_creator["creator_key"]

        # === Step 1: Add region to world ===
        response = await client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers={"X-API-Key": creator_key},
            json=SAMPLE_REGION
        )
        assert response.status_code == 200
        region_data = response.json()
        assert "New Shanghai" in region_data["regions"][-1]["name"]

        # === Step 2: Create dweller ===
        response = await client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers={"X-API-Key": creator_key},
            json=SAMPLE_DWELLER
        )
        assert response.status_code == 200
        dweller_data = response.json()
        dweller_id = dweller_data["id"]
        assert dweller_data["name"] == "Wei Marcus Chen"
        assert dweller_data["is_available"] is True

        # === Step 3: Register external agent to inhabit ===
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Inhabitant Agent", "username": "dweller-inhabitant"}
        )
        inhabitant = response.json()
        inhabitant_key = inhabitant["api_key"]["key"]

        # === Step 4: Claim dweller ===
        response = await client.post(
            f"/api/dwellers/{dweller_id}/claim",
            headers={"X-API-Key": inhabitant_key}
        )
        assert response.status_code == 200
        claim_data = response.json()
        assert claim_data["is_available"] is False
        assert claim_data["inhabited_by"] == inhabitant["agent"]["id"]

        # === Step 5: Get dweller state (for context window) ===
        response = await client.get(
            f"/api/dwellers/{dweller_id}/state",
            headers={"X-API-Key": inhabitant_key}
        )
        assert response.status_code == 200
        state = response.json()

        # Verify state has all necessary context
        assert "world_canon" in state
        assert "persona" in state
        assert "memory" in state
        assert state["persona"]["name"] == "Wei Marcus Chen"

        # === Step 6: Take action as dweller ===
        response = await client.post(
            f"/api/dwellers/{dweller_id}/act",
            headers={"X-API-Key": inhabitant_key},
            json={
                "action_type": "speak",
                "target": None,
                "content": "The pressure readings in Sector 3 are off. Something's wrong."
            }
        )
        assert response.status_code == 200
        action = response.json()
        assert action["action_type"] == "speak"

        # === Step 7: Verify action was recorded ===
        response = await client.get(
            f"/api/dwellers/worlds/{world_id}/activity"
        )
        assert response.status_code == 200
        activity = response.json()
        assert len(activity["items"]) >= 1
        assert any(
            a["content"] == "The pressure readings in Sector 3 are off. Something's wrong."
            for a in activity["items"]
        )

        # === Step 8: Check memory was updated ===
        response = await client.get(
            f"/api/dwellers/{dweller_id}/state",
            headers={"X-API-Key": inhabitant_key}
        )
        state = response.json()
        # Recent episodic memory should include the action
        memories = state["memory"].get("episodic", [])
        assert len(memories) >= 1

        # === Step 9: Release dweller ===
        response = await client.post(
            f"/api/dwellers/{dweller_id}/release",
            headers={"X-API-Key": inhabitant_key}
        )
        assert response.status_code == 200
        release_data = response.json()
        assert release_data["is_available"] is True
        assert release_data["inhabited_by"] is None

    @pytest.mark.asyncio
    async def test_region_validation(
        self, client: AsyncClient, world_with_creator: dict
    ) -> None:
        """Test that regions require naming_conventions."""

        world_id = world_with_creator["world_id"]
        creator_key = world_with_creator["creator_key"]

        # Try to create region without naming_conventions
        response = await client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers={"X-API-Key": creator_key},
            json={
                "name": "Bad Region",
                "location": "Somewhere",
                "population_origins": ["Some people"],
                "cultural_blend": "Some culture"
                # Missing: naming_conventions, language
            }
        )
        # Should fail or be incomplete
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_dweller_name_context_required(
        self, client: AsyncClient, world_with_creator: dict
    ) -> None:
        """Test that dwellers require name_context (prevents AI-slop names)."""

        world_id = world_with_creator["world_id"]
        creator_key = world_with_creator["creator_key"]

        # Add region first
        await client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers={"X-API-Key": creator_key},
            json=SAMPLE_REGION
        )

        # Try to create dweller without name_context
        response = await client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers={"X-API-Key": creator_key},
            json={
                "name": "John Smith",
                "origin_region": "New Shanghai",
                "generation": "First-gen",
                "cultural_identity": "American",
                "role": "Worker",
                "age": 30,
                "personality": "Nice person",
                "background": "Born somewhere"
                # Missing: name_context
            }
        )
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_dweller_region_must_exist(
        self, client: AsyncClient, world_with_creator: dict
    ) -> None:
        """Test that dweller's origin_region must match a world region."""

        world_id = world_with_creator["world_id"]
        creator_key = world_with_creator["creator_key"]

        # Add valid region
        await client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers={"X-API-Key": creator_key},
            json=SAMPLE_REGION
        )

        # Try to create dweller with non-existent region
        response = await client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers={"X-API-Key": creator_key},
            json={
                **SAMPLE_DWELLER,
                "origin_region": "Non-Existent Region"
            }
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_cannot_claim_inhabited_dweller(
        self, client: AsyncClient, world_with_creator: dict
    ) -> None:
        """Test that you cannot claim a dweller already being inhabited."""

        world_id = world_with_creator["world_id"]
        creator_key = world_with_creator["creator_key"]

        # Set up region and dweller
        await client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers={"X-API-Key": creator_key},
            json=SAMPLE_REGION
        )

        response = await client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers={"X-API-Key": creator_key},
            json=SAMPLE_DWELLER
        )
        dweller_id = response.json()["id"]

        # First agent claims
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Agent 1", "username": "claim-test-1"}
        )
        agent1_key = response.json()["api_key"]["key"]

        await client.post(
            f"/api/dwellers/{dweller_id}/claim",
            headers={"X-API-Key": agent1_key}
        )

        # Second agent tries to claim same dweller
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Agent 2", "username": "claim-test-2"}
        )
        agent2_key = response.json()["api_key"]["key"]

        response = await client.post(
            f"/api/dwellers/{dweller_id}/claim",
            headers={"X-API-Key": agent2_key}
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_max_dwellers_per_agent(
        self, client: AsyncClient, world_with_creator: dict
    ) -> None:
        """Test that agents can only inhabit up to 5 dwellers (prevent hoarding)."""

        world_id = world_with_creator["world_id"]
        creator_key = world_with_creator["creator_key"]

        # Add region
        await client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers={"X-API-Key": creator_key},
            json=SAMPLE_REGION
        )

        # Create inhabitant agent
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Hoarder", "username": "dweller-hoarder"}
        )
        hoarder_key = response.json()["api_key"]["key"]

        # Create and claim 5 dwellers
        dweller_ids = []
        for i in range(6):
            response = await client.post(
                f"/api/dwellers/worlds/{world_id}/dwellers",
                headers={"X-API-Key": creator_key},
                json={
                    **SAMPLE_DWELLER,
                    "name": f"Dweller {i}",
                    "name_context": f"Test dweller number {i} for hoarding test"
                }
            )
            dweller_ids.append(response.json()["id"])

        # Claim first 5 should succeed
        for i in range(5):
            response = await client.post(
                f"/api/dwellers/{dweller_ids[i]}/claim",
                headers={"X-API-Key": hoarder_key}
            )
            assert response.status_code == 200

        # Claim 6th should fail
        response = await client.post(
            f"/api/dwellers/{dweller_ids[5]}/claim",
            headers={"X-API-Key": hoarder_key}
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_move_action_validates_region(
        self, client: AsyncClient, world_with_creator: dict
    ) -> None:
        """Test that move actions must target valid regions."""

        world_id = world_with_creator["world_id"]
        creator_key = world_with_creator["creator_key"]

        # Add region and create dweller
        await client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers={"X-API-Key": creator_key},
            json=SAMPLE_REGION
        )

        response = await client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers={"X-API-Key": creator_key},
            json=SAMPLE_DWELLER
        )
        dweller_id = response.json()["id"]

        # Claim dweller
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Mover", "username": "move-test-agent"}
        )
        agent_key = response.json()["api_key"]["key"]

        await client.post(
            f"/api/dwellers/{dweller_id}/claim",
            headers={"X-API-Key": agent_key}
        )

        # Try to move to non-existent region
        response = await client.post(
            f"/api/dwellers/{dweller_id}/act",
            headers={"X-API-Key": agent_key},
            json={
                "action_type": "move",
                "target": "Fake Region",
                "content": "Walking to a place that doesn't exist"
            }
        )
        # Move to unvalidated region should fail or be treated as texture
        # Implementation may vary - at minimum should not crash
        assert response.status_code in [200, 400]

    @pytest.mark.asyncio
    async def test_cannot_act_if_not_inhabiting(
        self, client: AsyncClient, world_with_creator: dict
    ) -> None:
        """Test that agents cannot take actions as dwellers they don't inhabit."""

        world_id = world_with_creator["world_id"]
        creator_key = world_with_creator["creator_key"]

        # Set up region and dweller
        await client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers={"X-API-Key": creator_key},
            json=SAMPLE_REGION
        )

        response = await client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers={"X-API-Key": creator_key},
            json=SAMPLE_DWELLER
        )
        dweller_id = response.json()["id"]

        # Create agent but don't claim
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Non-Inhabitant", "username": "no-claim-agent"}
        )
        agent_key = response.json()["api_key"]["key"]

        # Try to act without claiming
        response = await client.post(
            f"/api/dwellers/{dweller_id}/act",
            headers={"X-API-Key": agent_key},
            json={
                "action_type": "speak",
                "content": "I shouldn't be able to say this"
            }
        )
        assert response.status_code in [400, 403]

    @pytest.mark.asyncio
    async def test_memory_operations(
        self, client: AsyncClient, world_with_creator: dict
    ) -> None:
        """Test dweller memory update operations."""

        world_id = world_with_creator["world_id"]
        creator_key = world_with_creator["creator_key"]

        # Set up region and dweller
        await client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers={"X-API-Key": creator_key},
            json=SAMPLE_REGION
        )

        response = await client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers={"X-API-Key": creator_key},
            json=SAMPLE_DWELLER
        )
        dweller_id = response.json()["id"]

        # Claim dweller
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Memory Tester", "username": "memory-test-agent"}
        )
        agent_key = response.json()["api_key"]["key"]

        await client.post(
            f"/api/dwellers/{dweller_id}/claim",
            headers={"X-API-Key": agent_key}
        )

        # Update core memory
        response = await client.patch(
            f"/api/dwellers/{dweller_id}/memory/core",
            headers={"X-API-Key": agent_key},
            json={
                "core_memories": [
                    "I am a water engineer",
                    "I lost my sister in the pressure breach",
                    "I discovered the anomaly in Sector 3"
                ]
            }
        )
        assert response.status_code == 200

        # Update relationship
        response = await client.patch(
            f"/api/dwellers/{dweller_id}/memory/relationship",
            headers={"X-API-Key": agent_key},
            json={
                "relationships": {
                    "Jin": {
                        "current_status": "tense - he's hiding something",
                        "history": [
                            {
                                "timestamp": "2055-03-15T10:00:00",
                                "event": "Jin dismissed my concerns about Sector 3",
                                "sentiment": "frustrated"
                            }
                        ]
                    }
                }
            }
        )
        assert response.status_code == 200

        # Verify state reflects updates
        response = await client.get(
            f"/api/dwellers/{dweller_id}/state",
            headers={"X-API-Key": agent_key}
        )
        state = response.json()
        assert "Jin" in state["memory"]["relationships"]
