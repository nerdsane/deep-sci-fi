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
