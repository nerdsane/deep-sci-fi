"""E2E tests for Agent Round 1 Feedback features.

Tests the features implemented from the agent round 1 feedback plan:
1. Validation threshold (2 approvals required)
2. research_conducted field requirement
3. Per-agent proposal limits (max 3 active)
4. Notifications polling endpoint
"""

import os
import pytest
from httpx import AsyncClient


# Skip if no PostgreSQL
requires_postgres = pytest.mark.skipif(
    "postgresql" not in os.getenv("TEST_DATABASE_URL", ""),
    reason="Requires PostgreSQL (set TEST_DATABASE_URL)"
)


# Sample causal chain for testing
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
    }
]


# Required research_conducted field content (100+ chars)
VALID_RESEARCH = (
    "I researched the scientific basis by reviewing ITER progress reports, fusion startup "
    "funding trends, and historical energy cost curves. The causal chain aligns with "
    "mainstream fusion research timelines and economic projections from IEA reports."
)


@requires_postgres
class TestValidationThreshold:
    """Test that 2 approvals are required (not just 1)."""

    @pytest.mark.asyncio
    async def test_single_approval_keeps_validating(self, client: AsyncClient) -> None:
        """Verify that a single approval leaves proposal in 'validating' status."""

        # Register proposer and validator
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Proposer", "username": "threshold-proposer"}
        )
        proposer_key = response.json()["api_key"]["key"]

        response = await client.post(
            "/api/auth/agent",
            json={"name": "Validator1", "username": "threshold-validator1"}
        )
        validator1_key = response.json()["api_key"]["key"]

        # Create and submit proposal
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": proposer_key},
            json={
                "name": "Threshold Test World",
                "premise": "A world to test that two approvals are required for approval",
                "year_setting": 2050,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": (
                    "Scientific foundation for testing the validation threshold system "
                    "that requires multiple validators to approve a proposal."
                )
            }
        )
        assert response.status_code == 200
        proposal_id = response.json()["id"]

        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": proposer_key}
        )

        # First validator approves
        response = await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": validator1_key},
            json={
                "verdict": "approve",
                "critique": (
                    "Solid proposal with clear causal chain and scientific basis. "
                    "The timeline is realistic based on current fusion research progress."
                ),
                "research_conducted": VALID_RESEARCH,
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )
        assert response.status_code == 200
        result = response.json()

        # Should still be validating, not approved
        assert result["proposal_status"] == "validating"
        assert result["validation_status"]["approvals"] == 1
        assert result["validation_status"]["needed_for_approval"] == 2

    @pytest.mark.asyncio
    async def test_two_approvals_triggers_approval(self, client: AsyncClient) -> None:
        """Verify that two approvals trigger proposal approval."""

        # Register proposer and two validators
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Proposer", "username": "threshold-proposer2"}
        )
        proposer_key = response.json()["api_key"]["key"]

        response = await client.post(
            "/api/auth/agent",
            json={"name": "Validator1", "username": "threshold-validator2a"}
        )
        validator1_key = response.json()["api_key"]["key"]

        response = await client.post(
            "/api/auth/agent",
            json={"name": "Validator2", "username": "threshold-validator2b"}
        )
        validator2_key = response.json()["api_key"]["key"]

        # Create and submit proposal
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": proposer_key},
            json={
                "name": "Two Approval Test World",
                "premise": "A world to test that two approvals trigger approval status",
                "year_setting": 2051,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": (
                    "Scientific foundation for testing that two validator approvals "
                    "are sufficient to approve a proposal in the validation system."
                )
            }
        )
        assert response.status_code == 200
        proposal_id = response.json()["id"]

        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": proposer_key}
        )

        # First validator approves
        response = await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": validator1_key},
            json={
                "verdict": "approve",
                "critique": "First approval - solid proposal with clear reasoning.",
                "research_conducted": VALID_RESEARCH,
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )
        assert response.status_code == 200
        assert response.json()["proposal_status"] == "validating"

        # Second validator approves
        response = await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": validator2_key},
            json={
                "verdict": "approve",
                "critique": "Second approval - agreeing with first validator assessment.",
                "research_conducted": VALID_RESEARCH,
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )
        assert response.status_code == 200
        result = response.json()

        # Now should be approved
        assert result["proposal_status"] == "approved"
        assert result["world_created"] is True

    @pytest.mark.asyncio
    async def test_rejection_blocks_approval(self, client: AsyncClient) -> None:
        """Verify that a rejection prevents approval even with 2 approvals."""

        # Register proposer and validators
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Proposer", "username": "threshold-proposer3"}
        )
        proposer_key = response.json()["api_key"]["key"]

        validators = []
        for i in range(3):
            response = await client.post(
                "/api/auth/agent",
                json={"name": f"Validator{i}", "username": f"threshold-validator3{i}"}
            )
            validators.append(response.json()["api_key"]["key"])

        # Create and submit proposal
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": proposer_key},
            json={
                "name": "Rejection Blocks Approval World",
                "premise": "A world to test that rejections block approval",
                "year_setting": 2052,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": (
                    "Scientific foundation for testing that rejections properly "
                    "block the approval process in the validation system."
                )
            }
        )
        assert response.status_code == 200
        proposal_id = response.json()["id"]

        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": proposer_key}
        )

        # First validator rejects
        response = await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": validators[0]},
            json={
                "verdict": "reject",
                "critique": "I have serious concerns about the scientific validity.",
                "research_conducted": VALID_RESEARCH,
                "scientific_issues": ["Timeline seems too optimistic"],
                "suggested_fixes": []
            }
        )
        assert response.status_code == 200

        # Second validator approves
        response = await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": validators[1]},
            json={
                "verdict": "approve",
                "critique": "I think the proposal is solid.",
                "research_conducted": VALID_RESEARCH,
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )
        assert response.status_code == 200

        # Third validator approves - now have 2 approvals but also 1 rejection
        response = await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": validators[2]},
            json={
                "verdict": "approve",
                "critique": "Agreeing with second validator.",
                "research_conducted": VALID_RESEARCH,
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )
        assert response.status_code == 200
        result = response.json()

        # Should still be validating because of the rejection
        assert result["proposal_status"] == "validating"


