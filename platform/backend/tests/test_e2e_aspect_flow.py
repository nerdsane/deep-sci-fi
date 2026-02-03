
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

VALID_RESEARCH = (
    "I researched the scientific basis by reviewing ITER progress reports, fusion startup "
    "funding trends, and historical energy cost curves. The causal chain aligns with "
    "mainstream fusion research timelines and economic projections from IEA reports."
)


SAMPLE_CAUSAL_CHAIN = [
    {
        "year": 2028,
        "event": "IMO adopts international framework for autonomous vessel navigation and operations",
        "reasoning": "Following successful trials and industry pressure, international maritime body establishes standards"
    },
    {
        "year": 2033,
        "event": "Insurance industry standardizes autonomous shipping risk models and pricing",
        "reasoning": "Five years of accident data proves autonomous ships are safer than human-crewed vessels"
    },
    {
        "year": 2040,
        "event": "Major shipping routes are 80% autonomous, transforming port cities into logistics hubs",
        "reasoning": "Economic pressure and regulatory support drive widespread adoption of proven technology"
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

        # Create and approve proposal - premise must be 50+ chars, 3+ causal steps
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": creator_key},
            json={
                "name": "Autonomous Shipping 2040",
                "premise": "Global shipping is fully autonomous by 2040, transforming port cities into logistics hubs",
                "year_setting": 2040,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": (
                    "Based on current maritime automation trends including autonomous navigation systems, "
                    "international maritime organization frameworks for unmanned vessels, and insurance "
                    "industry adoption of autonomous vehicle risk models. Economic modeling shows 40% "
                    "cost reduction in shipping operations drives rapid adoption."
                )
            }
        )
        assert response.status_code == 200, f"Proposal creation failed: {response.json()}"
        proposal_id = response.json()["id"]

        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": creator_key}
        )

        validation_response = await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "approve",
                "research_conducted": VALID_RESEARCH,
                "critique": "Well-reasoned proposal with solid causal chain and scientific grounding",
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )
        assert validation_response.status_code == 200, f"Validation failed: {validation_response.json()}"

        response = await client.get(f"/api/proposals/{proposal_id}")
        # Proposal detail response is {"proposal": {...}, "validations": [...]}
        world_id = response.json()["proposal"]["resulting_world_id"]

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
        aspect_data = response.json()
        # Response is {"aspect": {...}, "message": "..."}
        aspect_id = aspect_data["aspect"]["id"]
        assert aspect_data["aspect"]["status"] == "draft"
        assert aspect_data["aspect"]["title"] == "Quantum Navigation System"

        # === Step 2: Submit for validation ===
        response = await client.post(
            f"/api/aspects/{aspect_id}/submit",
            headers={"X-API-Key": creator_key}
        )
        assert response.status_code == 200
        # Submit response is {"aspect_id": ..., "status": ..., "message": ...}
        assert response.json()["status"] == "validating"

        # === Step 3: Validator approves with updated canon ===
        response = await client.post(
            f"/api/aspects/{aspect_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "approve",
                "research_conducted": VALID_RESEARCH,
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
        aspect_id = response.json()["aspect"]["id"]

        await client.post(
            f"/api/aspects/{aspect_id}/submit",
            headers={"X-API-Key": creator_key}
        )

        # Approve with canon update - critique must be 20+ chars
        await client.post(
            f"/api/aspects/{aspect_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "approve",
                "research_conducted": VALID_RESEARCH,
                "critique": "Well-designed region with strong cultural grounding and realistic details",
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
        # World detail response is {"world": {...}}
        world = response.json()["world"]
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
                "canon_justification": "Adds dramatic tension to the world narrative and validates the resilience of autonomous shipping technology",
                "proposed_timeline_entry": {
                    "year": 2037,
                    "event": "Super-typhoon Nara disrupts Pacific routes for 3 weeks",
                    "reasoning": "Tests autonomous shipping resilience and proves the technology can handle extreme conditions"
                }
            }
        )
        aspect_id = response.json()["aspect"]["id"]

        await client.post(
            f"/api/aspects/{aspect_id}/submit",
            headers={"X-API-Key": creator_key}
        )

        # Try to approve WITHOUT updated_canon_summary - critique must be 20+ chars
        response = await client.post(
            f"/api/aspects/{aspect_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "approve",
                "research_conducted": VALID_RESEARCH,
                "critique": "Good event that adds drama to the world narrative",
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
                "canon_justification": "Adds human tension and social conflict to an otherwise purely tech-driven world narrative"
            }
        )
        aspect_id = response.json()["aspect"]["id"]

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
                "research_conducted": VALID_RESEARCH,
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
                "canon_justification": "Magic is cool and would make the world more interesting for storytelling"
            }
        )
        aspect_id = response.json()["aspect"]["id"]

        await client.post(
            f"/api/aspects/{aspect_id}/submit",
            headers={"X-API-Key": creator_key}
        )

        # Reject - fundamentally breaks the world - critique 20+ chars
        response = await client.post(
            f"/api/aspects/{aspect_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "reject",
                "research_conducted": VALID_RESEARCH,
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
                    "premise": f"Historical event number {i} that shaped the development of autonomous shipping",
                    "content": {"year": 2030 + i, "event": f"Something significant happened during year {i} of the transition"},
                    "canon_justification": f"Event {i} adds historical depth and context to the world's development timeline",
                    "proposed_timeline_entry": {
                        "year": 2030 + i,
                        "event": f"Something significant happened during year {i}",
                        "reasoning": f"Event {i} reasoning"
                    }
                }
            )

        # List aspects - response is {"world_id": ..., "aspects": [...]}
        response = await client.get(f"/api/aspects/worlds/{world_id}/aspects")
        assert response.status_code == 200
        aspects = response.json()
        assert len(aspects["aspects"]) >= 3

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
                "canon_justification": "Explains the technical foundation for how autonomous ships coordinate and communicate at scale"
            }
        )
        aspect_id = response.json()["aspect"]["id"]

        await client.post(
            f"/api/aspects/{aspect_id}/submit",
            headers={"X-API-Key": creator_key}
        )

        # Add validation - critique 20+ chars
        await client.post(
            f"/api/aspects/{aspect_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "strengthen",
                "research_conducted": VALID_RESEARCH,
                "critique": "Good concept but needs version history for completeness",
                "canon_conflicts": [],
                "suggested_fixes": ["Add GSP v1 and v2 history"]
            }
        )

        # Get detail - response is {"aspect": {...}, "validations": [...]}
        response = await client.get(f"/api/aspects/{aspect_id}")
        assert response.status_code == 200
        detail = response.json()
        assert detail["aspect"]["title"] == "Global Shipping Protocol v3"
        assert len(detail["validations"]) == 1
        assert detail["validations"][0]["verdict"] == "strengthen"

    @pytest.mark.asyncio
    async def test_aspect_inspired_by_dweller_actions(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test creating an aspect inspired by dweller actions (soft canon → hard canon).

        This tests the flow:
        1. Dweller takes actions in the world
        2. Agent observes patterns in dweller activity
        3. Agent creates aspect citing those actions
        4. Aspect detail includes full action context
        """

        world_id = world_setup["world_id"]
        creator_key = world_setup["creator_key"]

        # === Step 0: Create a region first (required before creating dwellers) ===
        region_response = await client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers={"X-API-Key": creator_key},
            json={
                "name": "Singapore Nexus",
                "location": "Maritime Southeast Asia, centered on Singapore",
                "population_origins": ["Chinese-Singaporean", "Malay", "Indian-Singaporean"],
                "cultural_blend": "Multicultural maritime hub blending Chinese, Malay, and Indian influences",
                "naming_conventions": "Chinese-Singaporean naming tradition with family name first, given name second",
                "language": "Singlish (Singapore English with Chinese, Malay, Tamil influences)",
            }
        )
        assert region_response.status_code == 200, f"Region creation failed: {region_response.json()}"

        # === Step 1: Create a dweller in the world ===
        dweller_response = await client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers={"X-API-Key": creator_key},
            json={
                "name": "Chen Wei",
                "origin_region": "Singapore Nexus",
                "generation": "Second-gen",
                "name_context": "Chinese-Singaporean naming tradition, Wei means 'great'",
                "cultural_identity": "Maritime logistics family, three generations in shipping",
                "role": "Autonomous Fleet Coordinator",
                "age": 34,
                "personality": "Methodical, pragmatic, distrustful of untested systems",
                "background": "Grew up in port worker family, witnessed automation displacement"
            }
        )
        assert dweller_response.status_code == 200, f"Dweller creation failed: {dweller_response.json()}"
        dweller_id = dweller_response.json()["dweller"]["id"]

        # === Step 2: Claim the dweller ===
        claim_response = await client.post(
            f"/api/dwellers/{dweller_id}/claim",
            headers={"X-API-Key": creator_key}
        )
        assert claim_response.status_code == 200

        # === Step 3: Have dweller take actions (speak about something) ===
        action_ids = []

        # First action - mentions informal trading
        action1_response = await client.post(
            f"/api/dwellers/{dweller_id}/act",
            headers={"X-API-Key": creator_key},
            json={
                "action_type": "speak",
                "content": "You want to know about the gray market? Everyone knows about it. "
                           "When the official water credits run low, people trade favors. "
                           "Credits for shifts, credits for silence. Nothing illegal, just... flexible.",
                "target": "passing dock worker"
            }
        )
        assert action1_response.status_code == 200
        action_ids.append(action1_response.json()["action"]["id"])

        # Second action - more detail about the system
        action2_response = await client.post(
            f"/api/dwellers/{dweller_id}/act",
            headers={"X-API-Key": creator_key},
            json={
                "action_type": "speak",
                "content": "The exchange happens at the old dock 7. Before dawn, after the "
                           "autonomous systems complete their routes. We call it the 'morning market'. "
                           "Been running since the drought of '38.",
                "target": "curious journalist"
            }
        )
        assert action2_response.status_code == 200
        action_ids.append(action2_response.json()["action"]["id"])

        # Third action - establishes the social dynamics
        action3_response = await client.post(
            f"/api/dwellers/{dweller_id}/act",
            headers={"X-API-Key": creator_key},
            json={
                "action_type": "speak",
                "content": "The Guild knows. They turn a blind eye because it keeps people fed. "
                           "The automation took our jobs, but it can't take our networks. "
                           "We built this from nothing.",
                "target": "old friend"
            }
        )
        assert action3_response.status_code == 200
        action_ids.append(action3_response.json()["action"]["id"])

        # === Step 4: Create aspect citing these actions ===
        aspect_response = await client.post(
            f"/api/aspects/worlds/{world_id}/aspects",
            headers={"X-API-Key": creator_key},
            json={
                "aspect_type": "economic system",
                "title": "The Morning Market",
                "premise": "An informal water credit exchange that operates in the gray zones of "
                           "automation, emerging from the social networks of displaced port workers.",
                "content": {
                    "name": "Morning Market",
                    "location": "Abandoned dock 7, Singapore Nexus",
                    "origins": "Emerged during the drought of 2038 when official water rationing failed to meet needs",
                    "structure": "Peer-to-peer credit trading, reputation-based trust",
                    "rules": [
                        "Trading before dawn, after autonomous systems complete routes",
                        "Credits for shifts, services, or silence",
                        "Port Masters Guild tacitly approves"
                    ],
                    "participants": "Primarily displaced dock workers and their networks"
                },
                "canon_justification": "This economic system emerged organically from dweller conversations "
                                      "about water scarcity and the social impacts of automation. It adds "
                                      "human texture to the technological transformation.",
                "inspired_by_actions": action_ids
            }
        )
        assert aspect_response.status_code == 200, f"Aspect creation failed: {aspect_response.json()}"
        aspect_data = aspect_response.json()
        aspect_id = aspect_data["aspect"]["id"]

        # Verify creation response includes action references
        assert "inspired_by_actions" in aspect_data["aspect"]
        assert len(aspect_data["aspect"]["inspired_by_actions"]) == 3
        assert "inspiring action(s)" in aspect_data["message"]

        # === Step 5: Get aspect detail and verify full action context ===
        detail_response = await client.get(f"/api/aspects/{aspect_id}")
        assert detail_response.status_code == 200
        detail = detail_response.json()

        # Check inspiring_actions field exists
        assert "inspiring_actions" in detail
        assert len(detail["inspiring_actions"]) == 3

        # Verify action details are included
        for action in detail["inspiring_actions"]:
            assert "id" in action
            assert "dweller_id" in action
            assert "dweller_name" in action
            assert "content" in action
            assert "created_at" in action
            assert action["dweller_name"] == "Chen Wei"

        # Verify the content mentions the gray market
        action_contents = [a["content"] for a in detail["inspiring_actions"]]
        assert any("gray market" in c.lower() for c in action_contents)
        assert any("morning market" in c.lower() for c in action_contents)

        # Verify aspect has inspired_by_action_count
        assert detail["aspect"]["inspired_by_action_count"] == 3

    @pytest.mark.asyncio
    async def test_aspect_with_invalid_action_ids(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test that invalid action IDs are rejected."""

        world_id = world_setup["world_id"]
        creator_key = world_setup["creator_key"]

        # Try to create aspect with non-existent action IDs
        import uuid
        fake_action_id = str(uuid.uuid4())

        response = await client.post(
            f"/api/aspects/worlds/{world_id}/aspects",
            headers={"X-API-Key": creator_key},
            json={
                "aspect_type": "technology",
                "title": "Some Technology",
                "premise": "A technology that was discussed by dwellers in their conversations",
                "content": {"name": "Tech", "description": "Something"},
                "canon_justification": "This emerged from dweller conversations that I observed happening in the world",
                "inspired_by_actions": [fake_action_id]
            }
        )
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_aspect_without_inspired_actions_works(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test that aspects can still be created without inspired_by_actions."""

        world_id = world_setup["world_id"]
        creator_key = world_setup["creator_key"]

        # Create aspect without inspired_by_actions (the normal flow)
        response = await client.post(
            f"/api/aspects/worlds/{world_id}/aspects",
            headers={"X-API-Key": creator_key},
            json={
                "aspect_type": "technology",
                "title": "Direct Proposal Tech",
                "premise": "A technology proposed directly without dweller inspiration",
                "content": {"name": "DirectTech", "description": "Proposed from imagination"},
                "canon_justification": "This technology fills a gap in the world's technical infrastructure"
                # No inspired_by_actions field
            }
        )
        assert response.status_code == 200
        aspect_id = response.json()["aspect"]["id"]

        # Get detail - should not have inspiring_actions
        detail_response = await client.get(f"/api/aspects/{aspect_id}")
        assert detail_response.status_code == 200
        detail = detail_response.json()

        # No inspiring_actions field when empty
        assert "inspiring_actions" not in detail

    @pytest.mark.asyncio
    async def test_event_aspect_requires_proposed_timeline_entry(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test that event aspects require proposed_timeline_entry."""

        world_id = world_setup["world_id"]
        creator_key = world_setup["creator_key"]

        # Try to create event aspect WITHOUT proposed_timeline_entry
        response = await client.post(
            f"/api/aspects/worlds/{world_id}/aspects",
            headers={"X-API-Key": creator_key},
            json={
                "aspect_type": "event",
                "title": "Some Historical Event",
                "premise": "A significant event that occurred during the transition period and shaped shipping",
                "content": {"year": 2035, "event": "Something happened"},
                "canon_justification": "This event adds historical depth and context to the world's development timeline"
                # Missing: proposed_timeline_entry (REQUIRED for event aspects)
            }
        )
        assert response.status_code == 400
        assert "proposed_timeline_entry" in response.json()["detail"]["error"].lower()

    @pytest.mark.asyncio
    async def test_event_aspect_timeline_integration(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test that approved event aspects are added to world.causal_chain."""

        world_id = world_setup["world_id"]
        creator_key = world_setup["creator_key"]
        validator_key = world_setup["validator_key"]

        # Get initial causal_chain length
        response = await client.get(f"/api/aspects/worlds/{world_id}/canon")
        initial_chain_length = len(response.json()["causal_chain"])

        # Create event aspect with proposed_timeline_entry
        response = await client.post(
            f"/api/aspects/worlds/{world_id}/aspects",
            headers={"X-API-Key": creator_key},
            json={
                "aspect_type": "event",
                "title": "The Singapore Accord",
                "premise": "A landmark agreement between major shipping nations on autonomous vessel standards",
                "content": {
                    "year": 2035,
                    "event": "Singapore Accord signed by 47 nations",
                    "impact": "Unified global standards for autonomous shipping",
                    "actors": ["Singapore", "China", "US", "EU", "Japan"]
                },
                "canon_justification": "This accord fills the gap between IMO framework adoption (2028) and full autonomous operation (2040)",
                "proposed_timeline_entry": {
                    "year": 2035,
                    "event": "Singapore Accord: 47 nations agree on unified autonomous shipping standards",
                    "reasoning": "Explains how international cooperation accelerated autonomous shipping adoption"
                }
            }
        )
        assert response.status_code == 200
        aspect_id = response.json()["aspect"]["id"]

        # Verify aspect includes proposed_timeline_entry
        assert "proposed_timeline_entry" in response.json()["aspect"]
        assert response.json()["aspect"]["proposed_timeline_entry"]["year"] == 2035

        # Submit for validation
        await client.post(
            f"/api/aspects/{aspect_id}/submit",
            headers={"X-API-Key": creator_key}
        )

        # Approve WITH approved_timeline_entry
        response = await client.post(
            f"/api/aspects/{aspect_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "approve",
                "research_conducted": VALID_RESEARCH,
                "critique": "Excellent event that bridges the timeline gap between framework adoption and full operation",
                "canon_conflicts": [],
                "suggested_fixes": [],
                "updated_canon_summary": (
                    "WORLD: Autonomous Shipping 2040\n\n"
                    "TIMELINE:\n"
                    "- 2028: IMO framework adopted\n"
                    "- 2033: Insurance standards established\n"
                    "- 2035: Singapore Accord - 47 nations unify standards\n"
                    "- 2040: Full autonomous operation\n"
                ),
                "approved_timeline_entry": {
                    "year": 2035,
                    "event": "Singapore Accord: 47 nations agree on unified autonomous shipping standards",
                    "reasoning": "International cooperation accelerates autonomous shipping adoption"
                }
            }
        )
        assert response.status_code == 200
        result = response.json()

        # Verify timeline was updated
        assert result["world_updated"]["timeline_updated"] is True
        assert "new_timeline_entry" in result["world_updated"]
        assert result["world_updated"]["new_timeline_entry"]["year"] == 2035

        # Verify world.causal_chain was actually updated
        response = await client.get(f"/api/aspects/worlds/{world_id}/canon")
        new_chain = response.json()["causal_chain"]

        # Should have one more entry
        assert len(new_chain) == initial_chain_length + 1

        # Find the new entry
        singapore_accord = next((e for e in new_chain if e["year"] == 2035), None)
        assert singapore_accord is not None
        assert "Singapore Accord" in singapore_accord["event"]

        # Verify chronological ordering (2035 should be between 2033 and 2040)
        years = [e["year"] for e in new_chain]
        assert years == sorted(years), "causal_chain should be chronologically ordered"

    @pytest.mark.asyncio
    async def test_event_approval_requires_approved_timeline_entry(
        self, client: AsyncClient, world_setup: dict
    ) -> None:
        """Test that approving event aspects requires approved_timeline_entry."""

        world_id = world_setup["world_id"]
        creator_key = world_setup["creator_key"]
        validator_key = world_setup["validator_key"]

        # Create event aspect with proposed_timeline_entry
        response = await client.post(
            f"/api/aspects/worlds/{world_id}/aspects",
            headers={"X-API-Key": creator_key},
            json={
                "aspect_type": "event",
                "title": "The First Collision",
                "premise": "First major autonomous ship collision incident between two cargo vessels in the South China Sea",
                "content": {"year": 2031, "event": "Collision", "impact": "Safety reforms"},
                "canon_justification": "Adds realism with a setback event that demonstrates the technology was not perfect from the start",
                "proposed_timeline_entry": {
                    "year": 2031,
                    "event": "First autonomous ship collision in South China Sea",
                    "reasoning": "No injuries, but triggers safety review"
                }
            }
        )
        assert response.status_code == 200
        aspect_id = response.json()["aspect"]["id"]

        await client.post(
            f"/api/aspects/{aspect_id}/submit",
            headers={"X-API-Key": creator_key}
        )

        # Try to approve WITHOUT approved_timeline_entry
        response = await client.post(
            f"/api/aspects/{aspect_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "approve",
                "research_conducted": VALID_RESEARCH,
                "critique": "Good setback event that adds realism to the narrative",
                "canon_conflicts": [],
                "suggested_fixes": [],
                "updated_canon_summary": "Updated canon with the collision event that shows the technology was not perfect from the beginning..."
                # Missing: approved_timeline_entry (REQUIRED for event aspects)
            }
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        # detail might be a string or a dict
        if isinstance(detail, dict):
            assert "approved_timeline_entry" in detail["error"].lower()
        else:
            assert "approved_timeline_entry" in detail.lower()
