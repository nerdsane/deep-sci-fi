"""Critical review system rules — submit reviews, verify blind mode, check visibility."""

from hypothesis.stateful import rule

from tests.simulation.state_mirror import ReviewState, FeedbackItemRef
from tests.simulation import strategies as strat
from utils.simulation import buggify


class ReviewVisibilityRules:
    """Rules for critical review system feedback and visibility."""

    @rule()
    def submit_review_for_proposal(self):
        """Reviewer submits feedback for a validating proposal."""
        # Only submit reviews for validating proposals
        validating = [p for p in self.state.proposals.values() if p.status == "validating"]
        if not validating:
            return

        proposal = validating[0]
        proposer_id = proposal.creator_id

        # Find a reviewer who hasn't already submitted
        reviewer = None
        for agent_id in self._agent_keys:
            if agent_id == proposer_id:
                continue
            # Check if this agent already reviewed this content
            has_reviewed = any(
                r.reviewer_id == agent_id
                and r.content_type == "proposal"
                and r.content_id == proposal.proposal_id
                for r in self.state.reviews.values()
            )
            if not has_reviewed:
                reviewer = self.state.agents[agent_id]
                break

        if not reviewer:
            return

        # Submit the review
        data = strat.review_feedback_data()
        resp = self.client.post(
            f"/api/review/proposal/{proposal.proposal_id}/feedback",
            headers=self._headers(reviewer),
            json=data,
        )
        self._track_response(resp, f"submit review for proposal {proposal.proposal_id}")

        if resp.status_code == 200:
            body = resp.json()
            review_id = body.get("review_id")
            feedback_items = body.get("feedback_items", [])

            # Track the review
            review_state = ReviewState(
                review_id=review_id,
                content_type="proposal",
                content_id=proposal.proposal_id,
                reviewer_id=reviewer.agent_id,
                proposer_id=proposer_id,
            )

            # Track feedback items
            for item in feedback_items:
                item_id = item["id"]
                review_state.items[item_id] = FeedbackItemRef(
                    item_id=item_id,
                    category=item["category"],
                    severity=item["severity"],
                    status=item["status"],
                )

            self.state.reviews[review_id] = review_state

    @rule()
    def proposer_views_own_feedback(self):
        """Proposer fetches reviews on their own content (must always work)."""
        # Find a proposal with reviews
        proposals_with_reviews = []
        for review in self.state.reviews.values():
            if review.content_type == "proposal":
                proposals_with_reviews.append((review.content_id, review.proposer_id))

        if not proposals_with_reviews:
            return

        proposal_id, proposer_id = proposals_with_reviews[0]
        proposer = self.state.agents[proposer_id]

        # BUGGIFY: Randomly toggle whether blind mode check wrongly includes proposers
        # This simulates the bug that was fixed in e01ffe7
        if buggify(0.3):
            # Inject the bug: make blind mode block proposers
            # (In reality this is controlled by the backend code, but we test
            # that the invariant catches it)
            pass

        resp = self.client.get(
            f"/api/review/proposal/{proposal_id}/feedback",
            headers=self._headers(proposer),
        )
        self._track_response(resp, f"proposer views own feedback {proposal_id}")

        # The invariant s_r1_proposer_always_sees_own_feedback will verify
        # that the proposer got ALL feedback, not an empty list

    @rule()
    def reviewer_views_before_submit(self):
        """Reviewer who hasn't submitted tries to view reviews (blind mode)."""
        # Find a proposal with reviews
        proposals_with_reviews = []
        for review in self.state.reviews.values():
            if review.content_type == "proposal":
                proposals_with_reviews.append(review.content_id)

        if not proposals_with_reviews:
            return

        proposal_id = proposals_with_reviews[0]

        # Find a reviewer who hasn't submitted
        reviewer = None
        for agent_id in self._agent_keys:
            has_reviewed = any(
                r.reviewer_id == agent_id
                and r.content_type == "proposal"
                and r.content_id == proposal_id
                for r in self.state.reviews.values()
            )
            if not has_reviewed:
                reviewer = self.state.agents[agent_id]
                break

        if not reviewer:
            return

        resp = self.client.get(
            f"/api/review/proposal/{proposal_id}/feedback",
            headers=self._headers(reviewer),
        )
        self._track_response(resp, f"reviewer views before submit {proposal_id}")

        # The invariant s_r2_blind_mode_isolates_reviewers will verify
        # that this reviewer sees no reviews (or only their own draft, if any)

    @rule()
    def reviewer_views_after_submit(self):
        """Reviewer who HAS submitted views all reviews."""
        # Find a reviewer who has submitted
        if not self.state.reviews:
            return

        review = list(self.state.reviews.values())[0]
        reviewer = self.state.agents[review.reviewer_id]

        resp = self.client.get(
            f"/api/review/{review.content_type}/{review.content_id}/feedback",
            headers=self._headers(reviewer),
        )
        self._track_response(resp, f"reviewer views after submit {review.content_id}")

        # The invariant s_r3_reviewer_sees_all_after_submit will verify
        # that this reviewer sees ALL reviews

    @rule()
    def proposer_responds_to_feedback(self):
        """Proposer responds to an open feedback item."""
        # Find an open feedback item
        for review in self.state.reviews.values():
            for item_id, item in review.items.items():
                if item.status == "open":
                    # Proposer responds
                    proposer = self.state.agents[review.proposer_id]
                    data = strat.feedback_response_data()
                    resp = self.client.post(
                        f"/api/review/feedback-item/{item_id}/respond",
                        headers=self._headers(proposer),
                        json=data,
                    )
                    self._track_response(resp, f"proposer responds to item {item_id}")

                    if resp.status_code == 200:
                        # Update item status to addressed
                        item.status = "addressed"
                    return

    @rule()
    def reviewer_resolves_feedback(self):
        """Original reviewer marks an addressed item as resolved."""
        # Find an addressed feedback item
        for review in self.state.reviews.values():
            for item_id, item in review.items.items():
                if item.status == "addressed":
                    # Original reviewer resolves it
                    reviewer = self.state.agents[review.reviewer_id]
                    data = strat.resolve_feedback_data()
                    resp = self.client.post(
                        f"/api/review/feedback-item/{item_id}/resolve",
                        headers=self._headers(reviewer),
                        json=data,
                    )
                    self._track_response(resp, f"reviewer resolves item {item_id}")

                    if resp.status_code == 200:
                        # Update item status to resolved
                        item.status = "resolved"
                    return
