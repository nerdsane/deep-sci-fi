# DevOps & Quality Harness Implementation

**Date:** 2026-02-04
**Status:** IN PROGRESS (Phase 0 complete, Phase 2.2 complete, Phase 1 next)
**Paper:** docs/papers/deterministic-simulation-testing.md

---

## Phase 0: Foundation ✅

### Task 0.1: Install Logfire MCP ✅
- [x] Created `~/.local/bin/logfire-mcp-project` wrapper for per-project tokens
- [x] Created `.claude/logfire-token.example` template
- [x] Added `.claude/logfire-token` to `.gitignore`
- [x] CLAUDE.md directive added (in Post-Deploy Verification section)
- [x] Updated `.claude/logfire-token` with new read token
- [x] Created `.mcp.json` with logfire MCP server config (gitignored — machine-specific paths)
- [ ] Verify with `find_exceptions(60)` query (requires session restart)

### Task 0.2: Create Post-Push Verification Hook ✅
- [x] Created `.claude/hooks/post-push-verify.sh`
  - Detects `git push` in Bash tool_input.command via jq
  - Creates `/tmp/claude-deepsci/push-pending` marker
  - Returns additionalContext mandating verification steps
- [x] Added to `.claude/settings.json` as PostToolUse hook on Bash matcher

### Task 0.3: Create Stop Hook for Deploy Verification ✅
- [x] Created `.claude/hooks/stop-verify-deploy.sh`
  - Checks for push-pending marker
  - If push happened but deploy-verified marker missing, blocks stop
  - Returns `{ "decision": "block", "reason": "..." }`
- [x] Added to `.claude/settings.json` as Stop hook

### Task 0.4: Update CLAUDE.md ✅
- [x] Added "Post-Deploy Verification (MANDATORY)" section
- [x] Documented: verify-deployment workflow (CI → smoke → Logfire)
- [x] Referenced hooks as enforcement mechanism
- [x] Included manual verification fallback commands

### Task 0.5: Fix CI continue-on-error ✅
- [x] Removed `continue-on-error: true` from all 6 critical steps in review.yml
- [x] Replaced aggregation step with simple "All Checks Passed" confirmation
- [x] Each step now fails fast — PR is blocked on any check failure

### Task 0.6: Create verify-deployment.sh ✅
- [x] Created `scripts/verify-deployment.sh` with 4 verification steps
- [x] Supports staging/production/local environments
- [x] Creates `/tmp/claude-deepsci/deploy-verified` marker on success
- [x] Integrated with post-push hook coordination

---

## Phase 1: Deterministic Simulation Testing

### Task 1.1: Core State Machine (Game Rules)
- [ ] Create `platform/backend/tests/simulation/` directory
- [ ] Create `conftest.py` with async test client fixture
- [ ] Create `test_game_rules.py` with RuleBasedStateMachine:
  - Rules: register_agent, create_proposal, submit_proposal, validate_proposal, create_dweller, claim_dweller, take_action, submit_feedback, upvote_feedback
  - Invariants:
    - Proposal status transitions are valid
    - Dwellers have at most one claimant
    - Upvote count == len(upvoters)
    - No self-upvotes exist
    - No double-upvotes exist
    - Terminal feedback states can't transition
    - No 500 errors in any response

### Task 1.2: Fault Injection Layer
- [ ] Create `test_game_rules_with_faults.py` extending the core SM:
  - Rule: inject_concurrent_claim (asyncio.gather two claims)
  - Rule: inject_duplicate_request (replay last request)
  - Rule: inject_db_timeout (monkey-patch session.execute)
  - Same invariants must hold under faults

### Task 1.3: CI Integration
- [ ] Add DST to review.yml as a separate job
- [ ] Run with `--hypothesis-seed` range (200 seeds)
- [ ] Save hypothesis database as artifact for reproduction
- [ ] Block PR on invariant violation

### Task 1.4: Slop-Slayer Custom Detectors
- [ ] Create DeepSciFi-specific detectors using repl_load + repl_exec:
  - Detector: every endpoint that serializes a relationship uses selectinload()
  - Detector: every error response uses agent_error() helper
  - Detector: no raw SQL with table names (must use ORM)
  - Detector: all enum values in migrations are UPPERCASE
- [ ] Run slop_full_audit to establish baseline
- [ ] Export baseline to docs/slop/

---

## Phase 2: Automation

### Task 2.1: Post-Deploy Smoke in CI
- [ ] Add smoke-test.sh as GitHub Actions job after deploy
- [ ] Wait for Railway deploy to complete (poll health endpoint)
- [ ] Run smoke test against deployed URL
- [ ] Send Slack notification on result (informational)

### Task 2.2: claude-code-action for Feedback Triage ✅
- [x] Created `.github/workflows/feedback-triage.yml`
  - Scheduled daily at 9am UTC + workflow_dispatch
  - Fetches feedback summary + open items from production API
  - Early exits if no open feedback
  - Claude triages: groups by root cause, prioritizes by severity + upvotes
  - Creates GitHub Issue with label `feedback-triage`
- [x] Created `.github/workflows/feedback-fix.yml`
  - Triggered by `approved-fix` label on issues
  - Claude reads triage issue, implements highest-priority fix
  - Runs tests, creates PR referencing the triage issue
  - Comments on issue with results
- [ ] Prerequisite: `ANTHROPIC_API_KEY` must be added to GitHub repo secrets

### Task 2.3: Concurrency Tests
- [ ] Concurrent proposal validation (two agents, same proposal)
- [ ] Concurrent dweller claim (two agents, same dweller)
- [ ] Concurrent feedback upvote (two agents, same feedback)
- [ ] Concurrent story creation with same title/world

### Task 2.4: Expand DST Coverage
- [ ] Add rules: create_aspect, submit_aspect, validate_aspect
- [ ] Add rules: create_story, review_story, respond_to_review
- [ ] Add rules: create_world_event, approve_world_event
- [ ] Add invariants for each new rule set

---

## Findings / Notes

- Logfire MCP exists and installs with one command
- Claude Code hooks support PostToolUse (detect git push), Stop (enforce verification), and agent-based hooks (subagent that verifies)
- Hypothesis RuleBasedStateMachine is the right abstraction for DST
- Both DST layers (game rules + fault injection) use same state machine, combined
- TLA+ deemed unnecessary — Hypothesis + actual code gives ~80% of value with 0% spec maintenance
- claude-code-action uses API billing (not Max subscription)
- Hook coordination uses marker files in `/tmp/claude-deepsci/` — simple and reliable
- Logfire read tokens are PROJECT-scoped (not org-level) — solved with `logfire-mcp-project` wrapper that reads token from `.claude/logfire-token` in project root

---

## Instance Log

| Instance | Phase | Status |
|----------|-------|--------|
| Session 1 | Phase 0 | ✅ Complete (except Logfire MCP — blocked on read token) |
| Session 2 | Phase 0.1 + 2.2 | ✅ Logfire MCP setup + Feedback triage workflows |
