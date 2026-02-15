"""Dweller proposal rules mixin — create, submit, review dweller proposals."""

from hypothesis.stateful import rule

from tests.simulation.state_mirror import DwellerProposalState, DwellerState
from tests.simulation import strategies as strat


class DwellerProposalRulesMixin:
    """Rules for dweller proposal lifecycle."""

    @rule()
    def create_dweller_proposal(self):
        """Random agent creates a dweller proposal in a world with regions."""
        world = self._first_world_with_regions()
        if not world:
            return
        agent = self._random_agent()
        region_name = world.regions[0]
        data = strat.dweller_proposal_data(region_name)
        resp = self.client.post(
            f"/api/dweller-proposals/worlds/{world.world_id}",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp, f"create dweller proposal in {world.world_id}")
        if resp.status_code == 200:
            body = resp.json()
            dp_id = body.get("id")
            if dp_id:
                self.state.dweller_proposals[dp_id] = DwellerProposalState(
                    proposal_id=dp_id,
                    world_id=world.world_id,
                    creator_id=agent.agent_id,
                    status="draft",
                )

    @rule()
    def submit_dweller_proposal(self):
        """Submit a draft dweller proposal for validation."""
        drafts = [dp for dp in self.state.dweller_proposals.values()
                  if dp.status == "draft"]
        if not drafts:
            return
        dp = drafts[0]
        agent = self.state.agents[dp.creator_id]
        resp = self.client.post(
            f"/api/dweller-proposals/{dp.proposal_id}/submit",
            headers=self._headers(agent),
        )
        self._track_response(resp, f"submit dweller proposal {dp.proposal_id}")
        if resp.status_code == 200:
            dp.status = "validating"

    @rule()
    def submit_dweller_proposal_review_feedback(self):
        """Non-creator submits review feedback for a dweller proposal."""
        validating = [dp for dp in self.state.dweller_proposals.values()
                      if dp.status == "validating"]
        if not validating:
            return
        dp = validating[0]
        # Find a validator who hasn't submitted feedback yet and isn't the creator
        for agent_id in self._agent_keys:
            if agent_id != dp.creator_id and agent_id not in dp.validators:
                agent = self.state.agents[agent_id]
                data = strat.review_feedback_data()
                resp = self.client.post(
                    f"/api/review/dweller_proposal/{dp.proposal_id}/feedback",
                    headers=self._headers(agent),
                    json=data,
                )
                self._track_response(resp, f"review dweller proposal {dp.proposal_id}")
                if resp.status_code in (200, 201):
                    dp.validators[agent_id] = "reviewed"
                return

    @rule()
    def revise_dweller_proposal(self):
        """Creator revises a dweller proposal that has feedback."""
        validating = [
            dp for dp in self.state.dweller_proposals.values()
            if dp.status == "validating"
            and len(dp.validators) > 0
        ]
        if not validating:
            return
        dp = validating[0]
        agent = self.state.agents[dp.creator_id]
        data = strat.dweller_proposal_revise_data()
        resp = self.client.post(
            f"/api/dweller-proposals/{dp.proposal_id}/revise",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp, f"revise dweller proposal {dp.proposal_id}")
        if resp.status_code == 200:
            dp.revision_count += 1
