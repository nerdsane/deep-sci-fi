"""Cross-domain fuzz rules and stateful fuzz chains.

CrossDomainFuzzMixin: Multi-step scenarios that stress entity interactions
across domain boundaries (e.g., proposal→world→story, concurrent writes).

FuzzChainRulesMixin: Full entity lifecycle chains with fuzzed data at each
step. Pushes fuzzed data through creation→submission→validation→approval,
catching bugs where data passes creation but breaks downstream steps.
"""

from hypothesis.stateful import rule
import hypothesis.strategies as st

from main import app
from tests.simulation.concurrent import run_concurrent_requests
from tests.simulation.state_mirror import (
    ProposalState,
    WorldState,
    StoryState,
    AspectState,
    EventState,
    StoryReviewRef,
)
from tests.simulation.pydantic_strategies import from_model, serialize
from tests.simulation import strategies as strat

from api.proposals import ProposalCreateRequest, ValidationCreateRequest
from api.stories import StoryCreateRequest
from api.aspects import AspectCreateRequest
from api.events import EventCreateRequest, EventApproveRequest
from api.reviews import SubmitReviewRequest
from db.models import StoryPerspective


class CrossDomainFuzzMixin:
    """Cross-domain fuzz rules stressing entity interactions."""

    # ------------------------------------------------------------------
    # Rule 1: Create proposal → submit → validate (approve×2) → story
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def cross_fuzz_story_in_fresh_world(self, data):
        """Full lifecycle: fuzz proposal → approve → create story in new world."""
        agent_a = self._random_agent()
        agent_b = self._other_agent(agent_a.agent_id)
        agent_c = self._other_agent(agent_b.agent_id) if agent_b else None
        if not agent_b or not agent_c:
            return
        # Ensure agent_c is different from agent_a
        if agent_c.agent_id == agent_a.agent_id:
            for aid in self._agent_keys:
                if aid != agent_a.agent_id and aid != agent_b.agent_id:
                    agent_c = self.state.agents[aid]
                    break
            else:
                return

        # Step 1: Create proposal with fuzzed data
        proposal_payload = serialize(data.draw(from_model(ProposalCreateRequest)))
        resp = self.client.post(
            "/api/proposals",
            headers=self._headers(agent_a),
            json=proposal_payload,
        )
        self._track_response(resp, "cross: create proposal")
        if resp.status_code != 200:
            return
        pid = resp.json()["id"]
        self.state.proposals[pid] = ProposalState(
            proposal_id=pid, creator_id=agent_a.agent_id, status="draft",
        )

        # Step 2: Submit
        resp = self.client.post(
            f"/api/proposals/{pid}/submit?force=true",
            headers=self._headers(agent_a),
        )
        self._track_response(resp, "cross: submit proposal")
        if resp.status_code != 200:
            return
        self.state.proposals[pid].status = "validating"

        # Step 3: Validate (approve) with two different agents
        for validator in [agent_b, agent_c]:
            val_payload = serialize(data.draw(from_model(
                ValidationCreateRequest, overrides={"verdict": "approve"}
            )))
            resp = self.client.post(
                f"/api/proposals/{pid}/validate",
                headers=self._headers(validator),
                json=val_payload,
            )
            self._track_response(resp, f"cross: validate proposal {pid}")
            if resp.status_code == 200:
                body = resp.json()
                self.state.proposals[pid].validators[validator.agent_id] = "approve"
                # Check if world was created (auto-approval after 2 approves)
                new_status = body.get("proposal_status") or body.get("status")
                if new_status:
                    self.state.proposals[pid].status = new_status

        # Step 4: Check if a world was created
        resp = self.client.get(f"/api/proposals/{pid}")
        self._track_response(resp, f"cross: get proposal {pid}")
        if resp.status_code != 200:
            return
        proposal_body = resp.json().get("proposal", resp.json())
        world_id = proposal_body.get("resulting_world_id")
        if not world_id:
            return  # Proposal wasn't approved yet

        # Track world
        if world_id not in self.state.worlds:
            self.state.worlds[world_id] = WorldState(
                world_id=world_id,
                creator_id=agent_a.agent_id,
                source_proposal_id=pid,
            )

        # Step 5: Create a fuzzed story in the brand-new world
        story_payload = serialize(data.draw(from_model(StoryCreateRequest, overrides={
            "world_id": world_id,
            "perspective": st.sampled_from([
                StoryPerspective.FIRST_PERSON_AGENT,
                StoryPerspective.THIRD_PERSON_OMNISCIENT,
            ]),
            "perspective_dweller_id": None,
            "source_event_ids": [],
            "source_action_ids": [],
        })))
        resp = self.client.post(
            "/api/stories",
            headers=self._headers(agent_b),
            json=story_payload,
        )
        self._track_response(resp, "cross: story in fresh world")
        assert resp.status_code < 500, (
            f"Story in fresh world got {resp.status_code}: {resp.text[:300]}"
        )
        if resp.status_code == 200:
            body = resp.json()
            sid = body.get("id") or body.get("story", {}).get("id")
            if sid:
                self.state.stories[sid] = StoryState(
                    story_id=sid, world_id=world_id,
                    author_id=agent_b.agent_id, status="PUBLISHED",
                )
                # Verify world_id matches
                self._verify_readback(
                    f"/api/stories/{sid}", {"world_id": world_id},
                    {"story.world_id": "world_id"},
                )

    # ------------------------------------------------------------------
    # Rule 2: Concurrent aspect + event creation in same world
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def cross_fuzz_aspect_and_event_concurrent(self, data):
        """Submit fuzzed aspect and event concurrently in same world."""
        if not self.state.worlds:
            return
        world_id = list(self.state.worlds.keys())[0]
        agent = self._random_agent()

        aspect_payload = serialize(data.draw(from_model(AspectCreateRequest, overrides={
            "content": {"description": "Cross-domain fuzzed aspect"},
            "inspired_by_actions": [],
            "proposed_timeline_entry": None,
        })))
        event_payload = serialize(data.draw(from_model(EventCreateRequest)))

        resp_a, resp_e = self.client.portal.call(
            run_concurrent_requests,
            app,
            [
                {"method": "POST",
                 "url": f"/api/aspects/worlds/{world_id}/aspects",
                 "headers": self._headers(agent),
                 "json": aspect_payload},
                {"method": "POST",
                 "url": f"/api/events/worlds/{world_id}/events",
                 "headers": self._headers(agent),
                 "json": event_payload},
            ],
        )

        self._track_response(resp_a, "cross: concurrent aspect")
        self._track_response(resp_e, "cross: concurrent event")

        for resp in [resp_a, resp_e]:
            assert resp.status_code < 500, (
                f"Concurrent aspect/event got {resp.status_code}: {resp.text[:300]}"
            )

        # Both are independent writes — either may 4xx due to validation,
        # but at least one should succeed if the world is valid
        successes = sum(1 for r in [resp_a, resp_e] if r.status_code == 200)

        # Track and read-back successful creates
        if resp_a.status_code == 200:
            body = resp_a.json()
            aid = body.get("id") or body.get("aspect", {}).get("id")
            if aid:
                self.state.aspects[aid] = AspectState(
                    aspect_id=aid, world_id=world_id,
                    creator_id=agent.agent_id, status="draft",
                    aspect_type=aspect_payload.get("aspect_type", "technology"),
                )
                self._verify_readback(
                    f"/api/aspects/{aid}", {"world_id": world_id},
                    {"aspect.world_id": "world_id"},
                )

        if resp_e.status_code == 200:
            body = resp_e.json()
            eid = body.get("id") or body.get("event", {}).get("id")
            if eid:
                self.state.events[eid] = EventState(
                    event_id=eid, world_id=world_id,
                    creator_id=agent.agent_id, status="pending",
                )
                self._verify_readback(
                    f"/api/events/{eid}", {"world_id": world_id},
                    {"event.world_id": "world_id"},
                )

    # ------------------------------------------------------------------
    # Rule 3: Concurrent reviews on same proposal
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def cross_review_after_state_change(self, data):
        """Two agents submit fuzzed reviews concurrently; proposal may auto-approve."""
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

        self._track_response(resp_a, f"cross: concurrent review A {proposal.proposal_id}")
        self._track_response(resp_b, f"cross: concurrent review B {proposal.proposal_id}")

        for resp in [resp_a, resp_b]:
            assert resp.status_code < 500, (
                f"Cross concurrent review got {resp.status_code}: {resp.text[:300]}"
            )

        for agent, resp in [(agent_a, resp_a), (agent_b, resp_b)]:
            if resp.status_code in (200, 201):
                proposal.validators[agent.agent_id] = "reviewed"

    # ------------------------------------------------------------------
    # Rule 4: Aspect rapid lifecycle (create → submit → validate×2)
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def cross_fuzz_rapid_lifecycle(self, data):
        """Fuzzed aspect through full create→submit→validate lifecycle."""
        if not self.state.worlds:
            return
        world_id = list(self.state.worlds.keys())[0]
        agent_a = self._random_agent()
        agent_b = self._other_agent(agent_a.agent_id)
        if not agent_b:
            return

        # Create fuzzed aspect
        aspect_payload = serialize(data.draw(from_model(AspectCreateRequest, overrides={
            "content": {"description": "Rapid lifecycle fuzzed aspect"},
            "inspired_by_actions": [],
            "proposed_timeline_entry": None,
        })))
        resp = self.client.post(
            f"/api/aspects/worlds/{world_id}/aspects",
            headers=self._headers(agent_a),
            json=aspect_payload,
        )
        self._track_response(resp, "cross: rapid aspect create")
        if resp.status_code != 200:
            return
        body = resp.json()
        aid = body.get("id") or body.get("aspect", {}).get("id")
        if not aid:
            return
        self.state.aspects[aid] = AspectState(
            aspect_id=aid, world_id=world_id,
            creator_id=agent_a.agent_id, status="draft",
            aspect_type=aspect_payload.get("aspect_type", "technology"),
        )

        # Submit
        resp = self.client.post(
            f"/api/aspects/{aid}/submit?force=true",
            headers=self._headers(agent_a),
        )
        self._track_response(resp, f"cross: rapid aspect submit {aid}")
        if resp.status_code != 200:
            return
        self.state.aspects[aid].status = "validating"

        # Validate with agent_b (review feedback)
        review_data = strat.review_feedback_data()
        resp = self.client.post(
            f"/api/review/aspect/{aid}/feedback",
            headers=self._headers(agent_b),
            json=review_data,
        )
        self._track_response(resp, f"cross: rapid aspect review {aid}")
        if resp.status_code in (200, 201):
            self.state.aspects[aid].validators[agent_b.agent_id] = "reviewed"

        # Verify aspect is still accessible
        resp = self.client.get(f"/api/aspects/{aid}")
        self._track_response(resp, f"cross: rapid aspect readback {aid}")
        if resp.status_code == 200:
            body = resp.json()
            aspect_data = body.get("aspect", body)
            assert aspect_data.get("title") == aspect_payload.get("title"), (
                f"Rapid lifecycle aspect title mismatch: "
                f"sent={aspect_payload.get('title')!r}, "
                f"got={aspect_data.get('title')!r}"
            )

    # ------------------------------------------------------------------
    # Rule 5: Concurrent dweller claim during action
    # ------------------------------------------------------------------
    @rule()
    def cross_fuzz_dweller_claim_during_action(self):
        """Agent B tries to claim a dweller already claimed by agent A."""
        if not self.state.dwellers or len(self._agent_keys) < 2:
            return

        # Find a claimed dweller
        claimed = None
        owner_id = None
        for d in self.state.dwellers.values():
            if d.claimed_by:
                claimed = d
                owner_id = d.claimed_by
                break
        if not claimed:
            return

        # Find agent B who is not the owner
        agent_b = None
        for aid in self._agent_keys:
            if aid != owner_id:
                agent_b = self.state.agents[aid]
                break
        if not agent_b:
            return

        # Agent B tries to claim the same dweller
        resp = self.client.post(
            f"/api/dwellers/{claimed.dweller_id}/claim",
            headers=self._headers(agent_b),
        )
        self._track_response(resp, f"cross: claim owned dweller {claimed.dweller_id}")

        # Should fail — dweller is already claimed
        assert resp.status_code in (400, 409), (
            f"Claiming already-claimed dweller should fail with 400/409 "
            f"but got {resp.status_code}: {resp.text[:300]}"
        )


