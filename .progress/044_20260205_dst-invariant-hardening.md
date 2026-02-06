# DST Invariant Hardening

## Status: COMPLETE

## Goal
Tighten DST from ~40-50% business rule coverage to ~80%+ by filling stubs, adding invariants, adding error-path rules, and fixing state tracking bugs.

## Phases
- [x] Phase 1: State mirror enrichment + bug fixes
  - Added `StoryReviewRef` dataclass (review_id + recommend_acclaim)
  - Enriched `FeedbackState` with `upvote_count` + `upvoters`
  - Fixed `review_story` to wrap in StoryReviewRef
  - Fixed `respond_to_review` to destructure StoryReviewRef
  - Fixed `upvote_feedback` to track upvoters/count
- [x] Phase 2: Fill 3 stub invariants
  - S_S3: Duplicate reaction spot-check (was `pass`)
  - S_A2: Aspect transition API spot-check (was empty loop)
  - S_R1: Read-only endpoint 500 check (was `pass`)
- [x] Phase 3: New safety (S8-S11) + liveness (L5-L6) invariants
  - S8: Max 5 dwellers per agent
  - S9: Feedback upvote consistency (count == len(upvoters))
  - S10: Story acclaim conditions (2+ acclaim reviews, all responded, revised)
  - S11: Escalation requires confirmation
  - L5: Rejected proposals have 2+ rejection votes
  - L6: Escalated actions <= events count
- [x] Phase 4: 10 new error-path rules
  - proposals: reject_proposal, self_validate_proposal
  - aspects: reject_aspect, self_validate_aspect
  - stories: self_review_story, review_story_no_acclaim
  - feedback: self_upvote_feedback
  - dwellers: claim_sixth_dweller
  - actions: self_confirm_action, escalate_unconfirmed_action
- [x] Phase 5: Verify all seeds pass

## Test Results
- test_game_rules: seeds 0-12 all PASS
- test_game_rules_with_faults: seeds 0-10 all PASS

## Files Modified (9 total)
- tests/simulation/state_mirror.py
- tests/simulation/rules/stories.py
- tests/simulation/rules/feedback.py
- tests/simulation/rules/proposals.py
- tests/simulation/rules/aspects.py
- tests/simulation/rules/dwellers.py
- tests/simulation/rules/actions.py
- tests/simulation/invariants/safety.py
- tests/simulation/invariants/liveness.py

## Linter Improvements (auto-applied)
- s_s3 moved from invariant to rule (`duplicate_story_reaction`) — runs as rule instead of every step
- s_s4 removed (redundant with stronger s10)
- `Counter` import hoisted to module level
- Net: 19 safety invariants (down from 21 planned, but test coverage is equivalent)

## Tally
- 1 stub invariant filled (s_a2), 1 improved (s_r1), 1 moved to rule (s_s3)
- 4 new safety invariants (S8-S11)
- 2 new liveness invariants (L5-L6)
- 11 new rules (10 error-path + 1 duplicate_story_reaction)
- 2 real bugs fixed (StoryReviewRef wrapping, upvote tracking)
