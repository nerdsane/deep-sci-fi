# Deterministic Simulation Testing for Agent Platforms: Applying FoundationDB's Insight to Deep Sci-Fi

**Authors:** Claude (Opus 4.5) and Sesh Endranalla
**Date:** February 4, 2026
**Project:** Deep Sci-Fi — a social platform for AI-generated sci-fi worlds
**Status:** Design + Implementation Plan

---

## Abstract

FoundationDB proved that the most reliable way to test distributed systems is to run actual production code in a deterministic simulation that explores all possible interleavings of events and failures. We apply this insight to Deep Sci-Fi, a multi-agent coordination platform where external AI agents propose worlds, validate each other's work, inhabit characters, and write stories.

Deep Sci-Fi isn't a distributed database, but it shares a critical property with one: **correctness depends on invariants holding under arbitrary sequences of concurrent operations from untrusted external actors**. A proposal must pass through VALIDATING before APPROVED. A dweller can only be claimed by one agent. Upvote counts must equal the length of the upvoter list. These are game rules — and game rules can have loopholes.

We present a two-layer deterministic simulation testing approach:

1. **Game Rule Invariant Testing** — Hypothesis `RuleBasedStateMachine` generates random sequences of actual API calls against real production code, checking invariants after each step.
2. **Fault-Injected Workflow Testing** — The same state machine includes failure injection rules (DB timeouts, concurrent requests, interrupted transactions) to verify that infrastructure failures cannot violate game rules.

Both layers run the **actual production code** via the httpx test client against a real PostgreSQL database. There is no specification language, no model to drift from implementation. The test IS the code.

---

## 1. The Problem: Game Logic in Agent Platforms

### 1.1 What Are "Game Rules"?

Deep Sci-Fi encodes rules about how agents interact with the platform:

| Rule | Invariant |
|------|-----------|
| Proposal lifecycle | A proposal transitions DRAFT → VALIDATING → APPROVED/REJECTED. No skipping states. |
| Dweller exclusivity | A dweller is claimed by at most one agent at any time. |
| Upvote consistency | `feedback.upvote_count == len(feedback.upvoters)` always. |
| Self-upvote prevention | An agent cannot upvote their own feedback. |
| Double-upvote prevention | An agent can upvote a given feedback item exactly once. |
| Validation consensus | A proposal is approved only after sufficient validator agreement. |
| Canon integrity | An aspect approval must include `updated_canon_summary`. |
| Story acclaim | A story reaches ACCLAIMED only after 2+ recommend_acclaim reviews + author response. |
| Status terminal states | RESOLVED and WONT_FIX feedback cannot transition further. |
| Authentication boundary | Unauthenticated requests cannot modify state. |

These rules are implemented across ~12,000 lines of Python in 17 API routers. Each rule is individually testable with unit tests. But the question isn't "does each rule work in isolation?" — it's **"can any sequence of valid API calls violate these rules?"**

### 1.2 Why Unit Tests Aren't Enough

Unit tests verify: "If I call endpoint X with input Y, I get result Z."

They don't verify: "If Agent A creates a proposal, Agent B starts validating it, Agent A modifies it while validation is in progress, and Agent C submits a conflicting aspect, do all invariants still hold?"

The space of possible action sequences is combinatorially large. Manual test cases cover the paths developers think of. The bugs live in the paths nobody thinks of.

### 1.3 The FoundationDB Insight

FoundationDB's simulation testing philosophy:

> **"We don't test a model of our system. We test the system itself, in a simulated environment where we control time, I/O, and failure injection."**

Key principles:
- **Deterministic**: Same seed → same execution → reproducible bugs
- **Exhaustive**: Random exploration of action interleavings with thousands of seeds
- **Real code**: The simulation runs actual production code, not a specification
- **Failure-aware**: Infrastructure failures (network partitions, disk corruption, crashes) are injected as first-class events

We can't replicate FDB's approach exactly — we can't replace Python's asyncio I/O layer with a deterministic simulator the way FDB replaces C++ I/O primitives. But we can achieve the same goals at the API level.

---

## 2. Our Approach: Two-Layer DST

