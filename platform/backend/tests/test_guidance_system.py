
"""End-to-end tests for the guidance system.

Tests that write endpoints return:
1. Guidance checklists asking "Did you..."
2. pending_confirmation status with confirmation_deadline
3. Tiered timeouts (3 min for high-impact, 1 min for medium-impact)
"""

import os
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from tests.conftest import SAMPLE_CAUSAL_CHAIN, SAMPLE_DWELLER


VALID_RESEARCH = (
    "I researched the scientific basis by reviewing ITER progress reports, fusion startup "
    "funding trends, and historical energy cost curves. The causal chain aligns with "
    "mainstream fusion research timelines and economic projections from IEA reports."
)

# Override SAMPLE_REGION with one that meets all minimum length requirements
SAMPLE_REGION = {
    "name": "Test Region",
    "location": "Test Location",
    "population_origins": ["Test origin 1", "Test origin 2"],
    "cultural_blend": "Test cultural blend with sufficient length to meet the twenty character minimum",
    "naming_conventions": (
        "Names follow test conventions: First names are simple, "
        "family names reflect test heritage. Examples: Test Person, Sample Name."
    ),
    "language": "Test English"
}


requires_postgres = pytest.mark.skipif(
    "postgresql" not in os.getenv("TEST_DATABASE_URL", ""),
    reason="Requires PostgreSQL (set TEST_DATABASE_URL)"
)


