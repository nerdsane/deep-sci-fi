"""Proposal rules mixin — create, submit, validate proposals."""

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
    def validate_proposal(self):
        """Non-creator, non-duplicate validator validates a proposal."""
        validating = [p for p in self.state.proposals.values() if p.status == "validating"]
        if not validating:
            return
        proposal = validating[0]
        for agent_id in self._agent_keys:
            if agent_id != proposal.creator_id and agent_id not in proposal.validators:
                agent = self.state.agents[agent_id]
                data = strat.validation_data("approve")
                resp = self.client.post(
                    f"/api/proposals/{proposal.proposal_id}/validate",
                    headers=self._headers(agent),
                    json=data,
                )
                self._track_response(resp, f"validate proposal {proposal.proposal_id}")
                if resp.status_code == 200:
                    proposal.validators[agent_id] = "approve"
                    body = resp.json()
                    if body.get("proposal_status"):
                        proposal.status = body["proposal_status"]
                    wc = body.get("world_created")
                    if wc and isinstance(wc, dict):
                        world_id = wc["id"]
                        proposal.status = "approved"
                        self.state.worlds[world_id] = WorldState(
                            world_id=world_id,
                            creator_id=proposal.creator_id,
                            source_proposal_id=proposal.proposal_id,
                        )
                return

    @rule()
    def reject_proposal(self):
        """Non-creator rejects a validating proposal."""
        validating = [p for p in self.state.proposals.values() if p.status == "validating"]
        if not validating:
            return
        proposal = validating[-1]
        for agent_id in self._agent_keys:
            if agent_id != proposal.creator_id and agent_id not in proposal.validators:
                agent = self.state.agents[agent_id]
                data = strat.validation_data("reject")
                resp = self.client.post(
                    f"/api/proposals/{proposal.proposal_id}/validate",
                    headers=self._headers(agent),
                    json=data,
                )
                self._track_response(resp, f"reject proposal {proposal.proposal_id}")
                if resp.status_code == 200:
                    proposal.validators[agent_id] = "reject"
                    body = resp.json()
                    if body.get("proposal_status"):
                        proposal.status = body["proposal_status"]
                return

    @rule()
    def strengthen_proposal(self):
        """Non-creator strengthens a validating proposal."""
        validating = [p for p in self.state.proposals.values() if p.status == "validating"]
        if not validating:
            return
        proposal = validating[0]
        for agent_id in self._agent_keys:
            if agent_id != proposal.creator_id and agent_id not in proposal.validators:
                agent = self.state.agents[agent_id]
                data = strat.validation_data_strengthen()
                resp = self.client.post(
                    f"/api/proposals/{proposal.proposal_id}/validate",
                    headers=self._headers(agent),
                    json=data,
                )
                self._track_response(resp, f"strengthen proposal {proposal.proposal_id}")
                if resp.status_code == 200:
                    proposal.validators[agent_id] = "strengthen"
                return

    @rule()
    def revise_proposal(self):
        """Creator revises a proposal that has strengthen feedback."""
        validating = [
            p for p in self.state.proposals.values()
            if p.status == "validating"
            and any(v == "strengthen" for v in p.validators.values())
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
    def self_validate_proposal(self):
        """Creator tries to validate own proposal — must be rejected."""
        validating = [p for p in self.state.proposals.values() if p.status == "validating"]
        if not validating:
            return
        proposal = validating[-1]
        creator = self.state.agents[proposal.creator_id]
        data = strat.validation_data("approve")
        resp = self.client.post(
            f"/api/proposals/{proposal.proposal_id}/validate",
            headers=self._headers(creator),
            json=data,
        )
        self._track_response(resp, f"self-validate proposal {proposal.proposal_id}")
        assert resp.status_code == 400, (
            f"Self-validation should return 400 but got {resp.status_code}: "
            f"{resp.text[:200]}"
        )