### 2.1 Layer 1 — Game Rule Invariant Testing

**Tool**: Python's [Hypothesis](https://hypothesis.readthedocs.io/) library with `RuleBasedStateMachine`.

**How it works**: Define a state machine where:
- **Rules** are API calls agents can make (register, propose, validate, claim dweller, act, upvote, etc.)
- **Invariants** are checked after every rule execution
- **Hypothesis** generates random sequences of rule applications with random valid parameters

```python
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, initialize

class DeepSciFiGameLogic(RuleBasedStateMachine):
    """
    Explores random sequences of API calls and verifies
    game rules hold after each step.
    """

    def __init__(self):
        super().__init__()
        self.client = None  # httpx AsyncClient
        self.agents = {}     # agent_id -> api_key
        self.proposals = {}  # proposal_id -> status
        self.dwellers = {}   # dweller_id -> claimed_by
        self.feedback = {}   # feedback_id -> {upvoters, upvote_count}

    @initialize()
    async def setup(self):
        """Create test database and HTTP client."""
        self.client = await create_test_client()
        # Register 3-5 agents
        for i in range(random.randint(3, 5)):
            agent = await self.register_agent(f"agent-{i}")
            self.agents[agent["id"]] = agent["api_key"]

    @rule()
    async def create_proposal(self):
        """Random agent creates a proposal."""
        agent_id = random.choice(list(self.agents.keys()))
        response = await self.client.post(
            "/api/proposals",
            headers={"X-API-Key": self.agents[agent_id]},
            json={...random valid proposal...}
        )
        if response.status_code == 201:
            self.proposals[response.json()["id"]] = "draft"

    @rule()
    async def submit_proposal(self):
        """Random agent submits a draft proposal."""
        drafts = [p for p, s in self.proposals.items() if s == "draft"]
        if not drafts:
            return
        proposal_id = random.choice(drafts)
        response = await self.client.post(f"/api/proposals/{proposal_id}/submit", ...)
        if response.status_code == 200:
            self.proposals[proposal_id] = "validating"

    @rule()
    async def validate_proposal(self):
        """Random agent validates a validating proposal."""
        validating = [p for p, s in self.proposals.items() if s == "validating"]
        if not validating:
            return
        # Agent validates (not the creator)
        ...

    @rule()
    async def claim_dweller(self):
        """Random agent tries to claim a random dweller."""
        ...

    @rule()
    async def upvote_feedback(self):
        """Random agent upvotes random feedback."""
        ...

    # ──────────────────────────────────────────────
    # INVARIANTS — checked after EVERY rule execution
    # ──────────────────────────────────────────────

    @invariant()
    async def proposals_follow_valid_transitions(self):
        """No proposal has an invalid status transition history."""
        for proposal_id, expected_status in self.proposals.items():
            resp = await self.client.get(f"/api/proposals/{proposal_id}")
            actual = resp.json()["status"]
            assert actual == expected_status, (
                f"Proposal {proposal_id}: expected {expected_status}, got {actual}"
            )

    @invariant()
    async def dwellers_have_at_most_one_owner(self):
        """No dweller is claimed by two different agents."""
        # Query DB directly to check this at the data level
        ...

    @invariant()
    async def upvote_counts_are_consistent(self):
        """upvote_count always equals len(upvoters)."""
        for fb_id in self.feedback:
            resp = await self.client.get(f"/api/feedback/{fb_id}")
            fb = resp.json()["feedback"]
            assert fb["upvote_count"] == len(fb.get("upvoters", [])), (
                f"Feedback {fb_id}: count={fb['upvote_count']}, "
                f"upvoters={len(fb.get('upvoters', []))}"
            )

    @invariant()
    async def no_500_errors_in_log(self):
        """No unhandled exceptions occurred during this sequence."""
        # Check error log table or in-memory error collector
        assert self.error_count == 0
```

**Key property**: When Hypothesis finds a failing sequence, it **shrinks** it to the minimal reproduction case. Instead of "after 47 random actions, invariant X broke," you get "these 3 specific actions in this order break invariant X."

### 2.2 Layer 2 — Fault Injection

The same state machine includes rules that inject infrastructure failures:

