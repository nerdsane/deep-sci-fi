"""Action rules mixin — confirm importance, escalate to events."""

from hypothesis.stateful import rule

from tests.simulation.state_mirror import EventState
from tests.simulation import strategies as strat


class ActionRulesMixin:
    """Rules for action importance confirmation and escalation."""

    @rule()
    def confirm_importance(self):
        """Different agent confirms importance of a high-importance action."""
        # Find an unconfirmed escalation-eligible action
        for aid, ar in self.state.actions.items():
            if ar.importance >= 0.8 and ar.confirmed_by is None:
                confirmer = self._other_agent(ar.actor_id)
                if not confirmer:
                    continue
                data = strat.confirm_importance_data()
                resp = self.client.post(
                    f"/api/actions/{aid}/confirm-importance",
                    headers=self._headers(confirmer),
                    json=data,
                )
                self._track_response(resp, f"confirm importance {aid}")
                if resp.status_code == 200:
                    ar.confirmed_by = confirmer.agent_id
                return

    @rule()
    def escalate_action(self):
        """Escalate a confirmed action to a world event."""
        for aid, ar in self.state.actions.items():
            if ar.confirmed_by is not None and not ar.escalated:
                agent = self._random_agent()
                # Get dweller's world_id from state
                dweller = self.state.dwellers.get(ar.dweller_id)
                if not dweller:
                    continue
                data = strat.escalate_data()
                resp = self.client.post(
                    f"/api/actions/{aid}/escalate",
                    headers=self._headers(agent),
                    json=data,
                )
                self._track_response(resp, f"escalate action {aid}")
                if resp.status_code == 200:
                    ar.escalated = True
                    body = resp.json()
                    event = body.get("event", {})
                    eid = event.get("id")
                    if eid:
                        self.state.events[eid] = EventState(
                            event_id=eid,
                            world_id=dweller.world_id,
                            creator_id=agent.agent_id,
                            status="pending",
                        )
                return

    @rule()
    def self_confirm_action(self):
        """Actor tries to confirm their own action — must be rejected."""
        for aid, ar in self.state.actions.items():
            if ar.importance >= 0.8 and ar.confirmed_by is None:
                actor = self.state.agents.get(ar.actor_id)
                if not actor:
                    continue
                data = strat.confirm_importance_data()
                resp = self.client.post(
                    f"/api/actions/{aid}/confirm-importance",
                    headers=self._headers(actor),
                    json=data,
                )
                self._track_response(resp, f"self-confirm action {aid}")
                assert resp.status_code == 400, (
                    f"Self-confirmation should return 400 but got "
                    f"{resp.status_code}: {resp.text[:200]}"
                )
                return

    @rule()
    def escalate_unconfirmed_action(self):
        """Escalate an unconfirmed action — must be rejected."""
        for aid, ar in self.state.actions.items():
            if ar.confirmed_by is None and not ar.escalated:
                agent = self._random_agent()
                dweller = self.state.dwellers.get(ar.dweller_id)
                if not dweller:
                    continue
                data = strat.escalate_data()
                resp = self.client.post(
                    f"/api/actions/{aid}/escalate",
                    headers=self._headers(agent),
                    json=data,
                )
                self._track_response(resp, f"escalate unconfirmed action {aid}")
                assert resp.status_code == 400, (
                    f"Unconfirmed escalation should return 400 but got "
                    f"{resp.status_code}: {resp.text[:200]}"
                )
                return


    @rule()
    def submit_action_direct(self):
        """Submit a dweller action via POST /api/actions with idempotency key (PROP-043)."""
        for dweller_id, ds in self.state.dwellers.items():
            if ds.inhabitant is None:
                continue
            agent = self.state.agents.get(ds.inhabitant)
            if not agent:
                continue
            data = strat.action_data()
            data["dweller_id"] = dweller_id
            idempotency_key = f"dst-direct-{strat._next_id()}"
            resp = self.client.post(
                "/api/actions",
                headers={**self._headers(agent), "X-Idempotency-Key": idempotency_key},
                json=data,
            )
            self._track_response(resp, f"submit action direct {dweller_id}")
            if resp.status_code == 201:
                body = resp.json()
                aid = body.get("action", {}).get("id")
                if aid:
                    from tests.simulation.state_mirror import ActionRef
                    self.state.actions[aid] = ActionRef(
                        action_id=aid,
                        dweller_id=dweller_id,
                        actor_id=agent.agent_id,
                        importance=data["importance"],
                    )
            return

    @rule()
    def submit_action_idempotent_replay(self):
        """Same idempotency key submitted twice — second must return same result (PROP-043)."""
        for dweller_id, ds in self.state.dwellers.items():
            if ds.inhabitant is None:
                continue
            agent = self.state.agents.get(ds.inhabitant)
            if not agent:
                continue
            data = strat.action_data()
            data["dweller_id"] = dweller_id
            idempotency_key = f"dst-replay-{strat._next_id()}"
            headers = {**self._headers(agent), "X-Idempotency-Key": idempotency_key}
            resp1 = self.client.post("/api/actions", headers=headers, json=data)
            resp2 = self.client.post("/api/actions", headers=headers, json=data)
            self._track_response(resp1, f"submit action replay first {dweller_id}")
            self._track_response(resp2, f"submit action replay second {dweller_id}")
            if resp1.status_code == 201:
                assert resp2.status_code in (200, 201), (
                    f"Idempotent replay should return 200/201, got {resp2.status_code}"
                )
            return

    @rule()
    def compose_action(self):
        """Buffer a dweller action via POST /api/actions/compose (PROP-043)."""
        for dweller_id, ds in self.state.dwellers.items():
            if ds.inhabitant is None:
                continue
            agent = self.state.agents.get(ds.inhabitant)
            if not agent:
                continue
            data = strat.action_data()
            data["dweller_id"] = dweller_id
            idempotency_key = f"dst-compose-{strat._next_id()}"
            resp = self.client.post(
                "/api/actions/compose",
                headers={**self._headers(agent), "X-Idempotency-Key": idempotency_key},
                json=data,
            )
            self._track_response(resp, f"compose action {dweller_id}")
            assert resp.status_code in (200, 201, 409, 422), (
                f"compose_action: unexpected {resp.status_code}: {resp.text[:200]}"
            )
            return
