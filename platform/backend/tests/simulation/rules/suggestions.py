"""Suggestion rules mixin — suggest, accept, reject, upvote, withdraw."""

from hypothesis.stateful import rule

from tests.simulation.state_mirror import SuggestionState
from tests.simulation import strategies as strat


class SuggestionRulesMixin:
    """Rules for revision suggestion lifecycle."""

    @rule()
    def suggest_proposal_revision(self):
        """Non-creator suggests a revision to a validating proposal."""
        validating = [p for p in self.state.proposals.values() if p.status == "validating"]
        if not validating:
            return
        proposal = validating[0]
        suggester = self._other_agent(proposal.creator_id)
        if not suggester:
            return
        data = strat.suggestion_data("premise")
        resp = self.client.post(
            f"/api/suggestions/proposals/{proposal.proposal_id}/suggest-revision",
            headers=self._headers(suggester),
            json=data,
        )
        self._track_response(resp, f"suggest revision on {proposal.proposal_id}")
        if resp.status_code == 200:
            body = resp.json()
            sid = body.get("suggestion_id")
            if sid:
                self.state.suggestions[sid] = SuggestionState(
                    suggestion_id=sid,
                    target_type="proposal",
                    target_id=proposal.proposal_id,
                    suggester_id=suggester.agent_id,
                    owner_id=proposal.creator_id,
                    status="pending",
                )

    @rule()
    def suggest_aspect_revision(self):
        """Non-creator suggests a revision to an approved aspect."""
        approved = [a for a in self.state.aspects.values() if a.status == "approved"]
        if not approved:
            return
        aspect = approved[0]
        suggester = self._other_agent(aspect.creator_id)
        if not suggester:
            return
        data = strat.suggestion_data("premise")
        resp = self.client.post(
            f"/api/suggestions/aspects/{aspect.aspect_id}/suggest-revision",
            headers=self._headers(suggester),
            json=data,
        )
        self._track_response(resp, f"suggest aspect revision on {aspect.aspect_id}")
        if resp.status_code == 200:
            body = resp.json()
            sid = body.get("suggestion_id")
            if sid:
                self.state.suggestions[sid] = SuggestionState(
                    suggestion_id=sid,
                    target_type="aspect",
                    target_id=aspect.aspect_id,
                    suggester_id=suggester.agent_id,
                    owner_id=aspect.creator_id,
                    status="pending",
                )

    @rule()
    def accept_suggestion(self):
        """Owner accepts a pending suggestion."""
        pending = [s for s in self.state.suggestions.values() if s.status == "pending"]
        if not pending:
            return
        suggestion = pending[0]
        owner = self.state.agents.get(suggestion.owner_id)
        if not owner:
            return
        data = strat.suggestion_response_data(accept=True)
        resp = self.client.post(
            f"/api/suggestions/{suggestion.suggestion_id}/accept",
            headers=self._headers(owner),
            json=data,
        )
        self._track_response(resp, f"accept suggestion {suggestion.suggestion_id}")
        if resp.status_code == 200:
            suggestion.status = "accepted"

    @rule()
    def reject_suggestion(self):
        """Owner rejects a pending suggestion."""
        pending = [s for s in self.state.suggestions.values() if s.status == "pending"]
        if not pending:
            return
        suggestion = pending[0]
        owner = self.state.agents.get(suggestion.owner_id)
        if not owner:
            return
        data = strat.suggestion_response_data(accept=False)
        resp = self.client.post(
            f"/api/suggestions/{suggestion.suggestion_id}/reject",
            headers=self._headers(owner),
            json=data,
        )
        self._track_response(resp, f"reject suggestion {suggestion.suggestion_id}")
        if resp.status_code == 200:
            suggestion.status = "rejected"

    @rule()
    def upvote_suggestion(self):
        """Non-suggester upvotes a pending suggestion."""
        pending = [s for s in self.state.suggestions.values() if s.status == "pending"]
        if not pending:
            return
        suggestion = pending[0]
        for agent_id in self._agent_keys:
            if agent_id != suggestion.suggester_id and agent_id not in suggestion.upvoters:
                agent = self.state.agents[agent_id]
                resp = self.client.post(
                    f"/api/suggestions/{suggestion.suggestion_id}/upvote",
                    headers=self._headers(agent),
                )
                self._track_response(resp, f"upvote suggestion {suggestion.suggestion_id}")
                if resp.status_code == 200:
                    suggestion.upvoters.add(agent_id)
                return

    @rule()
    def withdraw_suggestion(self):
        """Suggester withdraws their own pending suggestion."""
        pending = [s for s in self.state.suggestions.values()
                   if s.status == "pending"]
        if not pending:
            return
        suggestion = pending[0]
        suggester = self.state.agents.get(suggestion.suggester_id)
        if not suggester:
            return
        resp = self.client.post(
            f"/api/suggestions/{suggestion.suggestion_id}/withdraw",
            headers=self._headers(suggester),
        )
        self._track_response(resp, f"withdraw suggestion {suggestion.suggestion_id}")
        if resp.status_code == 200:
            suggestion.status = "withdrawn"
