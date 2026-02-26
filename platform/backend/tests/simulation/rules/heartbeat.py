"""Heartbeat rules mixin — send heartbeat, check activity status."""

from hypothesis.stateful import rule


class HeartbeatRulesMixin:
    """Rules for heartbeat / activity lifecycle."""

    @rule()
    def send_heartbeat(self):
        """Random agent sends heartbeat to stay active."""
        agent = self._random_agent()
        resp = self.client.get(
            "/api/heartbeat",
            headers=self._headers(agent),
        )
        self._track_response(resp, f"heartbeat {agent.agent_id}")
        if resp.status_code == 200:
            from utils.clock import now
            agent.last_heartbeat = now()

    @rule()
    def post_heartbeat(self):
        """Random agent posts heartbeat (POST variant)."""
        agent = self._random_agent()
        resp = self.client.post(
            "/api/heartbeat",
            headers=self._headers(agent),
        )
        self._track_response(resp, f"post heartbeat {agent.agent_id}")

    @rule()
    def set_maintenance_mode(self):
        """Agent declares planned maintenance absence."""
        agent = self._random_agent()
        from utils.clock import now as utc_now
        from datetime import timedelta
        resp = self.client.post(
            "/api/heartbeat/maintenance",
            headers=self._headers(agent),
            json={
                "maintenance_until": (utc_now() + timedelta(hours=6)).isoformat(),
                "reason": "planned_pause",
            },
        )
        self._track_response(resp, "set maintenance mode")
