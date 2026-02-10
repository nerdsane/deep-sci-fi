"""Auth rules mixin — update callback, update model."""

from hypothesis.stateful import rule

from tests.simulation import strategies as strat


class AuthRulesMixin:
    """Rules for agent auth profile updates."""

    @rule()
    def update_callback(self):
        """Agent updates their callback webhook URL."""
        agent = self._random_agent()
        data = strat.callback_update_data()
        resp = self.client.patch(
            "/api/auth/me/callback",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp, "update callback")

    @rule()
    def update_model(self):
        """Agent updates their model identifier."""
        agent = self._random_agent()
        data = strat.model_update_data()
        resp = self.client.patch(
            "/api/auth/me/model",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp, "update model")
