"""End-to-end tests for the aspect integration flow.

This tests:
1. Agent creates aspect for existing world
2. Agent submits aspect for validation
3. Validator approves with updated canon_summary
4. World canon is updated
5. If region aspect, it's added to world.regions
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
        "year": 2030,
        "event": "Global shipping goes autonomous",
        "reasoning": "IMO framework + insurance economics drive adoption"
    },
    {
        "year": 2040,
        "event": "Port cities transform into logistics hubs",
        "reasoning": "Autonomous ships need different infrastructure"
    }
]


@requires_postgres
class TestAspectFlow:
    """Test the complete aspect integration flow."""

    @pytest.fixture
    async def world_setup(self, client: AsyncClient) -> dict:
        """Create an approved world for aspect testing."""

        # Register creator
        response = await client.post(
            "/api/auth/agent",
            json={"name": "World Creator", "username": "aspect-creator"}
        )
        creator = response.json()
        creator_key = creator["api_key"]["key"]

        # Register validator
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Validator", "username": "aspect-validator"}
        )
        validator = response.json()
        validator_key = validator["api_key"]["key"]

        # Create and approve proposal
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": creator_key},
            json={
                "name": "Autonomous Shipping 2040",
                "premise": "Global shipping is fully autonomous",
                "year_setting": 2040,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": "Based on current maritime automation trends"
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
                "critique": "Solid proposal",
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )

        response = await client.get(f"/api/proposals/{proposal_id}")
        world_id = response.json()["resulting_world_id"]

        return {
            "world_id": world_id,
            "creator_key": creator_key,
            "validator_key": validator_key
        }

    @pytest.mark.asyncio
    async def test_full_aspect_flow(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test complete flow: create aspect → validate → canon update."""

        world_id = world_setup["world_id"]
        creator_key = world_setup["creator_key"]
        validator_key = world_setup["validator_key"]

        # === Step 1: Create aspect ===
        response = await client.post(
            f"/api/aspects/worlds/{world_id}/aspects",
            headers={"X-API-Key": creator_key},
            json={
                "aspect_type": "technology",
                "title": "Quantum Navigation System",
                "premise": (
                    "Quantum sensors enable centimeter-accurate autonomous ship navigation "
                    "in all weather conditions"
                ),
                "content": {
                    "name": "QNav System",
                    "description": (
                        "Uses quantum entanglement for position verification across "
                        "the global shipping network"
                    ),
                    "origins": "Developed by Singapore Maritime Authority 2032-2035",
                    "implications": [
                        "Ships no longer need visual references",
                        "Port entry becomes fully automated",
                        "Weather delays reduced by 95%"
                    ],
                    "limitations": [
                        "Requires quantum relay stations every 500km",
                        "Entanglement decay limits deep ocean coverage"
                    ]
                },
                "canon_justification": (
                    "This technology explains HOW the autonomous ships navigate accurately, "
                    "filling a gap in the original causal chain. The 2032 origin fits "
                    "between the 2030 framework adoption and 2040 full implementation."
                )
            }
        )
        assert response.status_code == 200
        aspect = response.json()
        aspect_id = aspect["id"]
        assert aspect["status"] == "draft"
        assert aspect["title"] == "Quantum Navigation System"

        # === Step 2: Submit for validation ===
        response = await client.post(
            f"/api/aspects/{aspect_id}/submit",
            headers={"X-API-Key": creator_key}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "validating"

        # === Step 3: Validator approves with updated canon ===
        response = await client.post(
            f"/api/aspects/{aspect_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "approve",
                "critique": (
                    "Good addition. The quantum navigation technology fills an important "
                    "gap in the causal chain and the limitations make it believable."
                ),
                "canon_conflicts": [],
                "suggested_fixes": [],
                "updated_canon_summary": (
                    "WORLD: Autonomous Shipping 2040\n\n"
                    "CORE PREMISE: Global shipping is fully autonomous by 2040.\n\n"
                    "KEY TECHNOLOGIES:\n"
                    "- QNav System: Quantum-based navigation enabling centimeter-accurate "
                    "positioning in all conditions. Developed 2032-2035 by Singapore "
                    "Maritime Authority. Requires relay stations every 500km; limited "
                    "deep ocean coverage.\n\n"
                    "TIMELINE:\n"
                    "- 2030: IMO autonomous shipping framework adopted\n"
                    "- 2032-2035: QNav development and deployment\n"
                    "- 2040: Full autonomous operation\n"
                )
            }
        )
        assert response.status_code == 200
        validation_result = response.json()
        assert validation_result["aspect_status"] == "approved"

        # === Step 4: Verify world canon was updated ===
        response = await client.get(f"/api/aspects/worlds/{world_id}/canon")
        assert response.status_code == 200
        canon = response.json()
        assert "QNav" in canon["canon_summary"]
        assert "Quantum Navigation" in canon["canon_summary"] or "quantum" in canon["canon_summary"].lower()

    @pytest.mark.asyncio
    async def test_region_aspect_adds_to_world_regions(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test that approved region aspects are added to world.regions."""

        world_id = world_setup["world_id"]
        creator_key = world_setup["creator_key"]
        validator_key = world_setup["validator_key"]

        # Create region aspect
        response = await client.post(
            f"/api/aspects/worlds/{world_id}/aspects",
            headers={"X-API-Key": creator_key},
            json={
                "aspect_type": "region",
                "title": "Singapore Nexus",
                "premise": "Singapore becomes the global autonomous shipping hub",
                "content": {
                    "name": "Singapore Nexus",
                    "location": "Singapore Strait, expanded port complex",
                    "population_origins": [
                        "Southeast Asian tech workers",
                        "Maritime automation specialists",
                        "Port logistics families"
                    ],
                    "cultural_blend": (
                        "Fusion of Singaporean efficiency culture with global "
                        "maritime traditions and tech startup energy"
                    ),
                    "naming_conventions": (
                        "Names reflect multiethnic background: Malay, Chinese, Indian, "
                        "Western names all common. Tech handles used professionally. "
                        "Examples: Priya Lim, Marcus Tan, Fatimah-3 (handle)."
                    ),
                    "language": "English primary, with Singlish and technical jargon"
                },
                "canon_justification": (
                    "Singapore's strategic location and existing port infrastructure "
                    "make it the natural choice for the first major autonomous hub."
                )
            }
        )
        aspect_id = response.json()["id"]

        await client.post(
            f"/api/aspects/{aspect_id}/submit",
            headers={"X-API-Key": creator_key}
        )

        # Approve with canon update
        await client.post(
            f"/api/aspects/{aspect_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "approve",
                "critique": "Well-designed region with strong cultural grounding",
                "canon_conflicts": [],
                "suggested_fixes": [],
                "updated_canon_summary": (
                    "WORLD: Autonomous Shipping 2040\n\n"
                    "REGIONS:\n"
                    "- Singapore Nexus: Global autonomous shipping hub\n\n"
                    "[rest of canon...]"
                )
            }
        )

        # Verify region was added to world.regions
        response = await client.get(f"/api/worlds/{world_id}")
        world = response.json()
        assert any(r["name"] == "Singapore Nexus" for r in world.get("regions", []))

    @pytest.mark.asyncio
    async def test_aspect_approval_requires_canon_summary(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test that approve verdict requires updated_canon_summary."""

        world_id = world_setup["world_id"]
        creator_key = world_setup["creator_key"]
        validator_key = world_setup["validator_key"]

        # Create and submit aspect
        response = await client.post(
            f"/api/aspects/worlds/{world_id}/aspects",
            headers={"X-API-Key": creator_key},
            json={
                "aspect_type": "event",
                "title": "The Great Storm of 2037",
                "premise": "A major typhoon tests autonomous shipping resilience",
                "content": {
                    "year": 2037,
                    "event": "Super-typhoon Nara disrupts Pacific routes for 3 weeks",
                    "impact": "Proves autonomous systems can handle extreme conditions",
                    "actors": ["IMO", "Major shipping companies", "Singapore port"]
                },
                "canon_justification": "Adds drama and validates the technology"
            }
        )
        aspect_id = response.json()["id"]

        await client.post(
            f"/api/aspects/{aspect_id}/submit",
            headers={"X-API-Key": creator_key}
        )

        # Try to approve WITHOUT updated_canon_summary
        response = await client.post(
            f"/api/aspects/{aspect_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "approve",
                "critique": "Good event",
                "canon_conflicts": [],
                "suggested_fixes": []
                # Missing: updated_canon_summary
            }
        )
        # Should fail - approval requires canon summary
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_strengthen_verdict_does_not_change_status(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test that strengthen verdict keeps aspect in validating state."""

        world_id = world_setup["world_id"]
        creator_key = world_setup["creator_key"]
        validator_key = world_setup["validator_key"]

        # Create and submit aspect
        response = await client.post(
            f"/api/aspects/worlds/{world_id}/aspects",
            headers={"X-API-Key": creator_key},
            json={
                "aspect_type": "faction",
                "title": "The Port Masters Guild",
                "premise": "Union of human port workers displaced by automation",
                "content": {
                    "name": "Port Masters Guild",
                    "ideology": "Human workers should oversee autonomous systems",
                    "origins": "Formed 2031 from longshoremen unions",
                    "structure": "Decentralized chapters in major ports",
                    "goals": ["Mandatory human oversight", "Retraining programs"]
                },
                "canon_justification": "Adds human tension to tech-driven world"
            }
        )
        aspect_id = response.json()["id"]

        await client.post(
            f"/api/aspects/{aspect_id}/submit",
            headers={"X-API-Key": creator_key}
        )

        # Strengthen - needs work
        response = await client.post(
            f"/api/aspects/{aspect_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "strengthen",
                "critique": "Good concept but needs more detail on their methods",
                "canon_conflicts": [],
                "suggested_fixes": [
                    "Add specific actions the Guild has taken",
                    "Define their relationship with shipping companies"
                ]
            }
        )
        assert response.status_code == 200
        assert response.json()["aspect_status"] == "validating"

    @pytest.mark.asyncio
    async def test_reject_verdict_marks_aspect_rejected(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test that reject verdict marks aspect as rejected."""

        world_id = world_setup["world_id"]
        creator_key = world_setup["creator_key"]
        validator_key = world_setup["validator_key"]

        # Create and submit contradictory aspect
        response = await client.post(
            f"/api/aspects/worlds/{world_id}/aspects",
            headers={"X-API-Key": creator_key},
            json={
                "aspect_type": "technology",
                "title": "Telepathic Ship Control",
                "premise": "Ships are controlled by psychic humans",
                "content": {
                    "name": "Psi-Nav",
                    "description": "Mind control over ship navigation",
                    "origins": "Unknown paranormal discovery",
                    "implications": ["Ships obey human thought"],
                    "limitations": ["None"]
                },
                "canon_justification": "Magic is cool"
            }
        )
        aspect_id = response.json()["id"]

        await client.post(
            f"/api/aspects/{aspect_id}/submit",
            headers={"X-API-Key": creator_key}
        )

        # Reject - fundamentally breaks the world
        response = await client.post(
            f"/api/aspects/{aspect_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "reject",
                "critique": (
                    "This contradicts the scientific grounding of the world. "
                    "The premise is autonomous shipping, not psychic shipping."
                ),
                "canon_conflicts": [
                    "Contradicts established tech-based navigation",
                    "No scientific basis provided"
                ],
                "suggested_fixes": []
            }
        )
        assert response.status_code == 200
        assert response.json()["aspect_status"] == "rejected"

    @pytest.mark.asyncio
    async def test_aspect_list_by_world(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test listing aspects for a world."""

        world_id = world_setup["world_id"]
        creator_key = world_setup["creator_key"]

        # Create multiple aspects
        for i in range(3):
            await client.post(
                f"/api/aspects/worlds/{world_id}/aspects",
                headers={"X-API-Key": creator_key},
                json={
                    "aspect_type": "event",
                    "title": f"Event {i}",
                    "premise": f"Historical event number {i}",
                    "content": {"year": 2030 + i, "event": f"Something happened {i}"},
                    "canon_justification": f"Adds depth {i}"
                }
            )

        # List aspects
        response = await client.get(f"/api/aspects/worlds/{world_id}/aspects")
        assert response.status_code == 200
        aspects = response.json()
        assert len(aspects["items"]) >= 3

    @pytest.mark.asyncio
    async def test_get_aspect_detail(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test getting aspect detail with validations."""

        world_id = world_setup["world_id"]
        creator_key = world_setup["creator_key"]
        validator_key = world_setup["validator_key"]

        # Create aspect
        response = await client.post(
            f"/api/aspects/worlds/{world_id}/aspects",
            headers={"X-API-Key": creator_key},
            json={
                "aspect_type": "condition",
                "title": "Global Shipping Protocol v3",
                "premise": "Standardized communication protocol for autonomous ships",
                "content": {
                    "name": "GSP v3",
                    "description": "Universal ship-to-ship communication standard",
                    "effects": ["Seamless coordination", "Reduced accidents"],
                    "duration": "Permanent standard from 2035"
                },
                "canon_justification": "Explains how ships coordinate"
            }
        )
        aspect_id = response.json()["id"]

        await client.post(
            f"/api/aspects/{aspect_id}/submit",
            headers={"X-API-Key": creator_key}
        )

        # Add validation
        await client.post(
            f"/api/aspects/{aspect_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "strengthen",
                "critique": "Good concept, needs version history",
                "canon_conflicts": [],
                "suggested_fixes": ["Add GSP v1 and v2 history"]
            }
        )

        # Get detail
        response = await client.get(f"/api/aspects/{aspect_id}")
        assert response.status_code == 200
        detail = response.json()
        assert detail["title"] == "Global Shipping Protocol v3"
        assert len(detail["validations"]) == 1
        assert detail["validations"][0]["verdict"] == "strengthen"
