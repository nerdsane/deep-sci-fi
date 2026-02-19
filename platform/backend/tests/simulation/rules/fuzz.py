"""Pydantic-driven fuzz rules mixin.

Extracted from test_game_rules_with_fuzzing.py so both the fuzzing tier
and the combined fuzz+fault tier can reuse these rules without diamond
inheritance.

Each rule draws data from Pydantic request models via Hypothesis,
exercising boundary values, all enum variants, and edge cases.

Phase 3 additions:
- Read-back verification: after successful creation, GET the entity and
  verify stored fields match sent data.
- Tighter assertions: schema-valid data with valid context should return
  200 or a specific documented 4xx (409, 422, 429, 403), not a generic 400.
"""

from hypothesis.stateful import rule
import hypothesis.strategies as st

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

# Known acceptable non-200 status codes for fuzz creation rules.
# 409: conflict (duplicate name), 422: Pydantic cross-field validation,
# 429: rate limit (max active proposals, dedup window), 403: auth edge case.
# 400 intentionally excluded: schema-valid data from Pydantic strategies
# should trigger specific error codes, not generic 400. If a 400 appears,
# either the API needs a more specific code or the strategy overrides need
# to provide more contextually valid data.
_ACCEPTABLE_4XX = (403, 409, 422, 429)


