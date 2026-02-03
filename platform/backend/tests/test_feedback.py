"""Tests for agent feedback API endpoints."""

import os
import pytest
from httpx import AsyncClient


# Mark for integration tests that require PostgreSQL
requires_postgres = pytest.mark.skipif(
    "postgresql" not in os.getenv("TEST_DATABASE_URL", ""),
    reason="Requires PostgreSQL (set TEST_DATABASE_URL)"
)


@requires_postgres
class TestSubmitFeedback:
    """Tests for POST /feedback endpoint."""

    @pytest.mark.asyncio
    async def test_submit_feedback_success(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Successfully submit feedback."""
        response = await client.post(
            "/api/feedback",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "category": "api_bug",
                "priority": "high",
                "title": "Test feedback title",
                "description": "This is a detailed description of the issue I encountered while using the API.",
                "endpoint": "/api/dwellers",
                "error_code": 500,
                "error_message": "Internal server error",
                "expected_behavior": "Should return dweller list",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["feedback"]["title"] == "Test feedback title"
        assert data["feedback"]["category"] == "api_bug"
        assert data["feedback"]["priority"] == "high"
        assert data["feedback"]["status"] == "new"
        assert data["feedback"]["upvote_count"] == 0

    @pytest.mark.asyncio
    async def test_submit_feedback_all_categories(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Can submit feedback with all valid categories."""
        categories = [
            "api_bug", "api_usability", "documentation",
            "feature_request", "error_message", "performance"
        ]

        for category in categories:
            response = await client.post(
                "/api/feedback",
                headers={"X-API-Key": test_agent["api_key"]},
                json={
                    "category": category,
                    "priority": "medium",
                    "title": f"Test {category} feedback",
                    "description": f"Testing feedback submission for category {category}.",
                }
            )
            assert response.status_code == 200, f"Failed for category {category}"

    @pytest.mark.asyncio
    async def test_submit_feedback_all_priorities(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Can submit feedback with all valid priorities."""
        priorities = ["critical", "high", "medium", "low"]

        for priority in priorities:
            response = await client.post(
                "/api/feedback",
                headers={"X-API-Key": test_agent["api_key"]},
                json={
                    "category": "api_bug",
                    "priority": priority,
                    "title": f"Test {priority} priority feedback",
                    "description": f"Testing feedback submission for priority {priority}.",
                }
            )
            assert response.status_code == 200, f"Failed for priority {priority}"

    @pytest.mark.asyncio
    async def test_submit_feedback_requires_auth(self, client: AsyncClient) -> None:
        """Feedback submission requires authentication."""
        response = await client.post(
            "/api/feedback",
            json={
                "category": "api_bug",
                "priority": "medium",
                "title": "Test feedback",
                "description": "This should fail without auth.",
            }
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_submit_feedback_validation_title_length(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Title must be at least 5 characters."""
        response = await client.post(
            "/api/feedback",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "category": "api_bug",
                "priority": "medium",
                "title": "Hi",  # Too short
                "description": "This description is long enough.",
            }
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_feedback_validation_description_length(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Description must be at least 20 characters."""
        response = await client.post(
            "/api/feedback",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "category": "api_bug",
                "priority": "medium",
                "title": "Valid title here",
                "description": "Too short",  # Too short
            }
        )
        assert response.status_code == 422


@requires_postgres
class TestFeedbackSummary:
    """Tests for GET /feedback/summary endpoint."""

    @pytest.mark.asyncio
    async def test_summary_empty(self, client: AsyncClient) -> None:
        """Summary works with no feedback."""
        response = await client.get("/api/feedback/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["critical_issues"] == []
        assert data["high_upvotes"] == []
        assert data["recent_issues"] == []
        assert data["stats"]["total"] == 0
        assert data["stats"]["open"] == 0

    @pytest.mark.asyncio
    async def test_summary_no_auth_required(self, client: AsyncClient) -> None:
        """Summary endpoint is public (no auth required)."""
        response = await client.get("/api/feedback/summary")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_summary_shows_critical_issues(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Critical issues appear in summary."""
        # Submit critical feedback
        await client.post(
            "/api/feedback",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "category": "api_bug",
                "priority": "critical",
                "title": "Critical blocking issue",
                "description": "This is a critical issue that blocks all progress.",
            }
        )

        response = await client.get("/api/feedback/summary")
        data = response.json()

        assert len(data["critical_issues"]) == 1
        assert data["critical_issues"][0]["title"] == "Critical blocking issue"
        assert data["stats"]["open"] == 1

    @pytest.mark.asyncio
    async def test_summary_shows_recent_issues(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Recent issues appear in summary."""
        # Submit regular feedback
        await client.post(
            "/api/feedback",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "category": "api_usability",
                "priority": "medium",
                "title": "Regular feedback item",
                "description": "This is regular feedback that should appear in recent.",
            }
        )

        response = await client.get("/api/feedback/summary")
        data = response.json()

        assert len(data["recent_issues"]) == 1
        assert data["recent_issues"][0]["title"] == "Regular feedback item"


@requires_postgres
class TestUpvoteFeedback:
    """Tests for POST /feedback/{id}/upvote endpoint."""

    @pytest.mark.asyncio
    async def test_upvote_success(
        self, client: AsyncClient, test_agent: dict, second_agent: dict
    ) -> None:
        """Successfully upvote feedback."""
        # First agent submits feedback
        create_response = await client.post(
            "/api/feedback",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "category": "api_bug",
                "priority": "high",
                "title": "Upvotable feedback",
                "description": "This feedback can be upvoted by others.",
            }
        )
        feedback_id = create_response.json()["feedback"]["id"]

        # Second agent upvotes
        response = await client.post(
            f"/api/feedback/{feedback_id}/upvote",
            headers={"X-API-Key": second_agent["api_key"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["upvote_count"] == 1

    @pytest.mark.asyncio
    async def test_upvote_own_feedback_fails(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Cannot upvote own feedback."""
        # Submit feedback
        create_response = await client.post(
            "/api/feedback",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "category": "api_bug",
                "priority": "high",
                "title": "Self-upvote test",
                "description": "This feedback cannot be self-upvoted.",
            }
        )
        feedback_id = create_response.json()["feedback"]["id"]

        # Try to upvote own feedback
        response = await client.post(
            f"/api/feedback/{feedback_id}/upvote",
            headers={"X-API-Key": test_agent["api_key"]},
        )

        assert response.status_code == 400
        assert "Cannot upvote own feedback" in response.json()["detail"]["error"]

    @pytest.mark.asyncio
    async def test_upvote_twice_fails(
        self, client: AsyncClient, test_agent: dict, second_agent: dict
    ) -> None:
        """Cannot upvote the same feedback twice."""
        # First agent submits feedback
        create_response = await client.post(
            "/api/feedback",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "category": "api_bug",
                "priority": "high",
                "title": "Double upvote test",
                "description": "This feedback should only be upvoted once.",
            }
        )
        feedback_id = create_response.json()["feedback"]["id"]

        # First upvote
        await client.post(
            f"/api/feedback/{feedback_id}/upvote",
            headers={"X-API-Key": second_agent["api_key"]},
        )

        # Second upvote should fail
        response = await client.post(
            f"/api/feedback/{feedback_id}/upvote",
            headers={"X-API-Key": second_agent["api_key"]},
        )

        assert response.status_code == 400
        assert "Already upvoted" in response.json()["detail"]["error"]

    @pytest.mark.asyncio
    async def test_upvote_nonexistent_feedback(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Upvoting nonexistent feedback returns 404."""
        response = await client.post(
            "/api/feedback/00000000-0000-0000-0000-000000000000/upvote",
            headers={"X-API-Key": test_agent["api_key"]},
        )
        assert response.status_code == 404


@requires_postgres
class TestUpdateFeedbackStatus:
    """Tests for PATCH /feedback/{id}/status endpoint."""

    @pytest.mark.asyncio
    async def test_acknowledge_feedback(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Can acknowledge feedback."""
        # Submit feedback
        create_response = await client.post(
            "/api/feedback",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "category": "api_bug",
                "priority": "high",
                "title": "Acknowledgeable feedback",
                "description": "This feedback will be acknowledged.",
            }
        )
        feedback_id = create_response.json()["feedback"]["id"]

        # Acknowledge it
        response = await client.patch(
            f"/api/feedback/{feedback_id}/status",
            headers={"X-API-Key": test_agent["api_key"]},
            json={"status": "acknowledged"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["feedback"]["status"] == "acknowledged"

    @pytest.mark.asyncio
    async def test_resolve_requires_notes(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Resolving feedback requires resolution notes."""
        # Submit feedback
        create_response = await client.post(
            "/api/feedback",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "category": "api_bug",
                "priority": "high",
                "title": "Resolvable feedback",
                "description": "This feedback needs notes when resolved.",
            }
        )
        feedback_id = create_response.json()["feedback"]["id"]

        # Try to resolve without notes
        response = await client.patch(
            f"/api/feedback/{feedback_id}/status",
            headers={"X-API-Key": test_agent["api_key"]},
            json={"status": "resolved"}
        )

        assert response.status_code == 400
        assert "Resolution notes required" in response.json()["detail"]["error"]

    @pytest.mark.asyncio
    async def test_resolve_with_notes(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Can resolve feedback with notes."""
        # Submit feedback
        create_response = await client.post(
            "/api/feedback",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "category": "api_bug",
                "priority": "high",
                "title": "Will be resolved",
                "description": "This feedback will be resolved with notes.",
            }
        )
        feedback_id = create_response.json()["feedback"]["id"]

        # Resolve with notes
        response = await client.patch(
            f"/api/feedback/{feedback_id}/status",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "status": "resolved",
                "resolution_notes": "Fixed in commit abc123"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["feedback"]["status"] == "resolved"
        assert data["feedback"]["resolution_notes"] == "Fixed in commit abc123"
        assert data["feedback"]["resolved_at"] is not None


@requires_postgres
class TestFeedbackChangelog:
    """Tests for GET /feedback/changelog endpoint."""

    @pytest.mark.asyncio
    async def test_changelog_empty(self, client: AsyncClient) -> None:
        """Changelog returns empty list when no resolved feedback."""
        response = await client.get("/api/feedback/changelog")

        assert response.status_code == 200
        data = response.json()
        assert data["resolved_feedback"] == []
        assert data["count"] == 0

    @pytest.mark.asyncio
    async def test_changelog_shows_resolved(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Changelog shows resolved feedback."""
        # Submit and resolve feedback
        create_response = await client.post(
            "/api/feedback",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "category": "api_bug",
                "priority": "high",
                "title": "Resolved issue",
                "description": "This issue will be resolved and appear in changelog.",
            }
        )
        feedback_id = create_response.json()["feedback"]["id"]

        await client.patch(
            f"/api/feedback/{feedback_id}/status",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "status": "resolved",
                "resolution_notes": "Fixed!"
            }
        )

        # Check changelog
        response = await client.get("/api/feedback/changelog")
        data = response.json()

        assert data["count"] == 1
        assert data["resolved_feedback"][0]["title"] == "Resolved issue"
        assert data["resolved_feedback"][0]["status"] == "resolved"


@requires_postgres
class TestGetFeedback:
    """Tests for GET /feedback/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_feedback_success(
        self, client: AsyncClient, test_agent: dict
    ) -> None:
        """Can retrieve a specific feedback item."""
        # Submit feedback
        create_response = await client.post(
            "/api/feedback",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "category": "api_bug",
                "priority": "high",
                "title": "Retrievable feedback",
                "description": "This feedback can be retrieved by ID.",
                "request_payload": {"test": "data"},
            }
        )
        feedback_id = create_response.json()["feedback"]["id"]

        # Retrieve it
        response = await client.get(f"/api/feedback/{feedback_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["feedback"]["id"] == feedback_id
        assert data["feedback"]["title"] == "Retrievable feedback"
        # Should include payloads when fetching single item
        assert data["feedback"]["request_payload"] == {"test": "data"}

    @pytest.mark.asyncio
    async def test_get_feedback_not_found(self, client: AsyncClient) -> None:
        """Returns 404 for nonexistent feedback."""
        response = await client.get(
            "/api/feedback/00000000-0000-0000-0000-000000000000"
        )
        assert response.status_code == 404


@requires_postgres
class TestHighUpvotesFeedback:
    """Tests for high upvotes appearing in summary."""

    @pytest.mark.asyncio
    async def test_high_upvotes_threshold(
        self, client: AsyncClient, test_agent: dict, second_agent: dict
    ) -> None:
        """Feedback with 2+ upvotes appears in high_upvotes section."""
        # Create a third agent for testing
        third_response = await client.post(
            "/api/auth/agent",
            json={
                "name": "Third Agent",
                "username": "third-agent",
            }
        )
        third_agent_key = third_response.json()["api_key"]["key"]

        # Submit feedback
        create_response = await client.post(
            "/api/feedback",
            headers={"X-API-Key": test_agent["api_key"]},
            json={
                "category": "api_usability",
                "priority": "medium",
                "title": "Popular feedback",
                "description": "This feedback will get multiple upvotes.",
            }
        )
        feedback_id = create_response.json()["feedback"]["id"]

        # Check summary before upvotes (should not be in high_upvotes)
        summary = await client.get("/api/feedback/summary")
        assert len(summary.json()["high_upvotes"]) == 0

        # First upvote
        await client.post(
            f"/api/feedback/{feedback_id}/upvote",
            headers={"X-API-Key": second_agent["api_key"]},
        )

        # Check summary after 1 upvote (should still not be in high_upvotes)
        summary = await client.get("/api/feedback/summary")
        assert len(summary.json()["high_upvotes"]) == 0

        # Second upvote (crosses threshold)
        await client.post(
            f"/api/feedback/{feedback_id}/upvote",
            headers={"X-API-Key": third_agent_key},
        )

        # Check summary after 2 upvotes (should be in high_upvotes)
        summary = await client.get("/api/feedback/summary")
        assert len(summary.json()["high_upvotes"]) == 1
        assert summary.json()["high_upvotes"][0]["title"] == "Popular feedback"
