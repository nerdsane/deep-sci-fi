"""Fault injection layer on top of core DST state machine.

Inherits all rules + invariants from DeepSciFiGameRules, adds concurrent
fault scenarios that stress race conditions.

Concurrency model: asyncio tasks (deterministic, single-threaded) instead
of OS threads (non-deterministic scheduling). BUGGIFY delays control
interleaving order via the seeded RNG.
"""

from hypothesis import settings, HealthCheck
from hypothesis.stateful import rule

from main import app
from tests.simulation.concurrent import run_concurrent_requests
from tests.simulation.test_game_rules import DeepSciFiGameRules
from tests.simulation.state_mirror import WorldState, FeedbackState
from tests.simulation import strategies as strat


class DeepSciFiGameRulesWithFaults(DeepSciFiGameRules):
    """Extended state machine with concurrent fault injection rules."""

    @rule()
    def inject_concurrent_claim(self):
        """Two agents try to claim the same dweller simultaneously."""
        if not self.state.dwellers:
            return
        did = list(self.state.dwellers.keys())[0]

        # Pick two different agents
        if len(self._agent_keys) < 2:
            return
        agent_a = self.state.agents[self._agent_keys[0]]
        agent_b = self.state.agents[self._agent_keys[1]]

        resp_a, resp_b = self.client.portal.call(
            run_concurrent_requests,
            app,
            [
                {"method": "POST", "url": f"/api/dwellers/{did}/claim",
                 "headers": self._headers(agent_a)},
                {"method": "POST", "url": f"/api/dwellers/{did}/claim",
                 "headers": self._headers(agent_b)},
            ],
        )

        self._track_response(resp_a, f"concurrent claim A {did}")
        self._track_response(resp_b, f"concurrent claim B {did}")

        # At most one should succeed
        successes = sum(1 for r in [resp_a, resp_b] if r.status_code == 200)
        assert successes <= 1, (
            f"Concurrent claim race: {successes} agents claimed dweller {did}! "
            f"A={resp_a.status_code} B={resp_b.status_code}"
        )

    @rule()
    def inject_duplicate_feedback(self):
        """Same feedback submitted twice rapidly. Neither should 500."""
        agent = self._random_agent()
        data = strat.feedback_data()

        resp1 = self.client.post(
            "/api/feedback",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp1, "duplicate feedback 1")

        resp2 = self.client.post(
            "/api/feedback",
            headers=self._headers(agent),
            json=data,
        )
        self._track_response(resp2, "duplicate feedback 2")

        # Neither should be a server error
        assert resp1.status_code < 500, f"First feedback 500: {resp1.text}"
        assert resp2.status_code < 500, f"Second feedback 500: {resp2.text}"

        # Track first success
        if resp1.status_code == 200:
            body = resp1.json()
            fb_data = body.get("feedback", {})
            fid = fb_data.get("id")
            if fid:
                self.state.feedback[fid] = FeedbackState(
                    feedback_id=fid,
                    creator_id=agent.agent_id,
                )

    @rule()
    def inject_double_upvote(self):
        """Agent who already upvoted tries again. Must return 400."""
        if not self.state.feedback:
            return
        fid = list(self.state.feedback.keys())[0]
        fb = self.state.feedback[fid]

        # Find a non-creator agent
        for agent_id in self._agent_keys:
            if agent_id != fb.creator_id:
                agent = self.state.agents[agent_id]

                # First upvote (may have already happened)
                resp1 = self.client.post(
                    f"/api/feedback/{fid}/upvote",
                    headers=self._headers(agent),
                )
                self._track_response(resp1, f"double upvote attempt 1 {fid}")

                # Second upvote — must be 400 (already upvoted)
                resp2 = self.client.post(
                    f"/api/feedback/{fid}/upvote",
                    headers=self._headers(agent),
                )
                self._track_response(resp2, f"double upvote attempt 2 {fid}")

                assert resp2.status_code == 400, (
                    f"Double upvote should return 400 but got {resp2.status_code}: {resp2.text}"
                )
                return

    @rule()
    def inject_self_upvote(self):
        """Agent tries to upvote own feedback. Must return 400."""
        if not self.state.feedback:
            return
        fid = list(self.state.feedback.keys())[0]
        fb = self.state.feedback[fid]
        creator = self.state.agents[fb.creator_id]

        resp = self.client.post(
            f"/api/feedback/{fid}/upvote",
            headers=self._headers(creator),
        )
        self._track_response(resp, f"self upvote {fid}")
        assert resp.status_code == 400, (
            f"Self-upvote should return 400 but got {resp.status_code}: {resp.text}"
        )

    @rule()
    def inject_unauthenticated_request(self):
        """State modification without auth. Must return 401/403."""
        data = strat.proposal_data()
        resp = self.client.post("/api/proposals", json=data)
        self._track_response(resp, "unauthenticated proposal")
        assert resp.status_code in (401, 403, 422), (
            f"Unauthenticated request should be rejected but got {resp.status_code}"
        )

    @rule()
    def inject_concurrent_validation(self):
        """Two agents validate same proposal simultaneously."""
        validating = [p for p in self.state.proposals.values() if p.status == "validating"]
        if not validating:
            return
        proposal = validating[0]

        # Find two unused validators
        unused = [
            aid for aid in self._agent_keys
            if aid != proposal.creator_id and aid not in proposal.validators
        ]
        if len(unused) < 2:
            return

        agent_a = self.state.agents[unused[0]]
        agent_b = self.state.agents[unused[1]]

        data_a = strat.validation_data("approve")
        data_b = strat.validation_data("approve")

        resp_a, resp_b = self.client.portal.call(
            run_concurrent_requests,
            app,
            [
                {"method": "POST",
                 "url": f"/api/proposals/{proposal.proposal_id}/validate",
                 "headers": self._headers(agent_a),
                 "json": data_a},
                {"method": "POST",
                 "url": f"/api/proposals/{proposal.proposal_id}/validate",
                 "headers": self._headers(agent_b),
                 "json": data_b},
            ],
        )

        self._track_response(resp_a, f"concurrent validate A {proposal.proposal_id}")
        self._track_response(resp_b, f"concurrent validate B {proposal.proposal_id}")

        # Track successful validations
        for agent, resp in [(agent_a, resp_a), (agent_b, resp_b)]:
            if resp.status_code == 200:
                proposal.validators[agent.agent_id] = "approve"
                body = resp.json()
                wc = body.get("world_created")
                if wc and isinstance(wc, dict):
                    world_id = wc["id"]
                    proposal.status = "approved"
                    self.state.worlds[world_id] = WorldState(
                        world_id=world_id,
                        creator_id=proposal.creator_id,
                        source_proposal_id=proposal.proposal_id,
                    )
                elif body.get("proposal_status"):
                    proposal.status = body["proposal_status"]

    # -------------------------------------------------------------------------
    # New concurrent fault rules (Phase 3.6)
    # -------------------------------------------------------------------------

    @rule()
    def inject_concurrent_suggestion_upvote(self):
        """Two agents upvote the same suggestion simultaneously."""
        if not self.state.suggestions:
            return
        sid = list(self.state.suggestions.keys())[0]
        sg = self.state.suggestions[sid]

        if sg.status != "pending":
            return

        # Find two agents who haven't upvoted and aren't the suggester
        candidates = [
            aid for aid in self._agent_keys
            if aid != sg.suggester_id and aid not in sg.upvoters
        ]
        if len(candidates) < 2:
            return

        agent_a = self.state.agents[candidates[0]]
        agent_b = self.state.agents[candidates[1]]

        resp_a, resp_b = self.client.portal.call(
            run_concurrent_requests,
            app,
            [
                {"method": "POST",
                 "url": f"/api/suggestions/{sid}/upvote",
                 "headers": self._headers(agent_a)},
                {"method": "POST",
                 "url": f"/api/suggestions/{sid}/upvote",
                 "headers": self._headers(agent_b)},
            ],
        )

        self._track_response(resp_a, f"concurrent suggestion upvote A {sid}")
        self._track_response(resp_b, f"concurrent suggestion upvote B {sid}")

        # Both should succeed (different agents) — neither should 500
        for resp in [resp_a, resp_b]:
            assert resp.status_code < 500, (
                f"Concurrent suggestion upvote 500: {resp.text}"
            )

        # Track upvotes
        for agent, resp in [(agent_a, resp_a), (agent_b, resp_b)]:
            if resp.status_code == 200:
                sg.upvoters.add(agent.agent_id)

    @rule()
    def inject_concurrent_event_approval(self):
        """Two agents try to approve the same event simultaneously."""
        pending_events = [e for e in self.state.events.values() if e.status == "pending"]
        if not pending_events:
            return
        event = pending_events[0]

        # Find two agents who aren't the creator
        candidates = [
            aid for aid in self._agent_keys
            if aid != event.creator_id
        ]
        if len(candidates) < 2:
            return

        agent_a = self.state.agents[candidates[0]]
        agent_b = self.state.agents[candidates[1]]

        data = strat.event_approve_data()

        resp_a, resp_b = self.client.portal.call(
            run_concurrent_requests,
            app,
            [
                {"method": "POST",
                 "url": f"/api/events/{event.event_id}/approve",
                 "headers": self._headers(agent_a),
                 "json": data},
                {"method": "POST",
                 "url": f"/api/events/{event.event_id}/approve",
                 "headers": self._headers(agent_b),
                 "json": data},
            ],
        )

        self._track_response(resp_a, f"concurrent event approve A {event.event_id}")
        self._track_response(resp_b, f"concurrent event approve B {event.event_id}")

        # At most one should succeed (FOR UPDATE serializes)
        successes = sum(1 for r in [resp_a, resp_b] if r.status_code == 200)
        assert successes <= 1, (
            f"Concurrent event approval race: {successes} approvals! "
            f"A={resp_a.status_code} B={resp_b.status_code}"
        )

        # Track if approved
        for resp in [resp_a, resp_b]:
            if resp.status_code == 200:
                event.status = "approved"

    @rule()
    def inject_concurrent_story_review(self):
        """Two agents try to review the same story simultaneously."""
        eligible_stories = [
            s for s in self.state.stories.values()
            if s.status in ("PUBLISHED", "ACCLAIMED")
        ]
        if not eligible_stories:
            return
        story = eligible_stories[0]

        # Find two agents who haven't reviewed and aren't the author
        candidates = [
            aid for aid in self._agent_keys
            if aid != story.author_id and aid not in story.reviews
        ]
        if len(candidates) < 2:
            return

        agent_a = self.state.agents[candidates[0]]
        agent_b = self.state.agents[candidates[1]]

        data_a = strat.review_data(recommend_acclaim=True)
        data_b = strat.review_data(recommend_acclaim=False)

        resp_a, resp_b = self.client.portal.call(
            run_concurrent_requests,
            app,
            [
                {"method": "POST",
                 "url": f"/api/stories/{story.story_id}/review",
                 "headers": self._headers(agent_a),
                 "json": data_a},
                {"method": "POST",
                 "url": f"/api/stories/{story.story_id}/review",
                 "headers": self._headers(agent_b),
                 "json": data_b},
            ],
        )

        self._track_response(resp_a, f"concurrent story review A {story.story_id}")
        self._track_response(resp_b, f"concurrent story review B {story.story_id}")

        # Both should succeed (different reviewers) — neither should 500
        for resp in [resp_a, resp_b]:
            assert resp.status_code < 500, (
                f"Concurrent story review 500: {resp.text}"
            )

        # Track reviews
        from tests.simulation.state_mirror import StoryReviewRef
        for agent, resp, data in [(agent_a, resp_a, data_a), (agent_b, resp_b, data_b)]:
            if resp.status_code == 200:
                body = resp.json()
                review_data = body.get("review", {})
                review_id = review_data.get("id")
                if review_id:
                    story.reviews[agent.agent_id] = StoryReviewRef(
                        review_id=review_id,
                        recommend_acclaim=data["recommend_acclaim"],
                    )


# Run the state machine
TestGameRulesWithFaults = DeepSciFiGameRulesWithFaults.TestCase
TestGameRulesWithFaults.settings = settings(
    max_examples=50,
    stateful_step_count=30,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)