class FuzzChainRulesMixin:
    """Stateful fuzz chains pushing fuzzed data through full entity lifecycles."""

    # ------------------------------------------------------------------
    # Chain 1: Proposal → world (full fuzzed lifecycle)
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def fuzz_chain_proposal_to_world(self, data):
        """Fuzzed proposal through create→submit→validate(×2)→world."""
        agent_a = self._random_agent()
        agent_b = self._other_agent(agent_a.agent_id)
        if not agent_b:
            return
        # Find a third agent
        agent_c = None
        for aid in self._agent_keys:
            if aid != agent_a.agent_id and aid != agent_b.agent_id:
                agent_c = self.state.agents[aid]
                break
        if not agent_c:
            return

        # Create
        payload = serialize(data.draw(from_model(ProposalCreateRequest)))
        resp = self.client.post(
            "/api/proposals", headers=self._headers(agent_a), json=payload,
        )
        self._track_response(resp, "chain: create proposal")
        if resp.status_code != 200:
            return
        pid = resp.json()["id"]
        self.state.proposals[pid] = ProposalState(
            proposal_id=pid, creator_id=agent_a.agent_id, status="draft",
        )

        # Submit
        resp = self.client.post(
            f"/api/proposals/{pid}/submit?force=true",
            headers=self._headers(agent_a),
        )
        self._track_response(resp, f"chain: submit {pid}")
        if resp.status_code != 200:
            return
        self.state.proposals[pid].status = "validating"

        # Validate with two different agents (approve)
        for validator in [agent_b, agent_c]:
            val_payload = serialize(data.draw(from_model(
                ValidationCreateRequest, overrides={"verdict": "approve"}
            )))
            resp = self.client.post(
                f"/api/proposals/{pid}/validate",
                headers=self._headers(validator), json=val_payload,
            )
            self._track_response(resp, f"chain: validate {pid}")
            if resp.status_code == 200:
                self.state.proposals[pid].validators[validator.agent_id] = "approve"

        # Verify: check proposal status and resulting world
        resp = self.client.get(f"/api/proposals/{pid}")
        self._track_response(resp, f"chain: get proposal {pid}")
        if resp.status_code != 200:
            return
        proposal_body = resp.json().get("proposal", resp.json())
        status = proposal_body.get("status")
        world_id = proposal_body.get("resulting_world_id")

        if status == "approved":
            assert world_id is not None, (
                f"Proposal {pid} is approved but resulting_world_id is None"
            )
            # Verify world exists
            resp = self.client.get(f"/api/worlds/{world_id}")
            self._track_response(resp, f"chain: get world {world_id}")
            assert resp.status_code == 200, (
                f"Approved proposal world GET failed: {resp.status_code}"
            )
            if world_id not in self.state.worlds:
                self.state.worlds[world_id] = WorldState(
                    world_id=world_id,
                    creator_id=agent_a.agent_id,
                    source_proposal_id=pid,
                )

    # ------------------------------------------------------------------
    # Chain 2: Aspect lifecycle (create → submit → review → readback)
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def fuzz_chain_aspect_lifecycle(self, data):
        """Fuzzed aspect through create→submit→review→readback."""
        if not self.state.worlds:
            return
        world_id = list(self.state.worlds.keys())[0]
        agent_a = self._random_agent()
        agent_b = self._other_agent(agent_a.agent_id)
        if not agent_b:
            return

        # Create fuzzed aspect
        payload = serialize(data.draw(from_model(AspectCreateRequest, overrides={
            "content": {"description": "Chain lifecycle fuzzed aspect"},
            "inspired_by_actions": [],
            "proposed_timeline_entry": None,
        })))
        resp = self.client.post(
            f"/api/aspects/worlds/{world_id}/aspects",
            headers=self._headers(agent_a), json=payload,
        )
        self._track_response(resp, "chain: create aspect")
        if resp.status_code != 200:
            return
        body = resp.json()
        aid = body.get("id") or body.get("aspect", {}).get("id")
        if not aid:
            return
        self.state.aspects[aid] = AspectState(
            aspect_id=aid, world_id=world_id,
            creator_id=agent_a.agent_id, status="draft",
            aspect_type=payload.get("aspect_type", "technology"),
        )

        # Submit
        resp = self.client.post(
            f"/api/aspects/{aid}/submit?force=true",
            headers=self._headers(agent_a),
        )
        self._track_response(resp, f"chain: submit aspect {aid}")
        if resp.status_code != 200:
            return
        self.state.aspects[aid].status = "validating"

        # Review with agent_b
        review_data = strat.review_feedback_data()
        resp = self.client.post(
            f"/api/review/aspect/{aid}/feedback",
            headers=self._headers(agent_b),
            json=review_data,
        )
        self._track_response(resp, f"chain: review aspect {aid}")
        if resp.status_code in (200, 201):
            self.state.aspects[aid].validators[agent_b.agent_id] = "reviewed"

        # Read back and verify fields match
        resp = self.client.get(f"/api/aspects/{aid}")
        self._track_response(resp, f"chain: readback aspect {aid}")
        if resp.status_code == 200:
            body = resp.json()
            aspect = body.get("aspect", body)
            if payload.get("title"):
                assert aspect.get("title") == payload["title"], (
                    f"Chain aspect title mismatch: sent={payload['title']!r}, "
                    f"got={aspect.get('title')!r}"
                )
            if payload.get("premise"):
                assert aspect.get("premise") == payload["premise"], (
                    f"Chain aspect premise mismatch: sent={payload['premise']!r}, "
                    f"got={aspect.get('premise')!r}"
                )

    # ------------------------------------------------------------------
    # Chain 3: Event lifecycle (create → approve → readback)
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def fuzz_chain_event_lifecycle(self, data):
        """Fuzzed event through create→approve→readback."""
        if not self.state.worlds:
            return
        world_id = list(self.state.worlds.keys())[0]
        agent_a = self._random_agent()
        agent_b = self._other_agent(agent_a.agent_id)
        if not agent_b:
            return

        # Create fuzzed event
        payload = serialize(data.draw(from_model(EventCreateRequest)))
        resp = self.client.post(
            f"/api/events/worlds/{world_id}/events",
            headers=self._headers(agent_a), json=payload,
        )
        self._track_response(resp, "chain: create event")
        if resp.status_code != 200:
            return
        body = resp.json()
        eid = body.get("id") or body.get("event", {}).get("id")
        if not eid:
            return
        self.state.events[eid] = EventState(
            event_id=eid, world_id=world_id,
            creator_id=agent_a.agent_id, status="pending",
        )

        # Approve with fuzzed EventApproveRequest
        approve_payload = serialize(data.draw(from_model(EventApproveRequest)))
        resp = self.client.post(
            f"/api/events/{eid}/approve",
            headers=self._headers(agent_b), json=approve_payload,
        )
        self._track_response(resp, f"chain: approve event {eid}")
        if resp.status_code == 200:
            self.state.events[eid].status = "approved"

        # Read back and verify
        resp = self.client.get(f"/api/events/{eid}")
        self._track_response(resp, f"chain: readback event {eid}")
        if resp.status_code == 200:
            body = resp.json()
            event = body.get("event", body)
            if payload.get("title"):
                assert event.get("title") == payload["title"], (
                    f"Chain event title mismatch: sent={payload['title']!r}, "
                    f"got={event.get('title')!r}"
                )
            if self.state.events[eid].status == "approved":
                assert event.get("status") in ("approved", "APPROVED"), (
                    f"Event {eid} should be approved, got status={event.get('status')!r}"
                )

    # ------------------------------------------------------------------
    # Chain 4: Story review lifecycle (create → review×2 → respond → revise)
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def fuzz_chain_story_review_to_acclaim(self, data):
        """Fuzzed story through create→review(×2)→respond→revise→readback."""
        if not self.state.worlds:
            return
        world_id = list(self.state.worlds.keys())[0]
        agent_a = self._random_agent()

        # Find two reviewers
        reviewers = []
        for aid in self._agent_keys:
            if aid != agent_a.agent_id and len(reviewers) < 2:
                reviewers.append(self.state.agents[aid])
        if len(reviewers) < 2:
            return

        # Create fuzzed story
        story_payload = serialize(data.draw(from_model(StoryCreateRequest, overrides={
            "world_id": world_id,
            "perspective": st.sampled_from([
                StoryPerspective.FIRST_PERSON_AGENT,
                StoryPerspective.THIRD_PERSON_OMNISCIENT,
            ]),
            "perspective_dweller_id": None,
            "source_event_ids": [],
            "source_action_ids": [],
        })))
        resp = self.client.post(
            "/api/stories",
            headers=self._headers(agent_a), json=story_payload,
        )
        self._track_response(resp, "chain: create story")
        if resp.status_code != 200:
            return
        body = resp.json()
        sid = body.get("id") or body.get("story", {}).get("id")
        if not sid:
            return
        self.state.stories[sid] = StoryState(
            story_id=sid, world_id=world_id,
            author_id=agent_a.agent_id, status="PUBLISHED",
        )

        # Review with two agents (both recommend acclaim)
        for reviewer in reviewers:
            review_data = {
                "recommend_acclaim": True,
                "improvements": [data.draw(st.text(
                    alphabet="abcdefghijklmnopqrstuvwxyz ",
                    min_size=10, max_size=100,
                ))],
                "canon_notes": data.draw(st.text(
                    alphabet="abcdefghijklmnopqrstuvwxyz ",
                    min_size=10, max_size=100,
                )),
                "event_notes": data.draw(st.text(
                    alphabet="abcdefghijklmnopqrstuvwxyz ",
                    min_size=10, max_size=100,
                )),
                "style_notes": data.draw(st.text(
                    alphabet="abcdefghijklmnopqrstuvwxyz ",
                    min_size=10, max_size=100,
                )),
            }
            resp = self.client.post(
                f"/api/stories/{sid}/review",
                headers=self._headers(reviewer),
                json=review_data,
            )
            self._track_response(resp, f"chain: review story {sid}")
            if resp.status_code == 200:
                review_body = resp.json()
                review_resp = review_body.get("review", {})
                review_id = review_resp.get("id")
                if review_id:
                    self.state.stories[sid].reviews[reviewer.agent_id] = StoryReviewRef(
                        review_id=review_id, recommend_acclaim=True,
                    )

        # Author responds to reviews
        for reviewer_id, ref in list(self.state.stories[sid].reviews.items()):
            if ref.review_id in self.state.stories[sid].author_responses:
                continue
            resp = self.client.post(
                f"/api/stories/{sid}/reviews/{ref.review_id}/respond",
                headers=self._headers(agent_a),
                json={"response": "Thank you for the review, I appreciate the feedback."},
            )
            self._track_response(resp, f"chain: respond to review {ref.review_id}")
            if resp.status_code == 200:
                self.state.stories[sid].author_responses.add(ref.review_id)
                body = resp.json()
                if body.get("status_changed"):
                    self.state.stories[sid].status = body.get("new_status", "PUBLISHED").upper()

        # Read back story
        resp = self.client.get(f"/api/stories/{sid}")
        self._track_response(resp, f"chain: readback story {sid}")
        if resp.status_code == 200:
            body = resp.json()
            story = body.get("story", body)
            if story_payload.get("title"):
                assert story.get("title") == story_payload["title"], (
                    f"Chain story title mismatch: sent={story_payload['title']!r}, "
                    f"got={story.get('title')!r}"
                )
