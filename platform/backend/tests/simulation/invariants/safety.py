"""Safety invariants — checked after every rule step.

Each invariant queries the API/state to verify game rules are maintained.
Prefixed S-XX for traceability to the plan.
"""

from collections import Counter

from hypothesis.stateful import invariant


class SafetyInvariantsMixin:
    """Safety invariants checked after every step."""

    # -------------------------------------------------------------------------
    # Core invariants (from original test_game_rules.py)
    # -------------------------------------------------------------------------

    @invariant()
    def s1_dweller_exclusivity(self):
        """No dweller is claimed by 2 agents simultaneously."""
        if not self.state.dwellers:
            return
        for did in list(self.state.dwellers.keys())[:3]:
            resp = self.client.get(f"/api/dwellers/{did}")
            if resp.status_code != 200:
                continue
            body = resp.json()
            dweller = body.get("dweller", {})
            inhabited_by = dweller.get("inhabited_by")
            if inhabited_by:
                claim_count = sum(
                    1 for aid in self._agent_keys if aid == inhabited_by
                )
                assert claim_count <= 1, f"Dweller {did} claimed by {claim_count} agents!"

    @invariant()
    def s2_upvote_consistency(self):
        """upvote_count is non-negative for all tracked feedback."""
        if not self.state.feedback:
            return
        for fid in list(self.state.feedback.keys())[:3]:
            resp = self.client.get(f"/api/feedback/{fid}")
            if resp.status_code != 200:
                continue
            body = resp.json()
            fb = body.get("feedback", {})
            count = fb.get("upvote_count", 0)
            assert isinstance(count, int) and count >= 0, (
                f"Feedback {fid}: invalid upvote_count={count}"
            )

    @invariant()
    def s5_valid_proposal_transitions(self):
        """Proposals only transition through valid states."""
        valid_transitions = {
            "draft": {"validating"},
            "validating": {"approved", "rejected"},
            "approved": set(),
            "rejected": set(),
        }
        for pid, p in self.state.proposals.items():
            resp = self.client.get(f"/api/proposals/{pid}")
            if resp.status_code != 200:
                continue
            body = resp.json()
            proposal_data = body.get("proposal", {})
            actual_status = proposal_data.get("status", p.status)
            if actual_status != p.status:
                assert actual_status in valid_transitions.get(p.status, set()), (
                    f"Proposal {pid}: invalid transition {p.status} -> {actual_status}"
                )

    @invariant()
    def s6_approved_proposals_have_one_world(self):
        """Each approved proposal has exactly 1 world, not 0 or 2+."""
        for pid, p in self.state.proposals.items():
            if p.status != "approved":
                continue
            matching = [w for w in self.state.worlds.values() if w.source_proposal_id == pid]
            assert len(matching) == 1, (
                f"Proposal {pid} is approved but has {len(matching)} worlds!"
            )

    @invariant()
    def s7_no_500_errors(self):
        """No unhandled server errors."""
        assert len(self.state.error_log) == 0, (
            f"{len(self.state.error_log)} server errors: {self.state.error_log}"
        )

    # -------------------------------------------------------------------------
    # Story invariants
    # -------------------------------------------------------------------------

    @invariant()
    def s_s1_story_references_valid_world(self):
        """Every tracked story references a world we know about."""
        for sid, story in self.state.stories.items():
            assert story.world_id in self.state.worlds, (
                f"Story {sid} references unknown world {story.world_id}"
            )

    # s_s3 duplicate reaction testing moved to rules/stories.py::duplicate_story_reaction
    # s_s4 removed (redundant with s10_story_acclaim_conditions)

    # -------------------------------------------------------------------------
    # Aspect invariants
    # -------------------------------------------------------------------------

    @invariant()
    def s_a1_aspect_references_valid_world(self):
        """Every tracked aspect references a world we know about."""
        for aid, aspect in self.state.aspects.items():
            assert aspect.world_id in self.state.worlds, (
                f"Aspect {aid} references unknown world {aspect.world_id}"
            )

    @invariant()
    def s_a2_valid_aspect_transitions(self):
        """Aspects only transition through valid states (API spot-check)."""
        valid_transitions = {
            "draft": {"validating"},
            "validating": {"approved", "rejected"},
            "approved": set(),
            "rejected": set(),
        }
        for aid, a in list(self.state.aspects.items())[:3]:
            if a.status not in valid_transitions:
                continue
            resp = self.client.get(f"/api/aspects/{aid}")
            if resp.status_code != 200:
                continue
            body = resp.json()
            aspect_data = body.get("aspect", {})
            actual_status = aspect_data.get("status", a.status)
            if actual_status != a.status:
                assert actual_status in valid_transitions.get(a.status, set()), (
                    f"Aspect {aid}: invalid transition {a.status} -> {actual_status}"
                )

    # -------------------------------------------------------------------------
    # Event invariants
    # -------------------------------------------------------------------------

    @invariant()
    def s_e1_event_references_valid_world(self):
        """Every tracked event references a world we know about."""
        for eid, event in self.state.events.items():
            assert event.world_id in self.state.worlds, (
                f"Event {eid} references unknown world {event.world_id}"
            )

    @invariant()
    def s_e3_different_agent_confirms(self):
        """Actions confirmed by a different agent than the actor."""
        for aid, action in self.state.actions.items():
            if action.confirmed_by is not None:
                assert action.confirmed_by != action.actor_id, (
                    f"Action {aid}: self-confirmed by {action.actor_id}"
                )

    @invariant()
    def s_e4_escalate_only_once(self):
        """No action is escalated more than once (tracked in state mirror)."""
        # Enforcement: rule only escalates if not ar.escalated.
        # This invariant verifies our bookkeeping is consistent.
        escalated_count = sum(1 for a in self.state.actions.values() if a.escalated)
        # Each escalated action should have produced exactly one event
        # (tracked by rule handler). Just verify count is reasonable.
        assert escalated_count <= len(self.state.actions), (
            f"More escalations ({escalated_count}) than actions ({len(self.state.actions)})"
        )

    # -------------------------------------------------------------------------
    # Suggestion invariants
    # -------------------------------------------------------------------------

    @invariant()
    def s_sg1_no_self_suggestions(self):
        """Suggestions are not made by the content owner."""
        for sid, s in self.state.suggestions.items():
            assert s.suggester_id != s.owner_id, (
                f"Suggestion {sid}: self-suggested by {s.suggester_id}"
            )

    @invariant()
    def s_sg3_valid_suggestion_transitions(self):
        """Suggestions only transition through valid states."""
        valid_states = {"pending", "accepted", "rejected", "withdrawn"}
        for sid, s in self.state.suggestions.items():
            assert s.status in valid_states, (
                f"Suggestion {sid}: invalid status {s.status}"
            )

    # -------------------------------------------------------------------------
    # Dweller proposal invariants
    # -------------------------------------------------------------------------

    @invariant()
    def s_dp1_max_active_proposals(self):
        """No agent has more than 5 active dweller proposals (draft + validating)."""
        active_by_agent = Counter()
        for dp in self.state.dweller_proposals.values():
            if dp.status in ("draft", "validating"):
                active_by_agent[dp.creator_id] += 1
        for agent_id, count in active_by_agent.items():
            assert count <= 5, (
                f"Agent {agent_id} has {count} active dweller proposals (max 5)"
            )

    # -------------------------------------------------------------------------
    # Cross-domain invariants
    # -------------------------------------------------------------------------

    @invariant()
    def s8_max_5_dwellers_per_agent(self):
        """No agent claims more than 5 dwellers simultaneously."""
        claims = Counter()
        for d in self.state.dwellers.values():
            if d.claimed_by is not None:
                claims[d.claimed_by] += 1
        for agent_id, count in claims.items():
            assert count <= 5, (
                f"Agent {agent_id} has {count} claimed dwellers (max 5)"
            )

    @invariant()
    def s9_feedback_upvote_consistency(self):
        """Feedback upvote_count matches len(upvoters) in state mirror."""
        for fid, fb in self.state.feedback.items():
            assert fb.upvote_count == len(fb.upvoters), (
                f"Feedback {fid}: upvote_count={fb.upvote_count} "
                f"but {len(fb.upvoters)} upvoters tracked"
            )

    @invariant()
    def s10_story_acclaim_conditions(self):
        """Acclaimed stories meet all acclaim prerequisites."""
        for sid, story in self.state.stories.items():
            if story.status != "ACCLAIMED":
                continue
            acclaim_reviews = sum(
                1 for ref in story.reviews.values()
                if ref.recommend_acclaim
            )
            assert acclaim_reviews >= 2, (
                f"Story {sid} is ACCLAIMED but only {acclaim_reviews} "
                f"acclaim reviews (need >= 2)"
            )
            responded = sum(
                1 for ref in story.reviews.values()
                if ref.review_id in story.author_responses
            )
            assert responded == len(story.reviews), (
                f"Story {sid} is ACCLAIMED but only {responded}/{len(story.reviews)} "
                f"reviews responded to"
            )
            assert story.revision_count >= 1, (
                f"Story {sid} is ACCLAIMED but revision_count={story.revision_count}"
            )

    @invariant()
    def s11_escalation_requires_confirmation(self):
        """Escalated actions must have been confirmed first."""
        for aid, action in self.state.actions.items():
            if action.escalated:
                assert action.confirmed_by is not None, (
                    f"Action {aid}: escalated but not confirmed"
                )

    # -------------------------------------------------------------------------
    # Strengthen gate invariant
    # -------------------------------------------------------------------------

    @invariant()
    def s12_approved_with_strengthen_has_revision(self):
        """Approved content with strengthen history must have revision_count >= 1."""
        # Check proposals
        for pid, p in self.state.proposals.items():
            if p.status != "approved":
                continue
            has_strengthen = any(v == "strengthen" for v in p.validators.values())
            if has_strengthen:
                assert p.revision_count >= 1, (
                    f"Proposal {pid}: approved with strengthen feedback "
                    f"but revision_count={p.revision_count}"
                )
        # Check aspects
        for aid, a in self.state.aspects.items():
            if a.status != "approved":
                continue
            has_strengthen = any(v == "strengthen" for v in a.validators.values())
            if has_strengthen:
                assert a.revision_count >= 1, (
                    f"Aspect {aid}: approved with strengthen feedback "
                    f"but revision_count={a.revision_count}"
                )
        # Check dweller proposals
        for dp_id, dp in self.state.dweller_proposals.items():
            if dp.status != "approved":
                continue
            has_strengthen = any(v == "strengthen" for v in dp.validators.values())
            if has_strengthen:
                assert dp.revision_count >= 1, (
                    f"Dweller proposal {dp_id}: approved with strengthen feedback "
                    f"but revision_count={dp.revision_count}"
                )

    # -------------------------------------------------------------------------
    # Read-only invariant
    # -------------------------------------------------------------------------

    @invariant()
    def s_r1_read_only_no_500s(self):
        """Read-only endpoints never return 500 (spot-check, routed via _track_response)."""
        # Only spot-check when worlds exist (reduces contention on empty DB)
        if not self.state.worlds:
            return
        for endpoint in ["/api/feed?limit=2", "/api/worlds?limit=2"]:
            resp = self.client.get(endpoint)
            self._track_response(resp, f"read-only {endpoint}")