class FuzzRulesMixin:
    """Pydantic-driven fuzz rules that interleave with deterministic rules.

    Catches bugs from diverse data that fixed generators never produce
    (boundary years, max-length strings, all enum variants).
    """

    # ------------------------------------------------------------------
    # Fuzz rule: Create proposal with diverse data
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def fuzz_create_proposal(self, data):
        """Create proposal with fuzzed field values."""
        agent = self._random_agent()
        payload = data.draw(from_model(ProposalCreateRequest))
        serialized = serialize(payload)
        resp = self.client.post(
            "/api/proposals",
            headers=self._headers(agent),
            json=serialized,
        )
        self._track_response(resp, "fuzz create proposal")
        if resp.status_code >= 400:
            assert resp.status_code in _ACCEPTABLE_4XX, (
                f"Fuzz proposal got unexpected {resp.status_code} "
                f"(expected 200 or {_ACCEPTABLE_4XX}): {resp.text[:300]}"
            )
        if resp.status_code == 200:
            body = resp.json()
            pid = body["id"]
            self.state.proposals[pid] = ProposalState(
                proposal_id=pid,
                creator_id=agent.agent_id,
                status="draft",
            )
            self._verify_readback(
                f"/api/proposals/{pid}",
                serialized,
                {"proposal.name": "name", "proposal.premise": "premise",
                 "proposal.year_setting": "year_setting"},
            )

    # ------------------------------------------------------------------
    # Fuzz rule: Create feedback with diverse data
    # ------------------------------------------------------------------
    @rule(data=st.data())
    def fuzz_create_feedback(self, data):
        """Create feedback with fuzzed category, priority, and text fields."""
        agent = self._random_agent()
        payload = data.draw(from_model(FeedbackCreateRequest))
        serialized = serialize(payload)
        resp = self.client.post(
            "/api/feedback",
            headers=self._headers(agent),
            json=serialized,
        )
        self._track_response(resp, "fuzz create feedback")
        if resp.status_code >= 400:
            assert resp.status_code in _ACCEPTABLE_4XX, (
                f"Fuzz feedback got unexpected {resp.status_code} "
                f"(expected 200 or {_ACCEPTABLE_4XX}): {resp.text[:300]}"
            )
        if resp.status_code in (200, 201):
            body = resp.json()
            fid = body.get("id") or body.get("feedback", {}).get("id")
            if fid:
                self.state.feedback[fid] = FeedbackState(
                    feedback_id=fid,
                    creator_id=agent.agent_id,
                )
                self._verify_readback(
                    f"/api/feedback/{fid}",
                    serialized,
                    {"feedback.title": "title", "feedback.description": "description",
                     "feedback.category": "category", "feedback.priority": "priority"},
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
        serialized = serialize(payload)
        resp = self.client.post(
            f"/api/dwellers/worlds/{world_id}/regions",
            headers=self._headers(agent),
            json=serialized,
        )
        self._track_response(resp, "fuzz add region")
        if resp.status_code >= 400:
            assert resp.status_code in _ACCEPTABLE_4XX, (
                f"Fuzz region got unexpected {resp.status_code} "
                f"(expected 200 or {_ACCEPTABLE_4XX}): {resp.text[:300]}"
            )
        if resp.status_code == 200:
            body = resp.json()
            region = body.get("region", {})
            region_name = region.get("name") or serialized.get("name")
            # Inline read-back: verify POST response matches sent name
            if region.get("name") and serialized.get("name"):
                assert region["name"] == serialized["name"], (
                    f"Region read-back mismatch: sent name={serialized['name']!r}, "
                    f"got {region['name']!r}"
                )
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
        serialized = serialize(payload)
        resp = self.client.post(
            f"/api/dwellers/worlds/{world_id}/dwellers",
            headers=self._headers(agent),
            json=serialized,
        )
        self._track_response(resp, "fuzz create dweller")
        if resp.status_code >= 400:
            assert resp.status_code in _ACCEPTABLE_4XX, (
                f"Fuzz dweller got unexpected {resp.status_code} "
                f"(expected 200 or {_ACCEPTABLE_4XX}): {resp.text[:300]}"
            )
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
                self._verify_readback(
                    f"/api/dwellers/{did}",
                    serialized,
                    {"dweller.name": "name", "dweller.origin_region": "origin_region",
                     "dweller.role": "role", "dweller.age": "age"},
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
        serialized = serialize(payload)
        resp = self.client.post(
            "/api/stories",
            headers=self._headers(agent),
            json=serialized,
        )
        self._track_response(resp, "fuzz create story")
        if resp.status_code >= 400:
            assert resp.status_code in _ACCEPTABLE_4XX, (
                f"Fuzz story got unexpected {resp.status_code} "
                f"(expected 200 or {_ACCEPTABLE_4XX}): {resp.text[:300]}"
            )
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
                self._verify_readback(
                    f"/api/stories/{sid}",
                    serialized,
                    {"story.title": "title", "story.perspective": "perspective"},
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
        serialized = serialize(payload)
        resp = self.client.post(
            f"/api/aspects/worlds/{world_id}/aspects",
            headers=self._headers(agent),
            json=serialized,
        )
        self._track_response(resp, "fuzz create aspect")
        if resp.status_code >= 400:
            assert resp.status_code in _ACCEPTABLE_4XX, (
                f"Fuzz aspect got unexpected {resp.status_code} "
                f"(expected 200 or {_ACCEPTABLE_4XX}): {resp.text[:300]}"
            )
        if resp.status_code == 200:
            body = resp.json()
            aid = body.get("id") or body.get("aspect", {}).get("id")
            if aid:
                self.state.aspects[aid] = AspectState(
                    aspect_id=aid,
                    world_id=world_id,
                    creator_id=agent.agent_id,
                    status="draft",
                    aspect_type=serialized.get("aspect_type", "technology"),
                )
                self._verify_readback(
                    f"/api/aspects/{aid}",
                    serialized,
                    {"aspect.title": "title", "aspect.premise": "premise",
                     "aspect.type": "aspect_type"},
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
        serialized = serialize(payload)
        resp = self.client.post(
            f"/api/events/worlds/{world_id}/events",
            headers=self._headers(agent),
            json=serialized,
        )
        self._track_response(resp, "fuzz create event")
        if resp.status_code >= 400:
            assert resp.status_code in _ACCEPTABLE_4XX, (
                f"Fuzz event got unexpected {resp.status_code} "
                f"(expected 200 or {_ACCEPTABLE_4XX}): {resp.text[:300]}"
            )
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
                self._verify_readback(
                    f"/api/events/{eid}",
                    serialized,
                    {"event.title": "title", "event.description": "description",
                     "event.year_in_world": "year_in_world"},
                )

    # ------------------------------------------------------------------
    # Fuzz rule: Submit review with diverse feedback items
    # (Keep < 500 — operates on existing entities, state-dependent 400s expected)
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
    # (Keep < 500 — state-dependent 400s expected)
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
    # (Keep < 500 — state-dependent 400s expected)
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
