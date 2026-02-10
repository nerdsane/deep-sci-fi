"""Event rules mixin — propose, approve, reject world events."""

from hypothesis.stateful import rule

from tests.simulation.state_mirror import EventState
from tests.simulation import strategies as strat


class EventRulesMixin:
    """Rules for world event lifecycle."""

    @rule()
    def propose_event(self):
        """Random agent proposes a world event."""
        if not self.state.worlds:
            return
        world_id = list(self.state.worlds.keys())[0]
        agent = self._random_agent()
        data = strat.event_data(world_id=world_id)
        resp = self.client.post(
            f"/api/events/worlds/{world_id}/events",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp, f"propose event in {world_id}")
        if resp.status_code == 200:
            body = resp.json()
            event = body.get("event", {})
            eid = event.get("id")
            if eid:
                self.state.events[eid] = EventState(
                    event_id=eid,
                    world_id=world_id,
                    creator_id=agent.agent_id,
                    status="pending",
                )

    @rule()
    def approve_event(self):
        """Non-proposer approves a pending event."""
        pending = [e for e in self.state.events.values() if e.status == "pending"]
        if not pending:
            return
        event = pending[0]
        approver = self._other_agent(event.creator_id)
        if not approver:
            return
        data = strat.event_approve_data()
        resp = self.client.post(
            f"/api/events/{event.event_id}/approve",
            headers=self._headers(approver),
            json=data,
        )
        self._track_response(resp, f"approve event {event.event_id}")
        if resp.status_code == 200:
            event.status = "approved"

    @rule()
    def reject_event(self):
        """Non-proposer rejects a pending event."""
        pending = [e for e in self.state.events.values() if e.status == "pending"]
        if not pending:
            return
        event = pending[0]
        rejector = self._other_agent(event.creator_id)
        if not rejector:
            return
        data = strat.event_reject_data()
        resp = self.client.post(
            f"/api/events/{event.event_id}/reject",
            headers=self._headers(rejector),
            json=data,
        )
        self._track_response(resp, f"reject event {event.event_id}")
        if resp.status_code == 200:
            event.status = "rejected"
