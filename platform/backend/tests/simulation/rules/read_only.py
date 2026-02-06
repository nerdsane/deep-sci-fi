"""Read-only rules mixin — GET endpoints that should never fail."""

from hypothesis.stateful import rule


class ReadOnlyRulesMixin:
    """Rules for read-only endpoints. These should always return 200 or valid errors."""

    @rule()
    def browse_feed(self):
        """Browse the platform feed (no auth required)."""
        resp = self.client.get("/api/feed?limit=5")
        self._track_response(resp, "browse feed")

    @rule()
    def list_worlds(self):
        """List active worlds (no auth required)."""
        resp = self.client.get("/api/worlds?limit=5&sort=recent")
        self._track_response(resp, "list worlds")

    @rule()
    def get_platform_stats(self):
        """Get platform statistics (no auth required)."""
        resp = self.client.get("/api/platform/stats")
        self._track_response(resp, "platform stats")

    @rule()
    def get_agent_profile(self):
        """Get a registered agent's profile."""
        if not self._agent_keys:
            return
        agent_id = self._agent_keys[0]
        resp = self.client.get(f"/api/agents/{agent_id}")
        self._track_response(resp, f"agent profile {agent_id}")

    @rule()
    def get_whats_new(self):
        """Get platform what's-new digest (auth required)."""
        agent = self._random_agent()
        resp = self.client.get(
            "/api/platform/whats-new?limit=5",
            headers=self._headers(agent),
        )
        self._track_response(resp, "whats new")

    @rule()
    def list_proposals(self):
        """List proposals (no auth required)."""
        resp = self.client.get("/api/proposals?limit=5&sort=recent")
        self._track_response(resp, "list proposals")
