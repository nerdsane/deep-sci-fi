"""
Tests for the critical review system (feedback-first validation).

Tests cover:
- Feedback submission flow
- Response and resolution cycle
- Blind mode behavior
- Graduation gate logic
"""
import pytest
from httpx import AsyncClient
from uuid import UUID, uuid4

from db.models import (
    Proposal,
    ProposalStatus,
    ReviewSystemType,
)


class TestFeedbackSubmission:
    """Test feedback submission flow."""

    @pytest.mark.asyncio
    async def test_submit_review_creates_feedback(
        self, client: AsyncClient, db_session, test_agent, second_agent
    ):
        """Submitting a review creates ReviewFeedback and FeedbackItems."""
        # Create a proposal for review
        proposal = Proposal(
            id=uuid4(),
            agent_id=UUID(test_agent["user"]["id"]),
            premise="Test future premise",
            year_setting=2100,
            causal_chain=[{"year": 2050, "event": "AI revolution", "reasoning": "Moore's Law"}],
            scientific_basis="Computational complexity theory",
            status=ProposalStatus.VALIDATING,
            review_system=ReviewSystemType.CRITICAL_REVIEW,
        )
        db_session.add(proposal)
        await db_session.commit()

        # Submit feedback as different agent
        response = await client.post(
            f"/api/review/proposal/{proposal.id}/feedback",
            json={
                "feedback_items": [
                    {
                        "category": "scientific_issue",
                        "description": "Moore's Law doesn't directly lead to AI revolution - missing intermediate steps",
                        "severity": "important",
                    },
                    {
                        "category": "other",
                        "description": "Premise could be more specific about which aspect of AI",
                        "severity": "minor",
                    },
                ]
            },
            headers={"X-API-Key": second_agent["api_key"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert "review_id" in data
        assert len(data["feedback_items"]) == 2
        assert data["feedback_items"][0]["status"] == "open"

    @pytest.mark.asyncio
    async def test_cannot_submit_duplicate_review(
        self, client: AsyncClient, db_session, test_agent, second_agent
    ):
        """Cannot submit more than one review per reviewer per content."""
        # Create proposal
        proposal = Proposal(
            id=uuid4(),
            agent_id=UUID(test_agent["user"]["id"]),
            premise="Test premise",
            year_setting=2100,
            causal_chain=[],
            scientific_basis="Test basis",
            status=ProposalStatus.VALIDATING,
            review_system=ReviewSystemType.CRITICAL_REVIEW,
        )
        db_session.add(proposal)
        await db_session.commit()

        # Submit first review
        await client.post(
            f"/api/review/proposal/{proposal.id}/feedback",
            json={
                "feedback_items": [
                    {
                        "category": "scientific_issue",
                        "description": "Test issue",
                        "severity": "important",
                    }
                ]
            },
            headers={"X-API-Key": second_agent["api_key"]},
        )

        # Try to submit second review
        response = await client.post(
            f"/api/review/proposal/{proposal.id}/feedback",
            json={
                "feedback_items": [
                    {
                        "category": "other",
                        "description": "Another issue",
                        "severity": "minor",
                    }
                ]
            },
            headers={"X-API-Key": second_agent["api_key"]},
        )

        assert response.status_code == 400
        assert "already submitted a review" in response.json()["detail"]["error"]


class TestBlindMode:
    """Test blind mode - reviewers can't see others' feedback until they submit."""

    @pytest.mark.asyncio
    async def test_cannot_see_feedback_before_submitting(
        self, client: AsyncClient, db_session, test_agent, second_agent
    ):
        """Non-proposer agent cannot see others' reviews until they submit their own."""
        # Create proposal (test_agent is proposer)
        proposal = Proposal(
            id=uuid4(),
            agent_id=UUID(test_agent["user"]["id"]),
            premise="Test premise",
            year_setting=2100,
            causal_chain=[],
            scientific_basis="Test basis",
            status=ProposalStatus.VALIDATING,
            review_system=ReviewSystemType.CRITICAL_REVIEW,
        )
        db_session.add(proposal)
        await db_session.commit()

        # second_agent submits review
        await client.post(
            f"/api/review/proposal/{proposal.id}/feedback",
            json={
                "feedback_items": [
                    {
                        "category": "scientific_issue",
                        "description": "Missing causal link",
                        "severity": "important",
                    }
                ]
            },
            headers={"X-API-Key": second_agent["api_key"]},
        )

        # Register a third agent (non-proposer, non-reviewer)
        third_resp = await client.post(
            "/api/auth/agent",
            json={"name": "Third Agent", "username": "third-agent-blind",
                  "description": "Third agent for blind mode test"},
        )
        third_key = third_resp.json()["api_key"]["key"]

        # Third agent tries to get feedback (hasn't submitted yet)
        response = await client.get(
            f"/api/review/proposal/{proposal.id}/feedback",
            headers={"X-API-Key": third_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["blind_mode"] is True
        assert len(data["reviews"]) == 0
        assert "Submit your review" in data["message"]


class TestFeedbackResponse:
    """Test proposer's response to feedback."""

    @pytest.mark.asyncio
    async def test_respond_to_feedback_item(
        self, client: AsyncClient, db_session, test_agent, second_agent
    ):
        """Proposer can respond to feedback items."""
        # Create proposal and review
        proposal = Proposal(
            id=uuid4(),
            agent_id=UUID(test_agent["user"]["id"]),
            premise="Test premise",
            year_setting=2100,
            causal_chain=[],
            scientific_basis="Test basis",
            status=ProposalStatus.VALIDATING,
            review_system=ReviewSystemType.CRITICAL_REVIEW,
        )
        db_session.add(proposal)
        await db_session.commit()

        # Submit review
        review_resp = await client.post(
            f"/api/review/proposal/{proposal.id}/feedback",
            json={
                "feedback_items": [
                    {
                        "category": "scientific_issue",
                        "description": "Missing intermediate steps in causal chain",
                        "severity": "important",
                    }
                ]
            },
            headers={"X-API-Key": second_agent["api_key"]},
        )
        item_id = review_resp.json()["feedback_items"][0]["id"]

        # Respond to feedback
        response = await client.post(
            f"/api/review/feedback-item/{item_id}/respond",
            json={"response_text": "Added intermediate steps: quantum computing breakthrough (2040), AGI emergence (2055)"},
            headers={"X-API-Key": test_agent["api_key"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["new_status"] == "addressed"
        assert "reviewer must now confirm" in data["message"].lower()


class TestResolution:
    """Test reviewer confirming resolution of feedback."""

    @pytest.mark.asyncio
    async def test_reviewer_can_resolve_own_item(
        self, client: AsyncClient, db_session, test_agent, second_agent
    ):
        """Reviewers can mark their own feedback items as resolved."""
        # Create proposal and review
        proposal = Proposal(
            id=uuid4(),
            agent_id=UUID(test_agent["user"]["id"]),
            premise="Test premise",
            year_setting=2100,
            causal_chain=[],
            scientific_basis="Test basis",
            status=ProposalStatus.VALIDATING,
            review_system=ReviewSystemType.CRITICAL_REVIEW,
        )
        db_session.add(proposal)
        await db_session.commit()

        # Submit review
        review_resp = await client.post(
            f"/api/review/proposal/{proposal.id}/feedback",
            json={
                "feedback_items": [
                    {
                        "category": "scientific_issue",
                        "description": "Missing steps",
                        "severity": "important",
                    }
                ]
            },
            headers={"X-API-Key": second_agent["api_key"]},
        )
        item_id = review_resp.json()["feedback_items"][0]["id"]

        # Proposer responds
        await client.post(
            f"/api/review/feedback-item/{item_id}/respond",
            json={"response_text": "Fixed - added intermediate steps"},
            headers={"X-API-Key": test_agent["api_key"]},
        )

        # Proposer revises (required before resolution)
        await client.post(
            f"/api/proposals/{proposal.id}/revise",
            json={"premise": "Revised test premise with improved scientific rigor and intermediate steps"},
            headers={"X-API-Key": test_agent["api_key"]},
        )

        # Reviewer resolves
        response = await client.post(
            f"/api/review/feedback-item/{item_id}/resolve",
            json={"resolution_note": "Looks good now"},
            headers={"X-API-Key": second_agent["api_key"]},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "resolved"

    @pytest.mark.asyncio
    async def test_non_reviewer_cannot_resolve(
        self, client: AsyncClient, db_session, test_agent, second_agent
    ):
        """Only the original reviewer can resolve their feedback item."""
        # Create proposal and review
        proposal = Proposal(
            id=uuid4(),
            agent_id=UUID(test_agent["user"]["id"]),
            premise="Test premise",
            year_setting=2100,
            causal_chain=[],
            scientific_basis="Test basis",
            status=ProposalStatus.VALIDATING,
            review_system=ReviewSystemType.CRITICAL_REVIEW,
        )
        db_session.add(proposal)
        await db_session.commit()

        # Submit review as second_agent
        review_resp = await client.post(
            f"/api/review/proposal/{proposal.id}/feedback",
            json={
                "feedback_items": [
                    {
                        "category": "scientific_issue",
                        "description": "Missing steps",
                        "severity": "important",
                    }
                ]
            },
            headers={"X-API-Key": second_agent["api_key"]},
        )
        item_id = review_resp.json()["feedback_items"][0]["id"]

        # test_agent (the proposer, not the reviewer) tries to resolve
        response = await client.post(
            f"/api/review/feedback-item/{item_id}/resolve",
            json={},
            headers={"X-API-Key": test_agent["api_key"]},
        )

        assert response.status_code == 403
        assert "Only the original reviewer" in response.json()["detail"]["error"]


class TestGraduationGate:
    """Test graduation gate logic."""

    @pytest.mark.asyncio
    async def test_cannot_graduate_without_min_reviewers(
        self, client: AsyncClient, db_session, test_agent, second_agent
    ):
        """Need at least 2 reviewers to graduate."""
        # Create proposal
        proposal = Proposal(
            id=uuid4(),
            agent_id=UUID(test_agent["user"]["id"]),
            premise="Test premise",
            year_setting=2100,
            causal_chain=[],
            scientific_basis="Test basis",
            status=ProposalStatus.VALIDATING,
            review_system=ReviewSystemType.CRITICAL_REVIEW,
        )
        db_session.add(proposal)
        await db_session.commit()

        # Submit one review (all resolved)
        review_resp = await client.post(
            f"/api/review/proposal/{proposal.id}/feedback",
            json={
                "feedback_items": [
                    {
                        "category": "scientific_issue",
                        "description": "Test issue",
                        "severity": "important",
                    }
                ]
            },
            headers={"X-API-Key": second_agent["api_key"]},
        )
        item_id = review_resp.json()["feedback_items"][0]["id"]

        # Respond and resolve
        await client.post(
            f"/api/review/feedback-item/{item_id}/respond",
            json={"response_text": "Fixed the issue as suggested by the reviewer"},
            headers={"X-API-Key": test_agent["api_key"]},
        )
        await client.post(
            f"/api/review/feedback-item/{item_id}/resolve",
            json={},
            headers={"X-API-Key": second_agent["api_key"]},
        )

        # Check graduation status
        response = await client.get(
            f"/api/review/proposal/{proposal.id}/status",
            headers={"X-API-Key": test_agent["api_key"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["can_graduate"] is False
        assert data["reviewer_count"] == 1
        assert data["min_reviewers"] == 2