@requires_postgres
class TestResearchConductedField:
    """Test that research_conducted field is required for validation."""

    @pytest.mark.asyncio
    async def test_missing_research_conducted_returns_422(self, client: AsyncClient) -> None:
        """Verify that omitting research_conducted returns a 422 error."""

        # Register agents
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Proposer", "username": "research-proposer"}
        )
        proposer_key = response.json()["api_key"]["key"]

        response = await client.post(
            "/api/auth/agent",
            json={"name": "Validator", "username": "research-validator"}
        )
        validator_key = response.json()["api_key"]["key"]

        # Create and submit proposal
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": proposer_key},
            json={
                "name": "Research Field Test World",
                "premise": "A world to test that research_conducted is required",
                "year_setting": 2053,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": (
                    "Scientific foundation for testing research field requirement."
                )
            }
        )
        proposal_id = response.json()["id"]

        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": proposer_key}
        )

        # Try to validate WITHOUT research_conducted
        response = await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "approve",
                "critique": "Good proposal with solid reasoning.",
                # Missing: research_conducted
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )

        # Should return 422 validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_short_research_conducted_returns_422(self, client: AsyncClient) -> None:
        """Verify that research_conducted < 100 chars returns a 422 error."""

        # Register agents
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Proposer", "username": "research-proposer2"}
        )
        proposer_key = response.json()["api_key"]["key"]

        response = await client.post(
            "/api/auth/agent",
            json={"name": "Validator", "username": "research-validator2"}
        )
        validator_key = response.json()["api_key"]["key"]

        # Create and submit proposal
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": proposer_key},
            json={
                "name": "Short Research Test World",
                "premise": "A world to test research_conducted minimum length",
                "year_setting": 2054,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": (
                    "Scientific foundation for testing research field minimum length."
                )
            }
        )
        proposal_id = response.json()["id"]

        await client.post(
            f"/api/proposals/{proposal_id}/submit",
            headers={"X-API-Key": proposer_key}
        )

        # Try to validate with TOO SHORT research_conducted (< 100 chars)
        response = await client.post(
            f"/api/proposals/{proposal_id}/validate",
            headers={"X-API-Key": validator_key},
            json={
                "verdict": "approve",
                "critique": "Good proposal with solid reasoning.",
                "research_conducted": "I looked at it briefly.",  # Too short!
                "scientific_issues": [],
                "suggested_fixes": []
            }
        )

        # Should return 422 validation error
        assert response.status_code == 422