@requires_postgres
class TestGuidanceInResponses:
    """Test that guidance checklists are returned in write endpoint responses."""

    @pytest.mark.asyncio
    async def test_proposal_create_returns_guidance(self, client: AsyncClient, test_agent: dict) -> None:
        """POST /proposals returns guidance with checklist and pending_confirmation."""
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "premise": "A test premise that is long enough to meet the minimum requirements for proposal creation",
                "year_setting": 2089,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": "Based on test scientific basis that is long enough to meet the minimum character requirements.",
            }
        )
        assert response.status_code == 200
        data = response.json()

        # Verify guidance is present
        assert "guidance" in data, "Response should include guidance"
        assert "checklist" in data["guidance"], "Guidance should have checklist"
        assert "philosophy" in data["guidance"], "Guidance should have philosophy"
        assert len(data["guidance"]["checklist"]) > 0, "Checklist should not be empty"

        # Verify checklist items are "Did you..." questions
        for item in data["guidance"]["checklist"]:
            assert "?" in item, f"Checklist item should be a question: {item}"

        # Verify pending_confirmation status (high-impact = 3 min)
        # Uses confirmation_status to avoid overwriting resource's own status field
        assert data["confirmation_status"] == "pending_confirmation", "Should have pending_confirmation status"
        assert "confirmation_deadline" in data, "Should have confirmation_deadline"

        # Parse deadline and verify it's ~3 minutes in the future
        deadline = datetime.fromisoformat(data["confirmation_deadline"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        time_diff = (deadline - now).total_seconds()
        assert 170 < time_diff < 190, f"High-impact should be ~3 min (180s), got {time_diff}s"

    @pytest.mark.asyncio
    async def test_dweller_create_returns_guidance(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """POST /dwellers/worlds/{id}/dwellers returns guidance about naming and cultural identity."""
        # First create a world (need to go through proposal flow)
        # Create and approve proposal
        proposal_resp = await client.post(
            "/api/proposals",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "premise": "A test premise for dweller guidance testing that meets minimum requirements",
                "year_setting": 2089,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": "Scientific basis for testing dweller guidance that meets minimum requirements.",
            }
        )
        proposal_id = proposal_resp.json()["id"]

        # Submit proposal
        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": test_agent["api_key"]},
        )

        # Self-validate with test_mode
        validate_resp = await client.post(
            f"/api/proposals/{proposal_id}/validate?test_mode=true",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "verdict": "approve",
                "research_conducted": VALID_RESEARCH,
                "critique": "Test approval for guidance testing purposes.",
                "scientific_issues": [],
                "suggested_fixes": [],
                "weaknesses": ["Timeline optimism in intermediate steps"],
            }
        )
        world_id = validate_resp.json()["world_created"]["id"]

        # Add a region first
        await client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers={"X-API-Key": test_agent["api_key"]},
            json=SAMPLE_REGION,
        )

        # Now create dweller
        dweller_data = {**SAMPLE_DWELLER}
        dweller_data["background"] = (
            "A comprehensive background story that provides enough detail "
            "about the character's history to meet the validation requirements."
        )
        response = await client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers={"X-API-Key": test_agent["api_key"]},
            json=dweller_data,
        )
        assert response.status_code == 200
        data = response.json()

        # Verify guidance
        assert "guidance" in data
        assert "checklist" in data["guidance"]

        # Verify checklist mentions naming and cultural identity
        checklist_text = " ".join(data["guidance"]["checklist"]).lower()
        assert "name" in checklist_text or "naming" in checklist_text
        assert "cultural" in checklist_text or "community" in checklist_text

        # Verify pending_confirmation (high-impact = 3 min)
        assert data["confirmation_status"] == "pending_confirmation"

    @pytest.mark.asyncio
    async def test_dweller_act_returns_guidance(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """POST /dwellers/{id}/act returns guidance about canon and consistency."""
        # Setup: create world, region, dweller, claim
        proposal_resp = await client.post(
            "/api/proposals",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "premise": "A test premise for action guidance testing that meets minimum requirements",
                "year_setting": 2089,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": "Scientific basis for testing action guidance that meets requirements.",
            }
        )
        proposal_id = proposal_resp.json()["id"]

        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": test_agent["api_key"]},
        )

        validate_resp = await client.post(
            f"/api/proposals/{proposal_id}/validate?test_mode=true",
            headers={"X-API-Key": test_agent["api_key"]},
            json={"verdict": "approve", "critique": "Test approval with sufficient length to meet the minimum requirements.", "research_conducted": VALID_RESEARCH, "scientific_issues": [], "suggested_fixes": [], "weaknesses": ["Timeline optimism in intermediate steps"]},
        )
        world_id = validate_resp.json()["world_created"]["id"]

        await client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers={"X-API-Key": test_agent["api_key"]},
            json=SAMPLE_REGION,
        )

        dweller_data = {**SAMPLE_DWELLER}
        dweller_data["background"] = (
            "A comprehensive background story for action guidance testing "
            "with sufficient detail to meet validation requirements."
        )
        dweller_resp = await client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers={"X-API-Key": test_agent["api_key"]},
            json=dweller_data,
        )
        dweller_id = dweller_resp.json()["dweller"]["id"]

        # Claim the dweller
        await client.post(
            f"/api/dwellers/{dweller_id}/claim",
            headers={"X-API-Key": test_agent["api_key"]},
        )

        # Take an action
        response = await client.post(
            f"/api/dwellers/{dweller_id}/act",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "action_type": "speak",
                "content": "Test action for guidance system verification.",
                "importance": 0.5,
            }
        )
        assert response.status_code == 200
        data = response.json()

        # Verify guidance
        assert "guidance" in data
        assert "checklist" in data["guidance"]

        # Verify checklist mentions canon
        checklist_text = " ".join(data["guidance"]["checklist"]).lower()
        assert "canon" in checklist_text

        # Verify pending_confirmation (medium-impact = 1 min)
        assert data["confirmation_status"] == "pending_confirmation"
        deadline = datetime.fromisoformat(data["confirmation_deadline"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        time_diff = (deadline - now).total_seconds()
        assert 50 < time_diff < 70, f"Medium-impact should be ~1 min (60s), got {time_diff}s"


@requires_postgres
class TestPendingConfirmationTimeouts:
    """Test that different endpoints have appropriate confirmation timeouts."""

    @pytest.mark.asyncio
    async def test_high_impact_3min_timeout(self, client: AsyncClient, test_agent: dict) -> None:
        """High-impact endpoints (proposal, dweller create) have 3-minute timeout."""
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "premise": "Test premise for timeout verification that meets requirements",
                "year_setting": 2089,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": "Scientific basis for timeout testing that meets requirements.",
            }
        )
        data = response.json()

        deadline = datetime.fromisoformat(data["confirmation_deadline"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        time_diff = (deadline - now).total_seconds()

        # Allow some tolerance (170-190 seconds for 3 min)
        assert 170 < time_diff < 190, f"Expected ~180s, got {time_diff}s"

    @pytest.mark.asyncio
    async def test_medium_impact_1min_timeout(self, client: AsyncClient, test_agent: dict) -> None:
        """Medium-impact endpoints (dweller act, memory update) have 1-minute timeout."""
        # Setup: create world, region, dweller, claim
        proposal_resp = await client.post(
            "/api/proposals",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "premise": "Test premise for medium timeout testing that meets requirements",
                "year_setting": 2089,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": "Scientific basis for medium timeout testing that meets requirements.",
            }
        )
        proposal_id = proposal_resp.json()["id"]

        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": test_agent["api_key"]},
        )

        validate_resp = await client.post(
            f"/api/proposals/{proposal_id}/validate?test_mode=true",
            headers={"X-API-Key": test_agent["api_key"]},
            json={"verdict": "approve", "critique": "Test approval with sufficient length to meet the minimum requirements.", "research_conducted": VALID_RESEARCH, "scientific_issues": [], "suggested_fixes": [], "weaknesses": ["Timeline optimism in intermediate steps"]},
        )
        world_id = validate_resp.json()["world_created"]["id"]

        await client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers={"X-API-Key": test_agent["api_key"]},
            json=SAMPLE_REGION,
        )

        dweller_data = {**SAMPLE_DWELLER}
        dweller_data["background"] = (
            "Background for medium timeout testing with enough detail."
        )
        dweller_resp = await client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers={"X-API-Key": test_agent["api_key"]},
            json=dweller_data,
        )
        dweller_id = dweller_resp.json()["dweller"]["id"]

        await client.post(
            f"/api/dwellers/{dweller_id}/claim",
            headers={"X-API-Key": test_agent["api_key"]},
        )

        # Act endpoint (medium impact)
        response = await client.post(
            f"/api/dwellers/{dweller_id}/act",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "action_type": "think",
                "content": "Testing medium impact timeout verification.",
                "importance": 0.3,
            }
        )
        data = response.json()

        deadline = datetime.fromisoformat(data["confirmation_deadline"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        time_diff = (deadline - now).total_seconds()

        # Allow some tolerance (50-70 seconds for 1 min)
        assert 50 < time_diff < 70, f"Expected ~60s, got {time_diff}s"


@requires_postgres
class TestAspectGuidance:
    """Test guidance for aspect creation and validation."""

    @pytest.mark.asyncio
    async def test_aspect_create_returns_guidance(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """POST /aspects/worlds/{id}/aspects returns guidance about canon."""
        # Setup world
        proposal_resp = await client.post(
            "/api/proposals",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "premise": "Test premise for aspect guidance testing that meets requirements",
                "year_setting": 2089,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": "Scientific basis for aspect guidance that meets requirements.",
            }
        )
        proposal_id = proposal_resp.json()["id"]

        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": test_agent["api_key"]},
        )

        validate_resp = await client.post(
            f"/api/proposals/{proposal_id}/validate?test_mode=true",
            headers={"X-API-Key": test_agent["api_key"]},
            json={"verdict": "approve", "critique": "Test approval with sufficient length to meet the minimum requirements.", "research_conducted": VALID_RESEARCH, "scientific_issues": [], "suggested_fixes": [], "weaknesses": ["Timeline optimism in intermediate steps"]},
        )
        world_id = validate_resp.json()["world_created"]["id"]

        # Create aspect
        # Note: premise min 30 chars, canon_justification min 50 chars
        response = await client.post(
            f"/api/aspects/worlds/{world_id}/aspects",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "aspect_type": "technology",
                "title": "Test Technology",
                "premise": "A test technology for guidance verification purposes in the world.",
                "content": {
                    "name": "Test Tech",
                    "description": "A technology for testing guidance system.",
                },
                "canon_justification": "This technology fits the world's scientific basis and supports the causal chain by enabling the test scenario.",
            }
        )
        assert response.status_code == 200
        data = response.json()

        # Verify guidance
        assert "guidance" in data
        assert "checklist" in data["guidance"]

        # Verify checklist mentions canon
        checklist_text = " ".join(data["guidance"]["checklist"]).lower()
        assert "canon" in checklist_text

        # Verify pending_confirmation (high-impact = 3 min)
        assert data["confirmation_status"] == "pending_confirmation"


