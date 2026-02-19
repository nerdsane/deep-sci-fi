"""Pydantic-driven property-based fuzz testing layer on top of core DST.

Inherits all rules + invariants from DeepSciFiGameRules. Adds ~10 fuzz rules
that draw data from Pydantic request models via Hypothesis, exercising:
- Boundary values (min/max length strings, ge/le integers)
- All enum variants (not just the 1 value deterministic generators pick)
- Optional field diversity (sometimes None, sometimes populated)
- Nested model variation (diverse causal chains, feedback items, etc.)

The key signal: `assert resp.status_code < 500`. Validation errors (4xx) are
expected and fine — they prove the API rejects bad input gracefully. Server
errors (5xx) are bugs.

State tracking on success keeps invariants working: fuzzed entities that pass
validation get tracked just like deterministic ones.
"""

from hypothesis import settings, HealthCheck
from hypothesis.stateful import rule
import hypothesis.strategies as st

from tests.simulation.test_game_rules import DeepSciFiGameRules
from tests.simulation.state_mirror import (
    ProposalState,
    FeedbackState,
    StoryState,
    AspectState,
    EventState,
    ReviewState,
    FeedbackItemRef,
)
from tests.simulation.pydantic_strategies import from_model, serialize

# Import Pydantic request models from API modules
from api.proposals import (
    ProposalCreateRequest,
    ProposalReviseRequest,
    ValidationCreateRequest,
)
from api.feedback import FeedbackCreateRequest
from api.dwellers import RegionCreateRequest, DwellerCreateRequest
from api.stories import StoryCreateRequest
from api.aspects import AspectCreateRequest
from api.events import EventCreateRequest
from api.reviews import SubmitReviewRequest

# Import enums for overrides
from db.models import StoryPerspective


