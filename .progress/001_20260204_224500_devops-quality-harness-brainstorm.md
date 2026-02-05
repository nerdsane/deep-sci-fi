# DevOps & Quality Harness Brainstorm

**Date:** 2026-02-04
**Status:** Brainstorming
**Goal:** Design the complete development experience for DeepSciFi, considering agents write the code

---

## Current State Assessment

### What Exists Today

| Layer | Tool | Status |
|-------|------|--------|
| **CI/CD** | GitHub Actions (`deploy.yml`, `review.yml`) | Working |
| **PR Gate** | Typecheck, frontend tests, backend tests, migration check, skill.md sync, schema drift | Working (but `continue-on-error` weakens it) |
| **Deployment** | Railway (backend), Vercel (frontend) | Working |
| **Database** | Supabase PostgreSQL, Alembic migrations | Working |
| **Pre-commit** | Migration check, skill.md endpoint sync | Working |
| **Observability** | Logfire (tracing FastAPI, SQLAlchemy, asyncpg, httpx, OpenAI, system metrics) | Configured but needs verification |
| **Smoke Test** | `scripts/smoke-test.sh` (curl-based endpoint checks) | Exists, not automated |
| **Feedback Loop** | Full feedback API (submit/upvote/resolve/notify) | Working |
| **Tests** | 21 test files (~12K lines), pytest + vitest | Good coverage |

### What's Missing / Gaps

1. **No post-deploy verification in CI** — smoke test exists but isn't wired into deploy.yml
2. **No agent-accessible Logfire feedback** — observability goes to Logfire dashboard, but coding agents can't query it
3. **Feedback loop requires manual intervention** — human must review, decide, and assign work
4. **No automated regression detection** — no canary or staging validation before prod
5. **No deterministic/simulation testing** — all tests are integration tests against real DB
6. **No drift detection for deployed state** — schema check is PR-time only, not runtime
7. **`continue-on-error: true` on all CI steps** — PR can merge even if checks fail (the final "Check Results" step catches it, but the pattern is fragile)

---

## Area 1: The CI/CD Pipeline & Quality Gates

### Current Flow
```
Push to staging → GitHub Actions → Deploy to Railway/Vercel
                      ↓
               PR to main → review.yml (typecheck, tests, migrations, skill sync, schema drift)
                      ↓
               Merge to main → deploy.yml → Deploy to production
```

### Proposed Enhancement

```
Push to staging
  ↓
┌─────────────────────────────────────┐
│ Gate 1: Pre-Deploy Checks (CI)      │
│ ├─ Backend tests (pytest)           │
│ ├─ Frontend typecheck               │
│ ├─ Frontend tests (vitest)          │
│ ├─ Alembic migration applies clean  │
│ ├─ Schema drift check               │
│ ├─ skill.md endpoint sync           │
│ ├─ Slop audit (new)                 │
│ └─ Security scan (new)              │
│                                     │
│ ALL MUST PASS — no continue-on-error│
└─────────────────────────────────────┘
  ↓ (only if Gate 1 passes)
┌─────────────────────────────────────┐
│ Gate 2: Deploy to Staging           │
│ ├─ Run Alembic migrations           │
│ ├─ Deploy backend (Railway)         │
│ └─ Deploy frontend (Vercel)         │
└─────────────────────────────────────┘
  ↓
┌─────────────────────────────────────┐
│ Gate 3: Post-Deploy Verification    │
│ ├─ Smoke test (expanded)            │
│ ├─ Health check with schema verify  │
│ ├─ API contract test (new)          │
│ └─ Notify agent/Slack on success    │
└─────────────────────────────────────┘
  ↓ (staging proven)
┌─────────────────────────────────────┐
│ Gate 4: Promote to Production       │
│ ├─ PR: staging → main               │
│ ├─ Human approval (or auto-merge)   │
│ ├─ Deploy to production             │
│ └─ Production smoke test            │
└─────────────────────────────────────┘
```

### Specific Improvements

1. **Remove `continue-on-error`** from review.yml — if a check fails, the PR should be blocked
2. **Add post-deploy smoke test** as a separate GitHub Action job that runs after deploy
3. **Add Slack notification** on deploy success/failure via the existing webhook
4. **Add staging environment** as a proper concept (staging deploys auto, prod requires PR merge)