```python
class DeepSciFiWithFaults(DeepSciFiGameLogic):
    """Extends game logic tests with infrastructure fault injection."""

    @rule()
    async def inject_db_timeout(self):
        """Next DB query will timeout."""
        # Monkey-patch the session to raise asyncpg.QueryCanceledError
        self.inject_next_query_failure(
            asyncpg.QueryCanceledError("simulated timeout")
        )

    @rule()
    async def inject_concurrent_claim(self):
        """Two agents try to claim the same dweller simultaneously."""
        unclaimed = [d for d, owner in self.dwellers.items() if owner is None]
        if not unclaimed or len(self.agents) < 2:
            return
        dweller_id = random.choice(unclaimed)
        agents = random.sample(list(self.agents.keys()), 2)

        # Fire both requests concurrently
        results = await asyncio.gather(
            self.client.post(
                f"/api/dwellers/{dweller_id}/claim",
                headers={"X-API-Key": self.agents[agents[0]]}
            ),
            self.client.post(
                f"/api/dwellers/{dweller_id}/claim",
                headers={"X-API-Key": self.agents[agents[1]]}
            ),
            return_exceptions=True
        )
        # Exactly one should succeed, one should fail
        successes = [r for r in results if not isinstance(r, Exception) and r.status_code == 200]
        assert len(successes) <= 1, (
            f"Both agents claimed dweller {dweller_id}!"
        )

    @rule()
    async def inject_request_during_transaction(self):
        """Simulate a second request arriving while a multi-step
        operation is mid-transaction (e.g., proposal approval
        that creates a world)."""
        ...

    @rule()
    async def inject_duplicate_request(self):
        """Same request sent twice (network retry). Must be idempotent."""
        # Replay the last successful request
        if self.last_request:
            response = await self.client.request(**self.last_request)
            # Should either succeed idempotently or return 409/400
            assert response.status_code != 500
```

### 2.3 Why Both Layers Together

Individually:
- Layer 1 catches: "The code has a logic bug where proposals can skip states"
- Layer 2 catches: "If the DB times out mid-approval, the proposal is stuck in a broken state"

Together:
- "If Agent A's validation is interrupted by a DB timeout, and Agent B immediately submits a conflicting validation, the proposal ends up approved with contradictory validations"

This is where bugs live in real production systems. Not in single-operation failures, but in the **interaction between concurrent operations and failure recovery**.

---

## 3. How This Applies to the FDB Philosophy

### 3.1 What We Achieve

| FDB Principle | Our Implementation |
|---|---|
| **Deterministic execution** | Hypothesis seeds produce reproducible sequences |
| **Actual production code** | httpx test client hits real FastAPI endpoints, real SQLAlchemy, real PostgreSQL |
| **Fault injection** | Rules that inject DB timeouts, concurrent requests, duplicate submissions |
| **Exhaustive state exploration** | Hypothesis generates thousands of random action sequences per test run |
| **Minimal reproduction** | Hypothesis shrinks failing cases to smallest sequence that breaks invariants |

### 3.2 What We Don't Achieve (And Why That's OK)

| FDB Feature | Why We Skip It |
|---|---|
| **Time simulation** | Our system doesn't have time-dependent correctness (no consensus timeouts, no leader election). Heartbeat intervals are soft requirements. |
| **Network-level simulation** | We can't replace Python's asyncio I/O layer. But we inject failures at the application level (DB queries, HTTP requests), which catches the same class of bugs for a web API. |
| **Deterministic thread scheduling** | Python's GIL + asyncio event loop makes this less relevant. We test concurrency via `asyncio.gather()` which is deterministic enough for our needs. |

### 3.3 The Alignment Guarantee

A critical question: **how do we ensure the simulation matches production?**

In FDB, the simulation runs the exact same compiled binary as production. In our case:

1. The test client calls real FastAPI endpoints
2. Which use real SQLAlchemy models
3. Which write to real PostgreSQL
4. Through the same middleware, auth, and error handlers

The only difference from production: the test uses a local PostgreSQL instance instead of Supabase. The code paths are identical. There is no specification to drift from implementation because **the implementation IS the specification**.

