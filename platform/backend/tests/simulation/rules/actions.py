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
