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
        self._l4_stories_with_acclaim_conditions()
        self._l5_rejected_proposals_have_rejections()
        self._l6_escalated_actions_produce_events()

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

    def _l4_stories_with_acclaim_conditions(self):
        """L4: Stories meeting all acclaim conditions should be acclaimed."""
        for sid, ss in self.state.stories.items():
            acclaim_reviews = sum(
                1 for ref in ss.reviews.values()
                if ref.recommend_acclaim
            )
            responded = sum(
                1 for ref in ss.reviews.values()
                if ref.review_id in ss.author_responses
            )
            all_responded = responded == len(ss.reviews) and len(ss.reviews) > 0
            if acclaim_reviews >= 2 and all_responded and ss.revision_count >= 1:
                assert ss.status == "ACCLAIMED", (
                    f"Story {sid}: {acclaim_reviews} acclaim reviews, all responded, "
                    f"revision_count={ss.revision_count}, but status={ss.status}"
                )

    def _l5_rejected_proposals_have_rejections(self):
        """L5: Rejected proposals must have at least 2 rejection votes."""
        for pid, p in self.state.proposals.items():
            if p.status != "rejected":
                continue
            rejections = sum(1 for v in p.validators.values() if v == "reject")
            assert rejections >= 2, (
                f"Proposal {pid}: status=rejected but only {rejections} "
                f"rejection votes (need >= 2)"
            )

    def _l6_escalated_actions_produce_events(self):
        """L6: Number of escalated actions <= number of events."""
        escalated = sum(1 for a in self.state.actions.values() if a.escalated)
        event_count = len(self.state.events)
        assert escalated <= event_count, (
            f"Escalated actions ({escalated}) > events ({event_count}); "
            f"escalation should produce an event"
        )