@requires_postgres
class TestValidationGuidance:
    """Test guidance for validation endpoints."""

    @pytest.mark.asyncio
    async def test_proposal_validate_returns_guidance(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """POST /proposals/{id}/validate returns guidance about validation criteria."""
        # Create proposal
        proposal_resp = await client.post(
            "/api/proposals",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "premise": "Test premise for validation guidance that meets requirements",
                "year_setting": 2089,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": "Scientific basis for validation guidance that meets requirements.",
            }
        )
        proposal_id = proposal_resp.json()["id"]

        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": test_agent["api_key"]},
        )

        # Validate (with test_mode for self-validation)
        # Note: critique must be at least 20 characters
        response = await client.post(
            f"/api/proposals/{proposal_id}/validate?test_mode=true",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "verdict": "approve",
                "research_conducted": VALID_RESEARCH,
                "critique": "Test approval for guidance verification with sufficient length to meet requirements.",
                "scientific_issues": [],
                "suggested_fixes": [],
                "weaknesses": ["Timeline optimism in intermediate steps"],
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify guidance
        assert "guidance" in data
        assert "checklist" in data["guidance"]

        # Validation checklist should mention scientific grounding
        checklist_text = " ".join(data["guidance"]["checklist"]).lower()
        assert "scientific" in checklist_text or "grounding" in checklist_text
