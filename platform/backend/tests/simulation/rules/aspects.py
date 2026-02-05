"""Aspect rules mixin — propose, submit, validate aspects."""

from hypothesis.stateful import rule

from tests.simulation.state_mirror import AspectState
from tests.simulation import strategies as strat


class AspectRulesMixin:
    """Rules for aspect lifecycle."""

    @rule()
    def create_aspect(self):
        """Random agent proposes an aspect for a world."""
        if not self.state.worlds:
            return
        world_id = list(self.state.worlds.keys())[0]
        agent = self._random_agent()
        data = strat.aspect_data(world_id=world_id)
        resp = self.client.post(
            f"/api/aspects/worlds/{world_id}/aspects",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp, f"create aspect in {world_id}")
        if resp.status_code == 200:
            body = resp.json()
            aspect = body.get("aspect", {})
            aid = aspect.get("id")
            if aid:
                self.state.aspects[aid] = AspectState(
                    aspect_id=aid,
                    world_id=world_id,
                    creator_id=agent.agent_id,
                    status="draft",
                    aspect_type=data["aspect_type"],
                )

    @rule()
    def submit_aspect(self):
        """Submit a draft aspect for validation."""
        drafts = [a for a in self.state.aspects.values() if a.status == "draft"]
        if not drafts:
            return
        aspect = drafts[0]
        agent = self.state.agents[aspect.creator_id]
        resp = self.client.post(
            f"/api/aspects/{aspect.aspect_id}/submit?force=true",
            headers=self._headers(agent),
        )
        self._track_response(resp, f"submit aspect {aspect.aspect_id}")
        if resp.status_code == 200:
            aspect.status = "validating"

    @rule()
    def validate_aspect(self):
        """Non-creator validates an aspect."""
        validating = [a for a in self.state.aspects.values() if a.status == "validating"]
        if not validating:
            return
        aspect = validating[0]
        validator = self._other_agent(aspect.creator_id)
        if not validator:
            return
        data = strat.aspect_validation_data("approve")
        resp = self.client.post(
            f"/api/aspects/{aspect.aspect_id}/validate",
            headers=self._headers(validator),
            json=data,
        )
        self._track_response(resp, f"validate aspect {aspect.aspect_id}")
        if resp.status_code == 200:
            body = resp.json()
            new_status = body.get("aspect_status")
            if new_status:
                aspect.status = new_status
