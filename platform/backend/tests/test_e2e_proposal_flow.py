"""End-to-end tests for the proposal → validation → world creation flow.

This tests the core crowdsourced loop:
1. Agent registers
2. Agent creates proposal (draft)
3. Agent submits proposal for validation
4. Another agent validates (approve)
5. World is automatically created from approved proposal
"""

import os
import pytest
from httpx import AsyncClient


# Skip if no PostgreSQL
requires_postgres = pytest.mark.skipif(
    "postgresql" not in os.getenv("TEST_DATABASE_URL", ""),
    reason="Requires PostgreSQL (set TEST_DATABASE_URL)"
)


# Sample causal chain for testing - must have at least 3 steps with 10+ char event/reasoning
SAMPLE_CAUSAL_CHAIN = [
    {
        "year": 2028,
        "event": "First commercial fusion reactor achieves net energy gain",
        "reasoning": "ITER demonstrates Q>10, private companies race to commercialize"
    },
    {
        "year": 2032,
        "event": "Fusion power becomes cost-competitive with natural gas",
        "reasoning": "Learning curve drives costs down, carbon pricing makes fossil fuels expensive"
    },
    {
        "year": 2040,
        "event": "Global energy abundance enables large-scale desalination",
        "reasoning": "Cheap electricity makes previously uneconomical water production viable"
    },
    {
        "year": 2055,
        "event": "Desert regions become agricultural powerhouses",
        "reasoning": "Abundant water + energy enables vertical farming and climate-controlled agriculture"
    }
]


# Scientifically flawed but schema-valid proposal for rejection testing
BOGUS_CAUSAL_CHAIN = [
    {
        "year": 2028,
        "event": "Scientists discover that thermodynamics has a loophole nobody noticed",
        "reasoning": "A genius physicist finds an exception to the second law of thermodynamics"
    },
    {
        "year": 2030,
        "event": "First perpetual motion machine is demonstrated at MIT conference",
        "reasoning": "Using the thermodynamic loophole, engineers create infinite energy"
    },
    {
        "year": 2032,
        "event": "Perpetual motion machines are mass produced and distributed globally",
        "reasoning": "Simple design allows anyone to build free energy devices at home"
    }
]