This is the fundamental advantage over TLA+ or any other formal specification approach: the "model" can never be wrong because there is no model — only the code itself.

---

## 4. What This Catches That Unit Tests Don't

### 4.1 State Transition Loopholes

Unit tests verify: "Submitting a draft proposal transitions it to validating."

DST verifies: "There is no sequence of API calls that can transition a proposal to approved without going through validating." This includes sequences involving:
- Concurrent modifications
- Interrupted transactions
- Duplicate requests
- Race conditions between validation and modification

### 4.2 Consistency Violations Under Concurrency

Unit tests verify: "Claiming a dweller sets inhabited_by."

DST verifies: "If two agents claim the same dweller simultaneously, exactly one succeeds." This tests the actual PostgreSQL row-level locking and SELECT FOR UPDATE behavior.

### 4.3 Idempotency Failures

Unit tests verify: "Creating a proposal returns 201."

DST verifies: "Creating the same proposal twice returns 201 then 409 (or idempotent 201), never a 500 or a duplicate record."

### 4.4 Cascade Failures

Unit tests verify: "Approving a proposal creates a world."

DST verifies: "If the world creation fails after proposal status is set to APPROVED, the system recovers to a consistent state (either both committed or both rolled back)."

---

## 5. How This Helps Us Concretely

### 5.1 For the Human (Sesh)

- **Confidence in game rules**: You can add new rules (reputation gates, new status transitions) and DST will automatically verify they don't break existing invariants
- **Regression detection**: If a code change introduces a loophole, DST finds it before agents do
- **Reduced feedback load**: Fewer bugs reaching production means fewer feedback items to triage
- **Architectural freedom**: You can refactor confidently knowing that 1000+ random action sequences still pass

### 5.2 For the Coding Agent (Claude Code)

- **Fast feedback loop**: Run DST locally before pushing. If invariants break, fix before deploy
- **Bug localization**: Hypothesis's shrinking gives minimal reproduction cases, not "something broke somewhere"
- **New feature confidence**: Adding a new endpoint? Add its rule to the state machine. If it introduces inconsistencies with existing rules, the test finds it
- **Post-deploy verification**: DST can run against the staging deployment URL as a comprehensive smoke test

### 5.3 For the Platform Agents (OpenClaw, etc.)

- **Fewer bugs**: Game rule loopholes get caught in testing, not in production
- **Predictable behavior**: If the simulation proves "proposals always follow valid transitions," agents can trust the state machine
- **Less need for defensive coding**: Agents don't need workarounds for API inconsistencies

---

## 6. Implementation Plan

### 6.1 Phase 1a: Core State Machine

Create `platform/backend/tests/simulation/test_game_rules.py`:
- Register N agents
- Rules: create_proposal, submit_proposal, validate_proposal, create_dweller, claim_dweller, take_action, submit_feedback, upvote_feedback
- Invariants: all rules from Section 1.1

### 6.2 Phase 1b: Fault Injection

Extend with `test_game_rules_with_faults.py`:
- Rules: inject_db_timeout, inject_concurrent_claim, inject_duplicate_request
- Same invariants, now must hold under failure conditions

### 6.3 Phase 1c: CI Integration

Add to `review.yml`:
- Run DST with 200 seeds (takes ~2-3 minutes)
- Any invariant violation blocks the PR
- Hypothesis database saved as artifact for reproduction

### 6.4 Phase 1d: Expand Coverage

As new features are added:
- Add new rules to the state machine (aspects, stories, events, suggestions)
- Add corresponding invariants
- The test automatically explores interactions between new and existing features

---

## 7. Comparison with Alternative Approaches

### 7.1 TLA+ / Formal Specification

**Pros**: Exhaustive state space exploration, mathematical proofs.
**Cons**: Separate specification language that can drift from code. Tests the model, not the implementation. High maintenance overhead. Finding: the gap between spec and code is where bugs hide.

**Our approach**: No specification to maintain. Tests run actual code.

### 7.2 Chaos Engineering (Gremlin, Litmus)

**Pros**: Tests real production infrastructure. Finds real failure modes.
**Cons**: Non-deterministic — hard to reproduce failures. Requires production-like environment. Can cause real outages.

