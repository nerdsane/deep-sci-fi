"""Liveness invariants — checked at teardown only.

These verify eventual consistency properties that aren't guaranteed
after every single step but should hold by end of test run.
"""


class LivenessInvariantsMixin:
    """Liveness invariants checked at teardown."""

    def check_liveness_invariants(self):
        """Run all liveness checks. Called from teardown."""
        self._l1_proposals_with_approvals()
        self._l2_dweller_proposals_with_approvals()
        self._l3_suggestions_resolved()

    def _l1_proposals_with_approvals(self):
        """L1: Proposals with 2+ approvals and 0 rejections should be approved."""
        for pid, p in self.state.proposals.items():
            approvals = sum(1 for v in p.validators.values() if v == "approve")
            rejections = sum(1 for v in p.validators.values() if v == "reject")
            if approvals >= 2 and rejections == 0:
                assert p.status == "approved", (
                    f"Proposal {pid}: {approvals} approvals, {rejections} rejections "
                    f"but status is {p.status}"
                )

    def _l2_dweller_proposals_with_approvals(self):
        """L2: Dweller proposals with 2+ approvals and 0 rejections should be approved."""
        for dp_id, dp in self.state.dweller_proposals.items():
            approvals = sum(1 for v in dp.validators.values() if v == "approve")
            rejections = sum(1 for v in dp.validators.values() if v == "reject")
            if approvals >= 2 and rejections == 0:
                assert dp.status == "approved", (
                    f"Dweller proposal {dp_id}: {approvals} approvals, "
                    f"{rejections} rejections but status is {dp.status}"
                )

    def _l3_suggestions_resolved(self):
        """L3: No structural inconsistencies in suggestion state."""
        for sid, s in self.state.suggestions.items():
            if s.status == "accepted":
                # Accepted suggestions should have been accepted by owner
                assert s.owner_id in self.state.agents, (
                    f"Suggestion {sid}: accepted but owner {s.owner_id} unknown"
                )
            if s.status == "withdrawn":
                # Withdrawn suggestions should have been withdrawn by suggester
                assert s.suggester_id in self.state.agents, (
                    f"Suggestion {sid}: withdrawn but suggester {s.suggester_id} unknown"
                )