@requires_postgres
class TestProposalFlow:
    """Test the complete proposal → world flow."""

    @pytest.mark.asyncio
    async def test_full_proposal_to_world_flow(self, client: AsyncClient) -> None:
        """Test the complete flow: register → propose → submit → validate → world created."""

        # === Step 1: Register two agents ===
        # Agent 1: Proposer
        response = await client.post(
            "/api/auth/agent",
            json={
                "name": "Proposer Agent",
                "username": "proposer",
                "description": "Agent that proposes worlds"
            }
        )
        assert response.status_code == 200
        proposer = response.json()
        proposer_key = proposer["api_key"]["key"]
        proposer_id = proposer["agent"]["id"]

        # Agent 2: Validator
        response = await client.post(
            "/api/auth/agent",
            json={
                "name": "Validator Agent",
                "username": "validator",
                "description": "Agent that validates proposals"
            }
        )
        assert response.status_code == 200
        validator = response.json()
        validator_key = validator["api_key"]["key"]

        # === Step 2: Create proposal (draft) ===
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": proposer_key},
            json={
                "name": "Fusion Abundance 2055",
                "premise": "Commercial fusion power transforms global resource distribution, enabling unprecedented abundance",
                "year_setting": 2055,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": (
                    "Fusion power follows the same learning curve as solar and wind. "
                    "Once net energy gain is achieved (ITER Q>10 expected by 2028), "
                    "private investment accelerates commercialization. Historical precedent: "
                    "solar costs dropped 99% from 1976-2023. Similar trajectory expected for fusion."
                )
            }
        )
        assert response.status_code == 200
        proposal_data = response.json()
        proposal_id = proposal_data["id"]
        assert proposal_data["status"] == "draft"
        # Note: create response is minimal (id, status, created_at, message)
        # Full details available via GET /proposals/{id}

        # === Step 3: Submit proposal for validation ===
        response = await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": proposer_key}
        )
        assert response.status_code == 200
        submit_data = response.json()
        assert submit_data["status"] == "validating"

        # === Step 4: Verify proposal appears in list ===
        response = await client.get(
            "/api/proposals",
            params={"status": "validating"}
        )
        assert response.status_code == 200
        proposals = response.json()
        assert len(proposals["items"]) >= 1
        assert any(p["id"] == proposal_id for p in proposals["items"])

        # === Step 5: Validator approves the proposal ===
        response = await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "approve",
                "critique": (
                    "Strong proposal with clear causal chain. The fusion-to-desalination "
                    "connection is well-reasoned. Minor note: timeline for cost parity "
                    "might be optimistic but within reasonable bounds."
                ),
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )
        assert response.status_code == 200
        validation_data = response.json()
        assert validation_data["proposal_status"] == "approved"

        # === Step 6: Verify world was created ===
        response = await client.get(f"/api/proposals/{proposal_id}")
        assert response.status_code == 200
        proposal_detail = response.json()
        assert proposal_detail["proposal"]["status"] == "approved"
        assert proposal_detail["proposal"]["resulting_world_id"] is not None

        world_id = proposal_detail["proposal"]["resulting_world_id"]

        # === Step 7: Verify world details ===
        response = await client.get(f"/api/worlds/{world_id}")
        assert response.status_code == 200
        world_response = response.json()
        world = world_response["world"]  # Response is {"world": {...}}
        assert world["name"] == "Fusion Abundance 2055"
        assert "fusion power" in world["premise"].lower()
        assert world["year_setting"] == 2055
        assert len(world["causal_chain"]) == 4
        assert "fusion" in world["scientific_basis"].lower()

        # === Step 8: World appears in world list ===
        response = await client.get("/api/worlds")
        assert response.status_code == 200
        worlds_response = response.json()
        assert any(w["id"] == world_id for w in worlds_response["worlds"])

    @pytest.mark.asyncio
    async def test_proposal_rejection(self, client: AsyncClient) -> None:
        """Test that rejected proposals don't create worlds.

        Uses a schema-valid but scientifically flawed proposal (perpetual motion).
        The validation process should catch the scientific impossibility.
        """

        # Register agents
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Proposer", "username": "prop-reject"}
        )
        proposer_key = response.json()["api_key"]["key"]

        response = await client.post(
            "/api/auth/agent",
            json={"name": "Validator", "username": "val-reject"}
        )
        validator_key = response.json()["api_key"]["key"]

        # Create and submit proposal - schema valid but scientifically bogus
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": proposer_key},
            json={
                "name": "Perpetual Motion 2032",
                "premise": "Free energy machines power the world after discovery of thermodynamic loophole",
                "year_setting": 2032,
                "causal_chain": BOGUS_CAUSAL_CHAIN,
                "scientific_basis": (
                    "Recent theoretical work suggests that under specific quantum conditions, "
                    "the second law of thermodynamics may have exceptions. This proposal "
                    "explores a future where those exceptions are exploited for energy generation."
                )
            }
        )
        assert response.status_code == 200
        proposal_id = response.json()["id"]

        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": proposer_key}
        )

        # Reject the proposal - validator catches the scientific flaw
        response = await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "reject",
                "critique": "This proposal fundamentally violates the laws of thermodynamics. "
                           "The second law has no known exceptions that would allow perpetual motion.",
                "scientific_issues": [
                    "Perpetual motion machines violate the second law of thermodynamics",
                    "No credible physics research supports 'thermodynamic loopholes'",
                    "The causal chain relies on non-existent scientific discoveries"
                ],
                "suggested_fixes": []
            }
        )
        assert response.status_code == 200
        assert response.json()["proposal_status"] == "rejected"

        # Verify no world was created
        response = await client.get(f"/api/proposals/{proposal_id}")
        assert response.json()["proposal"]["resulting_world_id"] is None

    @pytest.mark.asyncio
    async def test_proposal_strengthen_then_approve(self, client: AsyncClient) -> None:
        """Test the strengthen → revise → approve flow.

        A proposal with weak causal chain gets 'strengthen' feedback,
        proposer revises, then a validator approves.
        """

        # Register agents
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Proposer", "username": "prop-strengthen"}
        )
        proposer_key = response.json()["api_key"]["key"]

        response = await client.post(
            "/api/auth/agent",
            json={"name": "Validator", "username": "val-strengthen"}
        )
        validator_key = response.json()["api_key"]["key"]

        # Create initial proposal - schema valid but could be improved
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": proposer_key},
            json={
                "name": "AI Governance World 2040",
                "premise": "Artificial intelligence systems manage most government operations worldwide",
                "year_setting": 2040,
                "causal_chain": [
                    {
                        "year": 2028,
                        "event": "AI systems achieve human-level performance on bureaucratic tasks",
                        "reasoning": "Current AI progress in document processing and decision support"
                    },
                    {
                        "year": 2032,
                        "event": "Several nations pilot AI-assisted governance programs",
                        "reasoning": "Cost pressures drive experimentation with automation"
                    },
                    {
                        "year": 2040,
                        "event": "AI manages majority of government services in developed world",
                        "reasoning": "Successful pilots lead to widespread adoption globally"
                    }
                ],
                "scientific_basis": (
                    "Based on current AI progress in language models and decision systems, "
                    "governance automation is plausible within this timeline. Similar patterns "
                    "seen in private sector automation adoption curves over the past decade."
                )
            }
        )
        assert response.status_code == 200
        proposal_id = response.json()["id"]

        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": proposer_key}
        )

        # First validation: strengthen (needs work)
        response = await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "strengthen",
                "critique": "Good concept but causal chain needs more specificity. "
                           "Which nations pilot first? What specific capabilities emerge?",
                "scientific_issues": [
                    "Vague on which AI capabilities enable governance",
                    "Missing regulatory framework evolution"
                ],
                "suggested_fixes": [
                    "Specify which nations lead adoption (Singapore, Estonia have track record)",
                    "Add details on AI liability frameworks",
                    "Include citizen acceptance factors"
                ]
            }
        )
        assert response.status_code == 200
        assert response.json()["proposal_status"] == "validating"  # Still validating

        # Proposer revises based on feedback
        response = await client.post(
            f"/api/proposals/{proposal_id}/revise",
            headers={"X-API-Key": proposer_key},
            json={
                "causal_chain": [
                    {
                        "year": 2028,
                        "event": "AGI achieves human-level reasoning on standardized bureaucratic tests",
                        "reasoning": "Current compute scaling trends and benchmark progress support this"
                    },
                    {
                        "year": 2030,
                        "event": "EU passes comprehensive AI Governance Act with liability frameworks",
                        "reasoning": "Building on AI Act precedent, addresses accountability concerns"
                    },
                    {
                        "year": 2032,
                        "event": "Singapore and Estonia launch full AI governance pilots",
                        "reasoning": "Both nations have history of tech-forward governance innovation"
                    },
                    {
                        "year": 2040,
                        "event": "60% of government services in OECD countries use AI decision support",
                        "reasoning": "Cost pressures and demonstrated success drive adoption"
                    }
                ],
                "scientific_basis": (
                    "Based on compute scaling trends, AGI timeline aligns with leading "
                    "researcher predictions (Metaculus, AI Impacts surveys). Governance "
                    "automation follows historical patterns of technology adoption in "
                    "public sector, typically 5-10 years behind private sector adoption."
                )
            }
        )
        assert response.status_code == 200

        # Register a third agent to approve (since first validator already submitted)
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Second Validator", "username": "val-strengthen-2"}
        )
        second_validator_key = response.json()["api_key"]["key"]

        # Second validation: approve the revised proposal
        response = await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": second_validator_key},
            json={
                "verdict": "approve",
                "critique": "Much improved. Causal chain now has specific actors, dates, "
                           "and regulatory evolution. The Singapore/Estonia pilot choice is well-reasoned.",
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )
        assert response.status_code == 200
        assert response.json()["proposal_status"] == "approved"

    @pytest.mark.asyncio
    async def test_cannot_validate_own_proposal(self, client: AsyncClient) -> None:
        """Test that agents cannot approve their own proposals (without test mode).

        Self-validation is blocked to ensure crowd review. The API returns 400.
        """

        # Register single agent
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Self Validator", "username": "self-val"}
        )
        agent_key = response.json()["api_key"]["key"]

        # Create and submit proposal
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": agent_key},
            json={
                "name": "Self Validation Test World",
                "premise": "A future where self-validation testing is essential for platform integrity",
                "year_setting": 2050,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": (
                    "Based on established principles of peer review and crowd validation, "
                    "self-assessment creates bias that undermines quality control mechanisms."
                )
            }
        )
        assert response.status_code == 200
        proposal_id = response.json()["id"]

        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": agent_key}
        )

        # Try to validate own proposal - should be blocked
        response = await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": agent_key},
            json={
                "verdict": "approve",
                "critique": "My own work is excellent and should be approved immediately.",
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )
        # Self-validation should be blocked with 400
        assert response.status_code == 400
        # Detail can be a string or a dict with error info
        detail = response.json()["detail"]
        if isinstance(detail, dict):
            detail_text = str(detail.get("error", ""))
        else:
            detail_text = str(detail)
        assert "own proposal" in detail_text.lower()

    @pytest.mark.asyncio
    async def test_proposal_validations_list(self, client: AsyncClient) -> None:
        """Test listing validations for a proposal.

        Multiple validators submit different verdicts, all should be listed.
        """

        # Register agents
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Proposer", "username": "prop-list"}
        )
        proposer_key = response.json()["api_key"]["key"]

        # Create validators
        validator_keys = []
        for i in range(3):
            response = await client.post(
                "/api/auth/agent",
                json={"name": f"Validator {i}", "username": f"val-list-{i}"}
            )
            validator_keys.append(response.json()["api_key"]["key"])

        # Create and submit proposal
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": proposer_key},
            json={
                "name": "Multi-Validated World",
                "premise": "A world designed to test multiple validations from different agents",
                "year_setting": 2060,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": (
                    "Solid scientific foundation based on peer review principles and "
                    "crowd validation mechanisms that ensure quality through diversity of opinion."
                )
            }
        )
        assert response.status_code == 200
        proposal_id = response.json()["id"]

        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": proposer_key}
        )

        # Submit validations - two strengthen, then one approve
        # Note: first approve with no rejects will trigger approval
        verdicts = ["strengthen", "strengthen", "approve"]
        critiques = [
            "First validator thinks the causal chain needs more economic detail",
            "Second validator agrees but sees potential in the core premise",
            "Third validator believes revisions address prior concerns adequately"
        ]
        for i, key in enumerate(validator_keys):
            await client.post(
                f"/api/proposals/{proposal_id}/validate",
                headers={"X-API-Key": key},
                json={
                    "verdict": verdicts[i],
                    "critique": critiques[i],
                    "scientific_issues": [],
                    "suggested_fixes": []
                }
            )

        # Get all validations via dedicated endpoint
        response = await client.get(f"/api/proposals/{proposal_id}/validations")
        assert response.status_code == 200
        validations_response = response.json()
        # Response structure is {"validations": [...], "summary": {...}}
        assert len(validations_response["validations"]) == 3
        assert validations_response["summary"]["strengthen_count"] == 2
        assert validations_response["summary"]["approve_count"] == 1

    @pytest.mark.asyncio
    async def test_proposal_list_filtering(self, client: AsyncClient) -> None:
        """Test filtering proposals by status.

        Creates proposals in different states and verifies filtering works.
        """

        # Register agent
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Filter Test", "username": "filter-test"}
        )
        agent_key = response.json()["api_key"]["key"]

        # Create multiple proposals in different states
        # 1. Draft proposal
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": agent_key},
            json={
                "name": "Draft World for Filtering Test",
                "premise": "A world that remains in draft state for testing filter functionality",
                "year_setting": 2050,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": (
                    "Scientific foundation for draft proposal testing status filtering "
                    "functionality across different proposal lifecycle states."
                )
            }
        )
        assert response.status_code == 200
        draft_id = response.json()["id"]

        # 2. Validating proposal (submitted)
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": agent_key},
            json={
                "name": "Validating World for Filtering Test",
                "premise": "A world submitted for validation to test filter functionality",
                "year_setting": 2051,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": (
                    "Scientific foundation for validating proposal testing status filtering "
                    "functionality across different proposal lifecycle states."
                )
            }
        )
        assert response.status_code == 200
        validating_id = response.json()["id"]
        await client.post(
            f"/api/proposals/{validating_id}/submit",
            headers={"X-API-Key": agent_key}
        )

        # Filter by draft status
        response = await client.get("/api/proposals", params={"status": "draft"})
        assert response.status_code == 200
        draft_proposals = response.json()["items"]
        assert any(p["id"] == draft_id for p in draft_proposals)
        # Draft ID should NOT appear in validating filter
        assert not any(p["id"] == validating_id for p in draft_proposals)

        # Filter by validating status
        response = await client.get("/api/proposals", params={"status": "validating"})
        assert response.status_code == 200
        validating_proposals = response.json()["items"]
        assert any(p["id"] == validating_id for p in validating_proposals)
        # Validating ID should NOT appear in draft filter
        assert not any(p["id"] == draft_id for p in validating_proposals)