**Our approach**: Deterministic — same seed reproduces the same failure. Runs in test environment. No production risk.

### 7.3 Property-Based Testing (Standard Hypothesis)

**Pros**: Generates random inputs, finds edge cases.
**Cons**: Typically tests single functions/endpoints in isolation. Doesn't explore multi-step workflows.

**Our approach**: Extends property-based testing to stateful, multi-step, multi-agent workflows with `RuleBasedStateMachine`.

### 7.4 Integration Tests (What We Have Now)

**Pros**: Tests specific user stories. Easy to write and understand.
**Cons**: Only covers paths developers think of. The state space of multi-agent interactions is too large for manual test case design.

**Our approach**: Complements integration tests with randomized exploration. DST finds the paths nobody thought to test.

---

## 8. Conclusion

FoundationDB's key insight wasn't "simulate networks." It was: **run your actual code through every possible sequence of events and check that your invariants always hold.** This insight applies directly to any system with complex state transitions and concurrent actors — which is exactly what a multi-agent platform is.

By combining Hypothesis's `RuleBasedStateMachine` with fault injection, we get:
- Deterministic, reproducible test execution
- Exhaustive exploration of action interleavings
- Actual production code under test (not a model)
- Failure injection as a first-class testing primitive
- Automatic minimal reproduction of invariant violations

The result: higher confidence in game rule correctness, fewer bugs reaching production, faster development iterations, and a platform that agents can trust.

## 9. Honest Limitations

No testing approach is complete. Here is what our DST harness does **not** cover, and why each gap is accepted:

### 9.1 Model Primary Keys Are Non-Deterministic

All 19 SQLAlchemy models use `default=uuid.uuid4` for primary keys. These UUIDs are generated by the database driver, not our seeded RNG. Same seed does not produce the same set of IDs.

**Why accepted:** Primary keys are opaque identifiers. The state machine stores whatever the API returns and uses it for subsequent calls. No invariant depends on the *value* of a UUID, only its *uniqueness* and *referential integrity* — both of which are tested.

### 9.2 Thread Scheduling Is Non-Deterministic

Fault injection rules use `ThreadPoolExecutor` for concurrent requests. Python's thread scheduler is not controlled by our simulation seed.

**Why accepted:** This is intentional. We test that race outcomes are safe *regardless of scheduling order*. The invariant "at most one agent claims a dweller" must hold whether thread A runs first, thread B runs first, or they interleave. Non-deterministic scheduling makes this test stronger, not weaker.

### 9.3 Rate Limiters Are Disabled

Production rate limiters (SlowAPI) are turned off in simulation. Enabling them would cause false 429 rejections that prevent game rule exploration.

**Why accepted:** Rate limiting is infrastructure, not game logic. It doesn't affect state transitions or invariant correctness. Rate limiter behavior is tested separately.

### 9.4 AgentContextMiddleware Is Patched

The `AgentContextMiddleware` is replaced with a passthrough in simulation. It accesses async context vars that break under httpx's sync-to-async bridge.

**Why accepted:** This middleware only adds logging/tracing context (request ID, agent name). It doesn't affect request handling, authorization, or business logic.

### 9.5 Single-Database Topology

Tests run against a single PostgreSQL instance. Production may use connection pooling (PgBouncer) or cross-region replication.

**Why accepted:** Connection pooling doesn't affect SQL semantics. Cross-region latency could surface in real deployments but would only matter for network partitions — which our platform handles through idempotent operations and client-side retries, not database-level consensus.

### 9.6 Drift Prevention Covers Observable Behavior Only

The schema validation (strategies vs. Pydantic models) and coverage checker (OpenAPI vs. test URL patterns) catch changes to *observable* request/response contracts. Internal-only changes (log messages, metric labels, non-asserted response fields) are not caught automatically.

**Why accepted:** This is the same limitation as any test suite. Internal changes that don't affect observable behavior are, by definition, not bugs.

---

*This paper was written collaboratively by Claude (Opus 4.5) and Sesh Endranalla while designing the quality assurance harness for Deep Sci-Fi.*
