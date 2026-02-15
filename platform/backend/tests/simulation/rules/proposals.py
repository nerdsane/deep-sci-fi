"""Proposal rules mixin — create, submit, review proposals."""

from hypothesis.stateful import rule

from tests.simulation.state_mirror import ProposalState, WorldState
from tests.simulation import strategies as strat


class ProposalRulesMixin:
    """Rules for world proposal lifecycle."""

    @rule()
    def create_proposal(self):
        """Random agent creates a proposal."""
        agent = self._random_agent()
        data = strat.proposal_data()
        resp = self.client.post(
            "/api/proposals",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp, "create proposal")
        if resp.status_code == 200:
            body = resp.json()
            pid = body["id"]
            self.state.proposals[pid] = ProposalState(
                proposal_id=pid,
                creator_id=agent.agent_id,
                status="draft",
            )

    @rule()
    def submit_proposal(self):
        """Submit a draft proposal for validation."""
        drafts = [p for p in self.state.proposals.values() if p.status == "draft"]
        if not drafts:
            return
        proposal = drafts[0]
        agent = self.state.agents[proposal.creator_id]
        resp = self.client.post(
            f"/api/proposals/{proposal.proposal_id}/submit?force=true",
            headers=self._headers(agent),
        )
        self._track_response(resp, f"submit proposal {proposal.proposal_id}")
        if resp.status_code == 200:
            proposal.status = "validating"

    @rule()
    def submit_review_feedback(self):
        """Non-creator submits review feedback for a proposal."""
        validating = [p for p in self.state.proposals.values() if p.status == "validating"]
        if not validating:
            return
        proposal = validating[0]
        for agent_id in self._agent_keys:
            if agent_id != proposal.creator_id and agent_id not in proposal.validators:
                agent = self.state.agents[agent_id]
                data = strat.review_feedback_data()
                resp = self.client.post(
                    f"/api/review/proposal/{proposal.proposal_id}/feedback",
                    headers=self._headers(agent),
                    json=data,
                )
                self._track_response(resp, f"review proposal {proposal.proposal_id}")
                if resp.status_code in (200, 201):
                    proposal.validators[agent_id] = "reviewed"
                return

    @rule()
    def revise_proposal(self):
        """Creator revises a proposal that has feedback."""
        validating = [
            p for p in self.state.proposals.values()
            if p.status == "validating"
            and len(p.validators) > 0
        ]
        if not validating:
            return
        proposal = validating[0]
        agent = self.state.agents[proposal.creator_id]
        data = strat.proposal_revise_data()
        resp = self.client.post(
            f"/api/proposals/{proposal.proposal_id}/revise",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp, f"revise proposal {proposal.proposal_id}")
        if resp.status_code == 200:
            proposal.revision_count += 1

    @rule()
    def self_review_proposal(self):
        """Creator tries to review own proposal — must be rejected."""
        validating = [p for p in self.state.proposals.values() if p.status == "validating"]
        if not validating:
            return
        proposal = validating[-1]
        creator = self.state.agents[proposal.creator_id]
        data = strat.review_feedback_data()
        resp = self.client.post(
            f"/api/review/proposal/{proposal.proposal_id}/feedback",
            headers=self._headers(creator),
            json=data,
        )
        self._track_response(resp, f"self-review proposal {proposal.proposal_id}")
        # Self-review should be rejected (400 or 403)
        assert resp.status_code in (400, 403), (
            f"Self-review should return 400/403 but got {resp.status_code}: "
            f"{resp.text[:200]}"
        )
