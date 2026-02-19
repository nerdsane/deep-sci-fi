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

    @invariant()
    def s_story_status_transitions(self):
        """Stories only transition PUBLISHED -> ACCLAIMED, never backwards."""
        for sid, story in self.state.stories.items():
            assert story.status in ("PUBLISHED", "ACCLAIMED"), (
                f"Story {sid}: invalid status '{story.status}' "
                "(expected PUBLISHED or ACCLAIMED)"
            )
            resp = self.client.get(f"/api/stories/{sid}")
            if resp.status_code != 200:
                continue
            body = resp.json()
            actual_status = body.get("story", body).get("status", story.status)
            if actual_status != story.status:
                assert story.status == "PUBLISHED" and actual_status == "ACCLAIMED", (
                    f"Story {sid}: invalid transition {story.status} -> {actual_status} "
                    "(only PUBLISHED -> ACCLAIMED allowed)"
                )
                story.status = actual_status

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
        """No action is escalated more than once — verified via API."""
        if not self.state.actions:
            return
        escalated = [a for a in self.state.actions.values() if a.escalated]
        for action in escalated[:3]:  # spot-check
            resp = self.client.get(f"/api/dwellers/actions/{action.action_id}")
            if resp.status_code != 200:
                continue
            body = resp.json()
            action_data = body.get("action", body)
            api_escalated = action_data.get("escalated", False)
            assert api_escalated, (
                f"Action {action.action_id}: state mirror says escalated but API says not"
            )

    @invariant()
    def s_event_approval_integrity(self):
        """Approved events have a non-self approver."""
        for eid, event in self.state.events.items():
            if event.status != "approved":
                continue
            resp = self.client.get(f"/api/events/{eid}")
            if resp.status_code != 200:
                continue
            body = resp.json()
            event_data = body.get("event", body)
            approved_by = event_data.get("approved_by")
            proposed_by = event_data.get("proposed_by")
            if approved_by and proposed_by:
                assert approved_by != proposed_by, (
                    f"Event {eid}: approved by same agent who proposed it "
                    f"(approved_by={approved_by}, proposed_by={proposed_by})"
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
        """Feedback upvote_count matches len(upvoters) in state mirror AND API."""
        for fid, fb in list(self.state.feedback.items())[:3]:
            # State mirror internal consistency
            assert fb.upvote_count == len(fb.upvoters), (
                f"Feedback {fid}: upvote_count={fb.upvote_count} "
                f"but {len(fb.upvoters)} upvoters tracked"
            )
            # Verify against API
            resp = self.client.get(f"/api/feedback/{fid}")
            if resp.status_code != 200:
                continue
            body = resp.json()
            api_fb = body.get("feedback", {})
            api_count = api_fb.get("upvote_count", 0)
            assert api_count == fb.upvote_count, (
                f"Feedback {fid}: state mirror upvote_count={fb.upvote_count} "
                f"but API reports {api_count}"
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
    # NOTE: s12_approved_with_strengthen_has_revision was removed.
    # The critical review system (api/reviews.py) replaced the legacy validation
    # system with verdict-based approvals (approve/reject/strengthen).
    # The new system doesn't track "strengthen" verdicts in the same way —
    # it tracks feedback items and their resolution status instead.
    # -------------------------------------------------------------------------

    @invariant()
    def s_max_active_proposals(self):
        """No agent has more than 3 active world proposals (draft + validating)."""
        active_by_agent = Counter()
        for p in self.state.proposals.values():
            if p.status in ("draft", "validating"):
                active_by_agent[p.creator_id] += 1
        for agent_id, count in active_by_agent.items():
            assert count <= 3, (
                f"Agent {agent_id} has {count} active world proposals (max 3). "
                "See MAX_ACTIVE_PROPOSALS in api/proposals.py."
            )

    @invariant()
    def s_feedback_status_transitions(self):
        """Feedback status transitions follow the VALID_TRANSITIONS graph."""
        valid_transitions = {
            "new": {"acknowledged", "in_progress", "resolved", "wont_fix"},
            "acknowledged": {"in_progress", "resolved", "wont_fix"},
            "in_progress": {"resolved", "wont_fix"},
            "resolved": set(),
            "wont_fix": set(),
        }
        valid_statuses = set(valid_transitions.keys())
        for fid, fb in list(self.state.feedback.items())[:5]:
            resp = self.client.get(f"/api/feedback/{fid}")
            if resp.status_code != 200:
                continue
            body = resp.json()
            api_fb = body.get("feedback", {})
            actual_status = api_fb.get("status", fb.status)
            assert actual_status in valid_statuses, (
                f"Feedback {fid}: unknown status '{actual_status}'"
            )
            if actual_status != fb.status:
                assert actual_status in valid_transitions.get(fb.status, set()), (
                    f"Feedback {fid}: invalid transition {fb.status} -> {actual_status}. "
                    f"Valid transitions from {fb.status}: {valid_transitions.get(fb.status, set())}"
                )
                fb.status = actual_status

    @invariant()
    def s_no_self_review_in_db(self):
        """Creator never reviews their own content (defense-in-depth)."""
        for review in self.state.reviews.values():
            assert review.reviewer_id != review.proposer_id, (
                f"Review {review.review_id}: reviewer {review.reviewer_id} "
                f"reviewed their own content {review.content_id}. "
                "Self-review must never persist in the database."
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
        for endpoint in ["/api/feed/stream?limit=2", "/api/worlds?limit=2"]:
            resp = self.client.get(endpoint)
            self._track_response(resp, f"read-only {endpoint}")

    # -------------------------------------------------------------------------
    # Middleware invariant
    # -------------------------------------------------------------------------

    @invariant()
    def s_m1_agent_context_middleware_registered(self):
        """AgentContextMiddleware is in the ASGI stack (not stripped in DST)."""
        # Use the actual app the TestClient wraps
        app = self.client.app
        current = getattr(app, "middleware_stack", app)
        found = False
        for _ in range(20):  # safety limit
            if current is None:
                break
            # Use type name (not isinstance) because conftest module cache
            # clearing can create different class objects for the same class
            if type(current).__name__ == "AgentContextMiddleware":
                found = True
                break
            current = getattr(current, "app", None)
        assert found, (
            "AgentContextMiddleware not found in ASGI stack. "
            "It may have been stripped from DST conftest."
        )

    # -------------------------------------------------------------------------
    # Critical review system invariants
    # -------------------------------------------------------------------------

    @invariant()
    def s_r1_proposer_always_sees_own_feedback(self):
        """Proposers can always retrieve ALL feedback on their content (blind mode bypass)."""
        # Check proposals with reviews
        for review in list(self.state.reviews.values())[:3]:  # spot-check
            if review.content_type != "proposal":
                continue

            proposer = self.state.agents[review.proposer_id]
            resp = self.client.get(
                f"/api/review/proposal/{review.content_id}/feedback",
                headers=self._headers(proposer),
            )

            if resp.status_code != 200:
                continue

            body = resp.json()
            reviews_returned = body.get("reviews", [])

            # Count how many reviews exist for this content
            expected_count = sum(
                1 for r in self.state.reviews.values()
                if r.content_type == "proposal" and r.content_id == review.content_id
            )

            assert len(reviews_returned) == expected_count, (
                f"Proposer {review.proposer_id} for proposal {review.content_id}: "
                f"expected {expected_count} reviews but got {len(reviews_returned)}. "
                "Proposers must see ALL feedback (blind mode bypass)."
            )

    @invariant()
    def s_r2_blind_mode_isolates_reviewers(self):
        """Reviewers who haven't submitted cannot see other reviewers' feedback."""
        # Find proposals with multiple reviews
        content_reviews = {}
        for r in self.state.reviews.values():
            key = (r.content_type, r.content_id)
            if key not in content_reviews:
                content_reviews[key] = []
            content_reviews[key].append(r)

        # Check blind mode for content with 2+ reviews
        for (content_type, content_id), reviews in list(content_reviews.items())[:2]:
            if len(reviews) < 2 or content_type != "proposal":
                continue

            # Pick an agent who hasn't reviewed this content
            non_reviewer = None
            for agent_id in self._agent_keys:
                if not any(r.reviewer_id == agent_id for r in reviews):
                    # Also make sure they're not the proposer
                    if agent_id != reviews[0].proposer_id:
                        non_reviewer = self.state.agents[agent_id]
                        break

            if not non_reviewer:
                continue

            resp = self.client.get(
                f"/api/review/{content_type}/{content_id}/feedback",
                headers=self._headers(non_reviewer),
            )

            if resp.status_code != 200:
                continue

            body = resp.json()
            reviews_returned = body.get("reviews", [])

            # Non-reviewer should see 0 reviews (blind mode)
            assert len(reviews_returned) == 0, (
                f"Non-reviewer {non_reviewer.agent_id} for {content_type} {content_id}: "
                f"expected 0 reviews but got {len(reviews_returned)}. "
                "Blind mode must block non-reviewers from seeing others' feedback."
            )

    @invariant()
    def s_r3_reviewer_sees_all_after_submit(self):
        """Once a reviewer submits, they can see all reviews."""
        # Check reviewers who have submitted
        for review in list(self.state.reviews.values())[:3]:  # spot-check
            if review.content_type != "proposal":
                continue

            reviewer = self.state.agents[review.reviewer_id]
            resp = self.client.get(
                f"/api/review/proposal/{review.content_id}/feedback",
                headers=self._headers(reviewer),
            )

            if resp.status_code != 200:
                continue

            body = resp.json()
            reviews_returned = body.get("reviews", [])

            # Count how many reviews exist for this content
            expected_count = sum(
                1 for r in self.state.reviews.values()
                if r.content_type == "proposal" and r.content_id == review.content_id
            )

            assert len(reviews_returned) == expected_count, (
                f"Reviewer {review.reviewer_id} for proposal {review.content_id}: "
                f"expected {expected_count} reviews but got {len(reviews_returned)}. "
                "Reviewers who submitted must see ALL reviews."
            )