class FuzzedGameRules(DeepSciFiGameRules):
    """Extended state machine with Pydantic-driven fuzz rules.

    Inherits ALL existing rules + invariants. Fuzz rules interleave with
    deterministic rules, catching bugs from diverse data that fixed generators
    never produce (boundary years, max-length strings, all enum variants).
    """

    # ------------------------------------------------------------------
    # Fuzz rule: Create proposal with diverse data
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def fuzz_create_proposal(self, data):
        """Create proposal with fuzzed field values."""
        agent = self._random_agent()
        payload = data.draw(from_model(ProposalCreateRequest))
        resp = self.client.post(
            "/api/proposals",
            headers=self._headers(agent),
            json=serialize(payload),
        )
        self._track_response(resp, "fuzz create proposal")
        assert resp.status_code < 500, f"Server error on fuzz proposal: {resp.text[:300]}"
        if resp.status_code == 200:
            body = resp.json()
            pid = body["id"]
            self.state.proposals[pid] = ProposalState(
                proposal_id=pid,
                creator_id=agent.agent_id,
                status="draft",
            )

    # ------------------------------------------------------------------
    # Fuzz rule: Create feedback with diverse data
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def fuzz_create_feedback(self, data):
        """Create feedback with fuzzed category, priority, and text fields."""
        agent = self._random_agent()
        payload = data.draw(from_model(FeedbackCreateRequest))
        resp = self.client.post(
            "/api/feedback",
            headers=self._headers(agent),
            json=serialize(payload),
        )
        self._track_response(resp, "fuzz create feedback")
        assert resp.status_code < 500, f"Server error on fuzz feedback: {resp.text[:300]}"
        if resp.status_code in (200, 201):
            body = resp.json()
            fid = body.get("id") or body.get("feedback", {}).get("id")
            if fid:
                self.state.feedback[fid] = FeedbackState(
                    feedback_id=fid,
                    creator_id=agent.agent_id,
                )

    # ------------------------------------------------------------------
    # Fuzz rule: Add region with diverse data
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def fuzz_add_region(self, data):
        """Add region with fuzzed naming conventions, cultural blend, etc."""
        if not self.state.worlds:
            return
        world_id = list(self.state.worlds.keys())[0]
        agent = self._random_agent()
        payload = data.draw(from_model(RegionCreateRequest))
        resp = self.client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers=self._headers(agent),
            json=serialize(payload),
        )
        self._track_response(resp, "fuzz add region")
        assert resp.status_code < 500, f"Server error on fuzz region: {resp.text[:300]}"
        if resp.status_code == 200:
            body = resp.json()
            region_name = body.get("region", {}).get("name") or payload.get("name")
            if region_name:
                world = self.state.worlds[world_id]
                if region_name not in world.regions:
                    world.regions.append(region_name)

    # ------------------------------------------------------------------
    # Fuzz rule: Create dweller with diverse data
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def fuzz_create_dweller(self, data):
        """Create dweller with fuzzed age, personality, background, etc."""
        # Need a world with regions
        worlds_with_regions = [
            (wid, w) for wid, w in self.state.worlds.items() if w.regions
        ]
        if not worlds_with_regions:
            return
        world_id, world = worlds_with_regions[0]
        region = world.regions[0]
        agent = self._random_agent()

        # Override region fields with valid values from state
        payload = data.draw(from_model(DwellerCreateRequest, overrides={
            "origin_region": region,
            "current_region": st.sampled_from([region, None]),
        }))
        resp = self.client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers=self._headers(agent),
            json=serialize(payload),
        )
        self._track_response(resp, "fuzz create dweller")
        assert resp.status_code < 500, f"Server error on fuzz dweller: {resp.text[:300]}"
        if resp.status_code == 200:
            body = resp.json()
            dweller = body.get("dweller", {})
            did = dweller.get("id")
            if did:
                from tests.simulation.state_mirror import DwellerState
                self.state.dwellers[did] = DwellerState(
                    dweller_id=did,
                    world_id=world_id,
                    origin_region=region,
                )

    # ------------------------------------------------------------------
    # Fuzz rule: Create story with diverse data
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def fuzz_create_story(self, data):
        """Create story with fuzzed content, title, and video prompt."""
        if not self.state.worlds:
            return
        world_id = list(self.state.worlds.keys())[0]
        agent = self._random_agent()

        # Use safe perspectives that don't require a dweller_id
        safe_perspectives = [
            StoryPerspective.FIRST_PERSON_AGENT,
            StoryPerspective.THIRD_PERSON_OMNISCIENT,
        ]
        payload = data.draw(from_model(StoryCreateRequest, overrides={
            "world_id": world_id,
            "perspective": st.sampled_from(safe_perspectives),
            "perspective_dweller_id": None,
            "source_event_ids": [],
            "source_action_ids": [],
        }))
        resp = self.client.post(
            "/api/stories",
            headers=self._headers(agent),
            json=serialize(payload),
        )
        self._track_response(resp, "fuzz create story")
        assert resp.status_code < 500, f"Server error on fuzz story: {resp.text[:300]}"
        if resp.status_code == 200:
            body = resp.json()
            sid = body.get("id") or body.get("story", {}).get("id")
            if sid:
                self.state.stories[sid] = StoryState(
                    story_id=sid,
                    world_id=world_id,
                    author_id=agent.agent_id,
                    status="PUBLISHED",
                )

    # ------------------------------------------------------------------
    # Fuzz rule: Create aspect with diverse data
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def fuzz_create_aspect(self, data):
        """Create aspect with fuzzed type, title, premise, and justification."""
        if not self.state.worlds:
            return
        world_id = list(self.state.worlds.keys())[0]
        agent = self._random_agent()

        payload = data.draw(from_model(AspectCreateRequest, overrides={
            "content": {"description": "Fuzzed aspect content for testing"},
            "inspired_by_actions": [],
            "proposed_timeline_entry": None,
        }))
        resp = self.client.post(
            f"/api/aspects/worlds/{world_id}/aspects",
            headers=self._headers(agent),
            json=serialize(payload),
        )
        self._track_response(resp, "fuzz create aspect")
        assert resp.status_code < 500, f"Server error on fuzz aspect: {resp.text[:300]}"
        if resp.status_code == 200:
            body = resp.json()
            aid = body.get("id") or body.get("aspect", {}).get("id")
            if aid:
                self.state.aspects[aid] = AspectState(
                    aspect_id=aid,
                    world_id=world_id,
                    creator_id=agent.agent_id,
                    status="draft",
                    aspect_type=payload.get("aspect_type", "technology"),
                )

    # ------------------------------------------------------------------
    # Fuzz rule: Create event with diverse data
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def fuzz_create_event(self, data):
        """Create event with fuzzed year, title, description."""
        if not self.state.worlds:
            return
        world_id = list(self.state.worlds.keys())[0]
        agent = self._random_agent()

        payload = data.draw(from_model(EventCreateRequest))
        resp = self.client.post(
            f"/api/events/worlds/{world_id}/events",
            headers=self._headers(agent),
            json=serialize(payload),
        )
        self._track_response(resp, "fuzz create event")
        assert resp.status_code < 500, f"Server error on fuzz event: {resp.text[:300]}"
        if resp.status_code == 200:
            body = resp.json()
            eid = body.get("id") or body.get("event", {}).get("id")
            if eid:
                self.state.events[eid] = EventState(
                    event_id=eid,
                    world_id=world_id,
                    creator_id=agent.agent_id,
                    status="pending",
                )

    # ------------------------------------------------------------------
    # Fuzz rule: Submit review with diverse feedback items
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def fuzz_submit_review(self, data):
        """Submit review with fuzzed feedback items (categories, severities)."""
        # Need a validating proposal under critical_review system
        validating = [
            p for p in self.state.proposals.values()
            if p.status == "validating"
        ]
        if not validating:
            return
        proposal = validating[0]

        # Find an agent who hasn't reviewed yet and isn't the creator
        reviewer_id = None
        for aid in self._agent_keys:
            if aid != proposal.creator_id and aid not in proposal.validators:
                reviewer_id = aid
                break
        if not reviewer_id:
            return

        agent = self.state.agents[reviewer_id]
        payload = data.draw(from_model(SubmitReviewRequest))

        resp = self.client.post(
            f"/api/review/proposal/{proposal.proposal_id}/feedback",
            headers=self._headers(agent),
            json=serialize(payload),
        )
        self._track_response(resp, f"fuzz review proposal {proposal.proposal_id}")
        assert resp.status_code < 500, f"Server error on fuzz review: {resp.text[:300]}"
        if resp.status_code in (200, 201):
            proposal.validators[reviewer_id] = "reviewed"
            body = resp.json()
            review_id = body.get("review_id") or body.get("review", {}).get("id")
            if review_id:
                items = {}
                for item in body.get("review", {}).get("items", []):
                    item_id = item.get("id")
                    if item_id:
                        items[item_id] = FeedbackItemRef(
                            item_id=item_id,
                            category=item.get("category", "other"),
                            severity=item.get("severity", "minor"),
                            status="open",
                        )
                self.state.reviews[review_id] = ReviewState(
                    review_id=review_id,
                    content_type="proposal",
                    content_id=proposal.proposal_id,
                    reviewer_id=reviewer_id,
                    proposer_id=proposal.creator_id,
                    items=items,
                )

    # ------------------------------------------------------------------
    # Fuzz rule: Validate proposal with diverse verdicts
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def fuzz_validate_proposal(self, data):
        """Validate proposal with fuzzed verdict, critique, research."""
        validating = [
            p for p in self.state.proposals.values()
            if p.status == "validating"
        ]
        if not validating:
            return
        proposal = validating[0]

        # Find non-creator agent who hasn't validated
        validator_id = None
        for aid in self._agent_keys:
            if aid != proposal.creator_id and aid not in proposal.validators:
                validator_id = aid
                break
        if not validator_id:
            return

        agent = self.state.agents[validator_id]
        payload = data.draw(from_model(ValidationCreateRequest))

        resp = self.client.post(
            f"/api/proposals/{proposal.proposal_id}/validate",
            headers=self._headers(agent),
            json=serialize(payload),
        )
        self._track_response(resp, f"fuzz validate proposal {proposal.proposal_id}")
        assert resp.status_code < 500, f"Server error on fuzz validate: {resp.text[:300]}"
        if resp.status_code == 200:
            body = resp.json()
            verdict = body.get("verdict") or payload.get("verdict")
            if isinstance(verdict, str):
                proposal.validators[validator_id] = verdict
            else:
                proposal.validators[validator_id] = verdict.value if hasattr(verdict, "value") else str(verdict)

    # ------------------------------------------------------------------
    # Fuzz rule: Revise proposal with diverse partial updates
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def fuzz_revise_proposal(self, data):
        """Revise proposal with fuzzed partial updates."""
        drafts_or_validating = [
            p for p in self.state.proposals.values()
            if p.status in ("draft", "validating")
        ]
        if not drafts_or_validating:
            return
        proposal = drafts_or_validating[0]
        agent = self.state.agents[proposal.creator_id]

        payload = data.draw(from_model(ProposalReviseRequest))
        # Filter out None values so we only send actual updates
        filtered = {k: v for k, v in serialize(payload).items() if v is not None}
        if not filtered:
            return

        resp = self.client.post(
            f"/api/proposals/{proposal.proposal_id}/revise",
            headers=self._headers(agent),
            json=filtered,
        )
        self._track_response(resp, f"fuzz revise proposal {proposal.proposal_id}")
        assert resp.status_code < 500, f"Server error on fuzz revise: {resp.text[:300]}"
        if resp.status_code == 200:
            proposal.revision_count += 1


# Run the state machine
TestGameRulesWithFuzzing = FuzzedGameRules.TestCase
TestGameRulesWithFuzzing.settings = settings(
    max_examples=30,
    stateful_step_count=20,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)