---

## Area 2: Observability Feedback Loop (Logfire → Coding Agent)

### Current State
- Logfire is configured and instruments everything
- But the coding agent (Claude Code) has no way to query Logfire
- Errors go to Logfire dashboard — human must check manually

### Proposed: Logfire Query Endpoint

Create an internal admin endpoint that lets the coding agent query recent errors from Logfire:

```python
# New endpoint: GET /api/admin/observability/errors
# Admin-only, returns recent 5xx errors, slow queries, error traces

@router.get("/admin/observability/errors")
async def get_recent_errors(
    admin: User = Depends(get_admin_user),
    hours: int = 24,
):
    """Query Logfire for recent errors.

    Returns structured error data that a coding agent can act on.
    """
    # Option A: Query Logfire API directly
    # Option B: Store errors in local DB table as they happen
    # Option C: Use Logfire's SQL explorer API
```

### Alternative: Error Aggregation Table

Instead of querying Logfire in real-time, create a middleware that captures 5xx errors into a local `platform_error_log` table:

```python
class ErrorCapture(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if response.status_code >= 500:
            # Log to error_log table
            await log_error(request, response, traceback)
        return response
```

Then expose via `GET /api/admin/errors` — the coding agent can check this after deploy.

### Logfire Direct Integration

Logfire has a [Read API / SQL explorer](https://docs.pydantic.dev/logfire/) that can be queried:

```bash
# The coding agent could do:
curl -H "Authorization: Bearer $LOGFIRE_TOKEN" \
  "https://logfire-api.pydantic.dev/v1/projects/deep-sci-fi/sql" \
  -d '{"sql": "SELECT * FROM records WHERE level = '\''error'\'' AND created_at > now() - interval '\''1 hour'\''"}'
```

**Recommendation:** Start with the error aggregation table (simpler, no external dependency for querying), add Logfire API integration later.

---

## Area 3: Feedback Loop Automation

### Current Manual Flow
```
1. Agent submits feedback → stored in DB
2. Human reads feedback summary
3. Human decides what to fix
4. Human tells Claude Code to fix it
5. Claude Code fixes and marks resolved
6. Agent gets notification
```

### Proposed Semi-Automated Flow
```
1. Agent submits feedback → stored in DB
2. NEW: Automated triage classifies and groups feedback
3. NEW: Daily digest sent to human (Slack) with:
   - New feedback items grouped by category
   - Suggested actions (fix/defer/won't fix)
   - One-click approve/reject per item
4. Human approves/rejects via Slack interaction (or CLI command)
5. Approved items auto-assigned to Claude Code
6. Claude Code fixes and marks resolved
7. Agent gets notification
```

### Implementation Options

#### Option A: CLI-Based Triage (Simplest)

Create a script that:
1. Pulls open feedback
2. Groups by category/priority
3. Shows interactive menu
4. Human selects which to address
5. Creates a `.progress/` plan for Claude Code

```bash
# New: scripts/triage-feedback.sh
# Or: python scripts/triage_feedback.py

$ python scripts/triage_feedback.py
╔══════════════════════════════════════════════════╗
║           Deep Sci-Fi Feedback Triage            ║
╠══════════════════════════════════════════════════╣
║                                                  ║
║  8 open feedback items:                          ║
║                                                  ║
║  🔴 CRITICAL (0)                                 ║
║  🟠 HIGH (3)                                     ║
║    1. [5329a6b8] Dweller claim silent fail       ║
║    2. [7eef413d] Proposal validation timeout     ║
║    3. [93b2dde2] Story endpoint 500 on long text ║
║  🟡 MEDIUM (5)                                   ║
║    4. [dfefef03] Error message unclear            ║
║    ...                                           ║
║                                                  ║
║  Actions: [a]pprove  [d]efer  [w]on't fix       ║
║  Enter selections (e.g., "a:1,2,3 d:4,5"):      ║
╚══════════════════════════════════════════════════╝
```

#### Option B: Slack-Based Triage (More Automated)

Send a daily digest to Slack with action buttons:
```json
{
  "blocks": [
    {"type": "header", "text": "📋 Feedback Triage - 8 open items"},
    {"type": "section", "text": "🔴 3 HIGH: dweller claim, validation timeout, story 500"},
    {"type": "actions", "elements": [
      {"type": "button", "text": "Approve All High", "action_id": "approve_high"},
      {"type": "button", "text": "Review Details", "action_id": "review"},
      {"type": "button", "text": "Defer All", "action_id": "defer"}
    ]}
  ]
}
```

**Challenge:** Slack webhook is one-way (send only). Would need a Slack app with interactivity endpoint to receive button clicks. Alternatively, keep it as a notification and use the CLI for the actual decision.

#### Option C: CLAUDE.md Task Queue (Most Integrated)

Create a `.tasks/` directory that acts as a work queue:

```
.tasks/
  pending/
    001_fix-dweller-claim.md    ← auto-generated from approved feedback
    002_fix-story-500.md
  in-progress/
    003_improve-error-messages.md  ← Claude Code claims this
  done/
    004_fixed-validation-timeout.md
```

Human approves feedback → system generates task files → Claude Code picks them up in next session.

**Recommendation:** Start with **Option A** (CLI triage) — it's the fastest to build and requires no infrastructure. Add Slack digest as a notification companion. The CLAUDE.md + `.tasks/` approach is interesting but adds file management complexity.

---

## Area 4: Slop & Drift Detection

### What Is "Slop" in This Context?

1. **Code slop:** TODO comments, placeholder implementations, console.logs, commented-out code, `any` types
2. **API slop:** Endpoints that don't match documentation, response schema drift
3. **Data slop:** Stale feedback items, abandoned proposals, orphaned dwellers
4. **Dependency slop:** Outdated packages, unused imports

### Proposed: Automated Slop Audit

#### A. Static Code Analysis (CI Gate)

```bash
# scripts/slop-check.sh — runs in CI

# Python backend
echo "Checking for code slop..."
grep -rn "TODO\|FIXME\|HACK\|XXX" platform/backend/ --include="*.py" && FAIL=1
grep -rn "console\.log\|print(" platform/backend/api/ --include="*.py" && FAIL=1
grep -rn "pass  #" platform/backend/ --include="*.py" && FAIL=1  # empty pass blocks

# TypeScript frontend
grep -rn "// TODO\|// FIXME\|// HACK" platform/ --include="*.ts" --include="*.tsx" && FAIL=1
grep -rn "console\.log" platform/ --include="*.ts" --include="*.tsx" && FAIL=1
grep -rn ": any" platform/ --include="*.ts" --include="*.tsx" && FAIL=1
```

#### B. API Contract Drift Detection

Compare the live OpenAPI spec against the documented spec:

```python
# scripts/check_api_contract.py
# 1. Load OpenAPI spec from running app
# 2. Load skill.md endpoint tables
# 3. Compare: any endpoints in code but not in docs? Vice versa?
# 4. Compare response schemas against actual responses
```

This is partially covered by `sync_skill_endpoints.py --check` but could be expanded to check response schemas.

#### C. Runtime Drift Detection

The `/health` endpoint already checks schema drift. Could expand to:
- Check that all expected tables exist
- Verify enum values match between code and DB
- Check that all FK constraints are in place
- Verify indexes exist

#### D. Integration with slop-slayer MCP Tool

You have `mcp__slop-slayer__*` tools available. These could be integrated into the CI pipeline:

```yaml
# In review.yml
- name: Run Slop Audit
  run: |
    # Use slop-slayer to detect code quality issues
    npx slop-slayer audit --format json > slop-report.json
```

---

## Area 5: Deterministic Simulation Testing (FoundationDB-Inspired)

### What FoundationDB Does

FoundationDB's simulation testing:
1. **Deterministic execution** — same seed produces same behavior
2. **Fault injection** — randomly drops messages, kills nodes, corrupts data
3. **Time simulation** — fast-forward through time-dependent behavior
4. **Exhaustive state exploration** — tests all possible interleavings

### How This Applies to DeepSciFi

DeepSciFi isn't a distributed database, but it IS a multi-agent coordination platform. The analogies:

| FoundationDB Concept | DeepSciFi Analog |
|---|---|
| Network partition | Agent goes offline during validation |
| Message reordering | Concurrent proposals on same world |
| Node crash | Server restart during multi-step workflow |
| Clock skew | Agents in different timezones, stale data |
| Disk corruption | DB inconsistency from failed migration |

### Practical Simulation Testing for DeepSciFi

#### Level 1: Workflow Simulation (Most Practical)

Create a test harness that simulates the full agent lifecycle:

```python
# tests/simulation/test_agent_lifecycle.py

class AgentSimulator:
    """Simulates an AI agent interacting with the platform."""

    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.agent_id = None
        self.api_key = None

    async def run_lifecycle(self, client):
        """Deterministic agent lifecycle."""
        # 1. Register
        await self.register(client)

        # 2. Propose a world (with random valid parameters)
        proposal_id = await self.propose_world(client)

        # 3. Submit for validation
        await self.submit_proposal(client, proposal_id)

        # 4. Create dweller (after world is approved)
        dweller_id = await self.create_dweller(client, world_id)

        # 5. Claim and act
        await self.claim_dweller(client, dweller_id)
        await self.take_actions(client, dweller_id, num_actions=self.rng.randint(1, 10))

        # 6. Submit feedback
        await self.submit_feedback(client)

class MultiAgentSimulation:
    """Run N agents concurrently with deterministic interleaving."""

    def __init__(self, seed: int, num_agents: int):
        self.agents = [AgentSimulator(seed + i) for i in range(num_agents)]

    async def run(self, client):
        """Run all agents with controlled concurrency."""
        # Deterministic task scheduling based on seed
        tasks = []
        for agent in self.agents:
            tasks.append(agent.run_lifecycle(client))
        await asyncio.gather(*tasks)

        # Verify invariants
        await self.check_invariants(client)

    async def check_invariants(self, client):
        """Platform-level invariants that must always hold."""
        # 1. Every approved proposal has exactly one world
        # 2. Every claimed dweller has exactly one inhabitant
        # 3. Upvote count matches upvoter list length
        # 4. No orphaned records
        # 5. All status transitions are valid
        # 6. Reputation scores are non-negative
```

#### Level 2: Fault Injection

```python
class FaultInjector:
    """Inject failures at specific points in the workflow."""

    async def inject_disconnect(self, at_step: str):
        """Simulate agent disconnecting mid-workflow."""
        pass

    async def inject_duplicate_request(self, endpoint: str):
        """Simulate agent sending same request twice (idempotency check)."""
        pass

    async def inject_concurrent_claim(self, dweller_id: str):
        """Two agents try to claim same dweller simultaneously."""
        pass

    async def inject_stale_read(self, entity_id: str):
        """Agent acts on stale data (world changed since last read)."""
        pass
```

#### Level 3: Property-Based Testing (Hypothesis)

Use Hypothesis to generate random but valid API inputs:

```python
from hypothesis import given, strategies as st

@given(
    title=st.text(min_size=10, max_size=200),
    premise=st.text(min_size=50, max_size=5000),
    year=st.integers(min_value=2030, max_value=2200),
    num_regions=st.integers(min_value=1, max_value=10),
)
async def test_proposal_creation_never_crashes(title, premise, year, num_regions):
    """Any valid input should either succeed or return a clean error — never 500."""
    response = await client.post("/api/proposals", json={...})
    assert response.status_code != 500
```

### What To Build First

**Recommendation:** Start with Level 1 (Workflow Simulation) — it's the most practical and catches the most common bugs:

1. **Multi-agent lifecycle test** — register, propose, validate, inhabit, act, feedback
2. **Invariant checker** — run after every test to verify DB consistency
3. **Seed-based determinism** — same seed = same test = reproducible bugs

This gives you 80% of the value of simulation testing with 20% of the complexity.

---

## Area 6: The Complete Coding Agent Development Loop

### The Dream Workflow

```
┌────────────────────────────────────────────────────────────┐
│                    HUMAN (You)                             │
│                                                            │
│  1. Set vision (.vision/)                                  │
│  2. Triage feedback (approve/reject)                       │
│  3. Review PRs (sign-off on architecture decisions)        │
│  4. That's it.                                             │
└────────────────────────────────────────────────────────────┘
                          ↓ approved work items
┌────────────────────────────────────────────────────────────┐
│                 CODING AGENT (Claude Code)                  │
│                                                            │
│  1. Check feedback summary                                 │
│  2. Pick up approved items                                 │
│  3. Write code + tests                                     │
│  4. Push to staging                                        │
│  5. Wait for CI to pass                                    │
│  6. Verify deployment via:                                 │
│     a. Smoke test (curl-based)                             │
│     b. Health check (schema verification)                  │
│     c. Error log check (Logfire/error table)               │
│  7. Mark feedback as resolved                              │
│  8. Send summary to human via Slack                        │
│  9. Move to next item                                      │
└────────────────────────────────────────────────────────────┘
                          ↓ deployed changes
┌────────────────────────────────────────────────────────────┐
│                 PLATFORM AGENTS (OpenClaw, etc.)            │
│                                                            │
│  1. Use the platform normally                              │
│  2. Encounter issues → submit feedback                     │
│  3. Get notified when issues resolved                      │
│  4. Upvote issues they also experience                     │
└────────────────────────────────────────────────────────────┘
```

### What Needs To Be Built For This

| Component | Effort | Priority | Description |
|-----------|--------|----------|-------------|
| **Feedback triage CLI** | Small | P0 | Script to review/approve/reject feedback items |
| **Post-deploy smoke in CI** | Small | P0 | Add smoke-test.sh as GitHub Actions step after deploy |
| **Slack deploy notifications** | Small | P0 | Notify on deploy success/failure |
| **Error aggregation endpoint** | Medium | P1 | Capture 5xx errors for coding agent to query |
| **Slop audit CI gate** | Small | P1 | Script to check for code quality issues |
| **Fix CI continue-on-error** | Small | P1 | Make CI gates actually block |
| **Multi-agent simulation test** | Medium | P1 | Deterministic lifecycle simulation |
| **Invariant checker** | Medium | P1 | DB consistency verification |
| **Logfire query integration** | Medium | P2 | Query Logfire API for error details |
| **Property-based testing** | Medium | P2 | Hypothesis-based fuzzing |
| **Fault injection framework** | Large | P3 | Simulate failures in agent workflows |

---

## Area 7: Testing Strategy Expansion

### Current Test Coverage

**Well-tested:**
- Auth flows (registration, API key validation)
- Feedback system (submit, upvote, summary)
- Story creation and engagement
- Notification delivery
- E2E proposal → validation → approval
- E2E aspect flow
- E2E dweller flow
- Social features (comments, reactions)

**Gaps identified:**
- No load/stress testing
- No API contract tests (response schema validation)
- No concurrency tests (race conditions)
- No migration rollback tests
- No frontend E2E (Playwright configured but no tests found)
- No webhook delivery reliability tests
- No rate limiting verification tests

### Proposed New Test Categories

1. **Contract Tests** — Verify API responses match OpenAPI spec
2. **Concurrency Tests** — Multiple agents acting on same resource
3. **Migration Tests** — Forward and rollback of each migration
4. **Idempotency Tests** — Same request twice should be safe
5. **Invariant Tests** — Run after any test suite to check DB consistency
6. **Performance Baseline** — Simple timing tests to catch regressions

---

## Summary: What to Build, In What Order

### Phase 0: Quick Wins (1-2 sessions)
1. Fix CI `continue-on-error` pattern
2. Add post-deploy smoke test to deploy.yml
3. Add Slack notifications on deploy success/failure
4. Create feedback triage CLI script

### Phase 1: Core Quality Harness (2-3 sessions)
5. Error aggregation endpoint (capture 5xx to DB)
6. Slop audit script (static analysis for code quality)
7. Multi-agent simulation test framework
8. Invariant checker for DB consistency

### Phase 2: Advanced Verification (3-5 sessions)
9. API contract tests
10. Concurrency/race condition tests
11. Property-based testing with Hypothesis
12. Logfire query integration for coding agent

### Phase 3: Full Automation (ongoing)
13. Automated feedback → work item pipeline
14. Fault injection framework
15. Performance baseline tests
16. Self-healing deployment (auto-rollback on smoke test failure)
