"""Combined fuzz + fault injection layer (Tier 4).

Inherits all rules + invariants from DeepSciFiGameRules, all fuzz rules
from FuzzRulesMixin, and adds concurrent fault rules that use fuzzed data.

This is the most thorough tier: diverse Pydantic-generated data exercised
under concurrent race conditions. Catches bugs that neither fuzzing alone
(single-threaded) nor fault injection with fixed data can find.
"""

from hypothesis import settings, HealthCheck
from hypothesis.stateful import rule
import hypothesis.strategies as st

from main import app
from tests.simulation.test_game_rules import DeepSciFiGameRules
from tests.simulation.rules.fuzz import FuzzRulesMixin
from tests.simulation.rules.fuzz_chains import CrossDomainFuzzMixin, FuzzChainRulesMixin
from tests.simulation.concurrent import run_concurrent_requests
from tests.simulation.pydantic_strategies import from_model, serialize
from tests.simulation.state_mirror import (
    FeedbackState,
    StoryReviewRef,
)

from api.events import EventApproveRequest
from api.reviews import SubmitReviewRequest
from api.feedback import FeedbackCreateRequest


class FuzzFaultRulesMixin:
    """Concurrent fault rules that use fuzzed data."""

    # ------------------------------------------------------------------
    # Concurrent fuzz claim: two agents claim same dweller with fuzzed
    # dweller data in the world
    # ------------------------------------------------------------------
    @rule()
    def inject_concurrent_claim_fuzzed_dweller(self):
        """Two agents concurrently claim a dweller created by fuzz rules."""
        if not self.state.dwellers:
            return
        did = list(self.state.dwellers.keys())[0]

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

        self._track_response(resp_a, f"fuzz concurrent claim A {did}")
        self._track_response(resp_b, f"fuzz concurrent claim B {did}")

        # At most one should succeed
        successes = sum(1 for r in [resp_a, resp_b] if r.status_code == 200)
        assert successes <= 1, (
            f"Concurrent fuzz claim race: {successes} agents claimed dweller {did}! "
            f"A={resp_a.status_code} B={resp_b.status_code}"
        )

    # ------------------------------------------------------------------
    # Concurrent fuzz review: two agents submit fuzzed reviews for
    # same proposal simultaneously
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def inject_concurrent_fuzz_review(self, data):
        """Two agents submit fuzzed review feedback simultaneously."""
        validating = [p for p in self.state.proposals.values() if p.status == "validating"]
        if not validating:
            return
        proposal = validating[0]

        unused = [
            aid for aid in self._agent_keys
            if aid != proposal.creator_id and aid not in proposal.validators
        ]
        if len(unused) < 2:
            return

        agent_a = self.state.agents[unused[0]]
        agent_b = self.state.agents[unused[1]]

        data_a = serialize(data.draw(from_model(SubmitReviewRequest)))
        data_b = serialize(data.draw(from_model(SubmitReviewRequest)))

        resp_a, resp_b = self.client.portal.call(
            run_concurrent_requests,
            app,
            [
                {"method": "POST",
                 "url": f"/api/review/proposal/{proposal.proposal_id}/feedback",
                 "headers": self._headers(agent_a),
                 "json": data_a},
                {"method": "POST",
                 "url": f"/api/review/proposal/{proposal.proposal_id}/feedback",
                 "headers": self._headers(agent_b),
                 "json": data_b},
            ],
        )

        self._track_response(resp_a, f"fuzz concurrent review A {proposal.proposal_id}")
        self._track_response(resp_b, f"fuzz concurrent review B {proposal.proposal_id}")

        # Both should succeed (different reviewers) — neither should 500
        for resp in [resp_a, resp_b]:
            assert resp.status_code < 500, (
                f"Concurrent fuzz review submission 500: {resp.text[:300]}"
            )

        for agent, resp in [(agent_a, resp_a), (agent_b, resp_b)]:
            if resp.status_code in (200, 201):
                proposal.validators[agent.agent_id] = "reviewed"

    # ------------------------------------------------------------------
    # Concurrent fuzz event approval: two agents approve same event
    # with fuzzed EventApproveRequest
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def inject_concurrent_fuzz_event_approval(self, data):
        """Two agents try to approve same event with fuzzed data simultaneously."""
        pending_events = [e for e in self.state.events.values() if e.status == "pending"]
        if not pending_events:
            return
        event = pending_events[0]

        candidates = [
            aid for aid in self._agent_keys
            if aid != event.creator_id
        ]
        if len(candidates) < 2:
            return

        agent_a = self.state.agents[candidates[0]]
        agent_b = self.state.agents[candidates[1]]

        data_a = serialize(data.draw(from_model(EventApproveRequest)))
        data_b = serialize(data.draw(from_model(EventApproveRequest)))

        resp_a, resp_b = self.client.portal.call(
            run_concurrent_requests,
            app,
            [
                {"method": "POST",
                 "url": f"/api/events/{event.event_id}/approve",
                 "headers": self._headers(agent_a),
                 "json": data_a},
                {"method": "POST",
                 "url": f"/api/events/{event.event_id}/approve",
                 "headers": self._headers(agent_b),
                 "json": data_b},
            ],
        )

        self._track_response(resp_a, f"fuzz concurrent event approve A {event.event_id}")
        self._track_response(resp_b, f"fuzz concurrent event approve B {event.event_id}")

        # At most one should succeed
        successes = sum(1 for r in [resp_a, resp_b] if r.status_code == 200)
        assert successes <= 1, (
            f"Concurrent fuzz event approval race: {successes} approvals! "
            f"A={resp_a.status_code} B={resp_b.status_code}"
        )

        for resp in [resp_a, resp_b]:
            if resp.status_code == 200:
                event.status = "approved"

    # ------------------------------------------------------------------
    # Fuzz duplicate feedback: submit fuzzed feedback twice rapidly
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def inject_concurrent_fuzz_duplicate_feedback(self, data):
        """Submit fuzzed feedback twice concurrently. Neither should 500."""
        agent = self._random_agent()
        payload = serialize(data.draw(from_model(FeedbackCreateRequest)))

        resp1, resp2 = self.client.portal.call(
            run_concurrent_requests,
            app,
            [
                {"method": "POST", "url": "/api/feedback",
                 "headers": self._headers(agent), "json": payload},
                {"method": "POST", "url": "/api/feedback",
                 "headers": self._headers(agent), "json": payload},
            ],
        )

        self._track_response(resp1, "fuzz concurrent duplicate feedback 1")
        self._track_response(resp2, "fuzz concurrent duplicate feedback 2")

        assert resp1.status_code < 500, f"First fuzz feedback 500: {resp1.text[:300]}"
        assert resp2.status_code < 500, f"Second fuzz feedback 500: {resp2.text[:300]}"

        for resp in [resp1, resp2]:
            if resp.status_code in (200, 201):
                body = resp.json()
                fb_data = body.get("feedback", body)
                fid = fb_data.get("id")
                if fid:
                    self.state.feedback[fid] = FeedbackState(
                        feedback_id=fid,
                        creator_id=agent.agent_id,
                    )

    # ------------------------------------------------------------------
    # Concurrent fuzz story review: two agents submit fuzzed story
    # reviews simultaneously
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def inject_concurrent_fuzz_story_review(self, data):
        """Two agents submit fuzzed story reviews simultaneously."""
        eligible_stories = [
            s for s in self.state.stories.values()
            if s.status in ("PUBLISHED", "ACCLAIMED")
        ]
        if not eligible_stories:
            return
        story = eligible_stories[0]

        candidates = [
            aid for aid in self._agent_keys
            if aid != story.author_id and aid not in story.reviews
        ]
        if len(candidates) < 2:
            return

        agent_a = self.state.agents[candidates[0]]
        agent_b = self.state.agents[candidates[1]]

        # Fuzz the review data — use recommend_acclaim as bool draw
        recommend_a = data.draw(st.booleans())
        recommend_b = data.draw(st.booleans())
        data_a = {
            "recommend_acclaim": recommend_a,
            "improvements": [data.draw(st.text(min_size=10, max_size=200))],
            "canon_notes": data.draw(st.text(min_size=10, max_size=200)),
            "event_notes": data.draw(st.text(min_size=10, max_size=200)),
            "style_notes": data.draw(st.text(min_size=10, max_size=200)),
        }
        data_b = {
            "recommend_acclaim": recommend_b,
            "improvements": [data.draw(st.text(min_size=10, max_size=200))],
            "canon_notes": data.draw(st.text(min_size=10, max_size=200)),
            "event_notes": data.draw(st.text(min_size=10, max_size=200)),
            "style_notes": data.draw(st.text(min_size=10, max_size=200)),
        }

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

        self._track_response(resp_a, f"fuzz concurrent story review A {story.story_id}")
        self._track_response(resp_b, f"fuzz concurrent story review B {story.story_id}")

        for resp in [resp_a, resp_b]:
            assert resp.status_code < 500, (
                f"Concurrent fuzz story review 500: {resp.text[:300]}"
            )

        for agent, resp, review_data in [
            (agent_a, resp_a, data_a),
            (agent_b, resp_b, data_b),
        ]:
            if resp.status_code == 200:
                body = resp.json()
                review_resp = body.get("review", {})
                review_id = review_resp.get("id")
                if review_id:
                    story.reviews[agent.agent_id] = StoryReviewRef(
                        review_id=review_id,
                        recommend_acclaim=review_data["recommend_acclaim"],
                    )


class FuzzedWithFaults(FuzzFaultRulesMixin, FuzzChainRulesMixin, CrossDomainFuzzMixin, FuzzRulesMixin, DeepSciFiGameRules):
    """Tier 4: Full state machine with fuzz rules + chains + concurrent fault injection.

    Inherits:
    - ~95 deterministic rules from DeepSciFiGameRules
    - ~10 fuzz rules from FuzzRulesMixin
    - 5 cross-domain rules from CrossDomainFuzzMixin
    - 4 fuzz chain rules from FuzzChainRulesMixin
    - 5 concurrent fuzz-fault rules from FuzzFaultRulesMixin
    - All safety + liveness invariants
    """


# Run the state machine
TestGameRulesWithFuzzFaults = FuzzedWithFaults.TestCase
TestGameRulesWithFuzzFaults.settings = settings(
    max_examples=20,
    stateful_step_count=15,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)