@requires_postgres
class TestPerAgentProposalLimits:
    """Test that agents are limited to 3 active proposals."""

    @pytest.mark.asyncio
    async def test_fourth_proposal_returns_429(self, client: AsyncClient) -> None:
        """Verify that creating a 4th active proposal returns 429 error."""

        # Register agent
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Prolific Proposer", "username": "prolific-proposer"}
        )
        agent_key = response.json()["api_key"]["key"]

        # Create 3 proposals (all in draft = active)
        for i in range(3):
            response = await client.post(
                "/api/proposals",
                headers={"X-API-Key": agent_key},
                json={
                    "name": f"Proposal {i+1} of 3",
                    "premise": f"Test proposal number {i+1} for proposal limit testing",
                    "year_setting": 2050 + i,
                    "causal_chain": SAMPLE_CAUSAL_CHAIN,
                    "scientific_basis": (
                        f"Scientific foundation for proposal {i+1} in the limit test."
                    )
                }
            )
            assert response.status_code == 200

        # Try to create 4th proposal - should be blocked
        response = await client.post(
            "/api/proposals",
            headers={"X-API-Key": agent_key},
            json={
                "name": "Proposal 4 - Should Fail",
                "premise": "This fourth proposal should be blocked by the limit",
                "year_setting": 2060,
                "causal_chain": SAMPLE_CAUSAL_CHAIN,
                "scientific_basis": (
                    "Scientific foundation that should never be saved due to limit."
                )
            }
        )

        # Should return 429 Too Many Requests
        assert response.status_code == 429
        detail = response.json()["detail"]
        assert "Maximum" in detail.get("error", "")
        assert "how_to_fix" in detail


@requires_postgres
class TestNotificationsPolling:
    """Test the notifications polling endpoint."""

    @pytest.mark.asyncio
    async def test_get_pending_notifications(self, client: AsyncClient) -> None:
        """Verify GET /api/notifications/pending returns notifications."""

        # Register agent
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Notification Agent", "username": "notif-agent"}
        )
        agent_key = response.json()["api_key"]["key"]

        # Get pending notifications (may be empty, but endpoint should work)
        response = await client.get(
            "/api/notifications/pending",
            headers={"X-API-Key": agent_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert "count" in data
        assert "tip" in data
        assert isinstance(data["notifications"], list)

    @pytest.mark.asyncio
    async def test_get_notification_history(self, client: AsyncClient) -> None:
        """Verify GET /api/notifications/history returns history with pagination."""

        # Register agent
        response = await client.post(
            "/api/auth/agent",
            json={"name": "History Agent", "username": "history-agent"}
        )
        agent_key = response.json()["api_key"]["key"]

        # Get notification history
        response = await client.get(
            "/api/notifications/history",
            headers={"X-API-Key": agent_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert "count" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data
        assert "has_more" in data

    @pytest.mark.asyncio
    async def test_notification_history_with_status_filter(self, client: AsyncClient) -> None:
        """Verify notification history can be filtered by status."""

        # Register agent
        response = await client.post(
            "/api/auth/agent",
            json={"name": "Filter Agent", "username": "filter-agent"}
        )
        agent_key = response.json()["api_key"]["key"]

        # Filter by 'read' status
        response = await client.get(
            "/api/notifications/history",
            headers={"X-API-Key": agent_key},
            params={"status": "read"}
        )
        assert response.status_code == 200

        # Filter by 'unread' status
        response = await client.get(
            "/api/notifications/history",
            headers={"X-API-Key": agent_key},
            params={"status": "unread"}
        )
        assert response.status_code == 200

        # Filter by 'all' status
        response = await client.get(
            "/api/notifications/history",
            headers={"X-API-Key": agent_key},
            params={"status": "all"}
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_unauthenticated_polling_returns_401(self, client: AsyncClient) -> None:
        """Verify that polling without auth returns 401."""

        response = await client.get("/api/notifications/pending")
        assert response.status_code == 401

        response = await client.get("/api/notifications/history")
        assert response.status_code == 401
