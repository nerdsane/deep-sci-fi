"""Aspect rules mixin — propose, submit, review aspects."""

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
    def submit_aspect_review_feedback(self):
        """Non-creator submits review feedback for an aspect."""
        validating = [a for a in self.state.aspects.values() if a.status == "validating"]
        if not validating:
            return
        aspect = validating[0]
        validator = self._other_agent(aspect.creator_id)
        if not validator:
            return
        # Skip if this validator already submitted feedback
        if validator.agent_id in aspect.validators:
            return
        data = strat.review_feedback_data()
        resp = self.client.post(
            f"/api/review/aspect/{aspect.aspect_id}/feedback",
            headers=self._headers(validator),
            json=data,
        )
        self._track_response(resp, f"review aspect {aspect.aspect_id}")
        if resp.status_code in (200, 201):
            aspect.validators[validator.agent_id] = "reviewed"

    @rule()
    def revise_aspect(self):
        """Creator revises an aspect that has feedback."""
        validating = [
            a for a in self.state.aspects.values()
            if a.status == "validating"
            and len(a.validators) > 0
        ]
        if not validating:
            return
        aspect = validating[0]
        agent = self.state.agents[aspect.creator_id]
        data = strat.aspect_revise_data()
        resp = self.client.post(
            f"/api/aspects/{aspect.aspect_id}/revise",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp, f"revise aspect {aspect.aspect_id}")
        if resp.status_code == 200:
            aspect.revision_count += 1

    @rule()
    def self_review_aspect(self):
        """Creator tries to review own aspect — must be rejected."""
        validating = [a for a in self.state.aspects.values() if a.status == "validating"]
        if not validating:
            return
        aspect = validating[-1]
        creator = self.state.agents[aspect.creator_id]
        data = strat.review_feedback_data()
        resp = self.client.post(
            f"/api/review/aspect/{aspect.aspect_id}/feedback",
            headers=self._headers(creator),
            json=data,
        )
        self._track_response(resp, f"self-review aspect {aspect.aspect_id}")
        # Self-review should be rejected (400 or 403)
        assert resp.status_code in (400, 403), (
            f"Self-review should return 400/403 but got {resp.status_code}: "
            f"{resp.text[:200]}"
        )
