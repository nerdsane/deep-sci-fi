"""Guidance rules mixin — story writing guidance publication (PROP-042)."""

from hypothesis.stateful import rule

from tests.simulation import strategies as strat


class GuidanceRulesMixin:
    """Rules covering POST /api/admin/guidance/story-writing."""

    @rule()
    def publish_story_guidance(self):
        """Admin publishes a new story writing guidance version."""
        data = {
            "version": f"dst-v-{strat._next_id()}",
            "rules": [
                {"id": "length", "severity": "strong", "text": "Target 800-1500 words"},
                {"id": "meta", "severity": "strong", "text": "No meta-commentary"},
                {"id": "opening", "severity": "medium", "text": "Open with sensory scene"},
            ],
            "examples": [
                {
                    "title": "Good Opening",
                    "excerpt": "The coolant mist drifted over the glass atrium.",
                    "why": "Sensory immersion before exposition",
                }
            ],
        }
        resp = self.client.post(
            "/api/admin/guidance/story-writing",
            headers=self._admin_headers(),
            json=data,
        )
        self._track_response(resp, "publish story guidance")
        assert resp.status_code in (200, 422), (
            f"publish_story_guidance: expected 200 or 422, got "
            f"{resp.status_code}: {resp.text[:200]}"
        )

    @rule()
    def publish_guidance_missing_version(self):
        """Admin publishes guidance without version — must return 422."""
        resp = self.client.post(
            "/api/admin/guidance/story-writing",
            headers=self._admin_headers(),
            json={"rules": []},
        )
        self._track_response(resp, "publish guidance missing version")
        assert resp.status_code == 422, (
            f"Missing version should be 422, got {resp.status_code}: {resp.text[:200]}"
        )

    @rule()
    def publish_guidance_unauthorized(self):
        """Non-admin tries to publish guidance — must be rejected."""
        if not self.state.agents:
            return
        agent = next(iter(self.state.agents.values()))
        data = {
            "version": f"dst-unauth-{strat._next_id()}",
            "rules": [],
        }
        resp = self.client.post(
            "/api/admin/guidance/story-writing",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp, "publish guidance unauthorized")
        assert resp.status_code in (401, 403), (
            f"Non-admin guidance publish should be 401/403, got "
            f"{resp.status_code}: {resp.text[:200]}"
        )
