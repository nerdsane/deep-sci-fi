"""Dweller proposal rules mixin — create, submit, validate dweller proposals."""

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
    def validate_dweller_proposal(self):
        """Non-creator validates a dweller proposal."""
        validating = [dp for dp in self.state.dweller_proposals.values()
                      if dp.status == "validating"]
        if not validating:
            return
        dp = validating[0]
        # Find a validator who hasn't validated yet and isn't the creator
        for agent_id in self._agent_keys:
            if agent_id != dp.creator_id and agent_id not in dp.validators:
                agent = self.state.agents[agent_id]
                data = strat.dweller_proposal_validation_data("approve")
                resp = self.client.post(
                    f"/api/dweller-proposals/{dp.proposal_id}/validate",
                    headers=self._headers(agent),
                    json=data,
                )
                self._track_response(resp, f"validate dweller proposal {dp.proposal_id}")
                if resp.status_code == 200:
                    dp.validators[agent_id] = "approve"
                    body = resp.json()
                    new_status = body.get("proposal_status")
                    if new_status:
                        dp.status = new_status
                    # If approved, a dweller was created
                    dweller_created = body.get("dweller_created")
                    if dweller_created and isinstance(dweller_created, dict):
                        did = dweller_created.get("id")
                        if did:
                            world = self.state.worlds.get(dp.world_id)
                            region = world.regions[0] if world and world.regions else "unknown"
                            self.state.dwellers[did] = DwellerState(
                                dweller_id=did,
                                world_id=dp.world_id,
                                origin_region=region,
                            )
                return

    @rule()
    def strengthen_dweller_proposal(self):
        """Non-creator strengthens a dweller proposal."""
        validating = [dp for dp in self.state.dweller_proposals.values()
                      if dp.status == "validating"]
        if not validating:
            return
        dp = validating[0]
        for agent_id in self._agent_keys:
            if agent_id != dp.creator_id and agent_id not in dp.validators:
                agent = self.state.agents[agent_id]
                data = strat.dweller_proposal_validation_data_strengthen()
                resp = self.client.post(
                    f"/api/dweller-proposals/{dp.proposal_id}/validate",
                    headers=self._headers(agent),
                    json=data,
                )
                self._track_response(resp, f"strengthen dweller proposal {dp.proposal_id}")
                if resp.status_code == 200:
                    dp.validators[agent_id] = "strengthen"
                return

    @rule()
    def revise_dweller_proposal(self):
        """Creator revises a dweller proposal that has strengthen feedback."""
        validating = [
            dp for dp in self.state.dweller_proposals.values()
            if dp.status == "validating"
            and any(v == "strengthen" for v in dp.validators.values())
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
