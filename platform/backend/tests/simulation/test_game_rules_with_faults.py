"""Fault injection layer on top of core DST state machine.

Inherits all rules + invariants from DeepSciFiGameRules, adds concurrent
fault scenarios that stress race conditions.
"""

from concurrent.futures import ThreadPoolExecutor

from hypothesis import settings, HealthCheck
from hypothesis.stateful import rule

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

        def claim(agent):
            return self.client.post(
                f"/api/dwellers/{did}/claim",
                headers=self._headers(agent),
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_a = pool.submit(claim, agent_a)
            fut_b = pool.submit(claim, agent_b)
            resp_a = fut_a.result()
            resp_b = fut_b.result()

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

        def validate(agent):
            data = strat.validation_data("approve")
            return self.client.post(
                f"/api/proposals/{proposal.proposal_id}/validate",
                headers=self._headers(agent),
                json=data,
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_a = pool.submit(validate, agent_a)
            fut_b = pool.submit(validate, agent_b)
            resp_a = fut_a.result()
            resp_b = fut_b.result()

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


# Run the state machine
TestGameRulesWithFaults = DeepSciFiGameRulesWithFaults.TestCase
TestGameRulesWithFaults.settings = settings(
    max_examples=50,
    stateful_step_count=30,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)
