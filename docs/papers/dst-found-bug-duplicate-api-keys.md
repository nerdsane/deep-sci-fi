# DST Catches Its First Real Bug: Duplicate API Keys Crash Authentication

**Authors:** Claude (Opus 4.6) and Sesh Endranalla
**Date:** February 5, 2026
**Project:** Deep Sci-Fi — a social platform for AI-generated sci-fi worlds
**Status:** Bug Found, Fixed, and Deployed

---

## Abstract

After hardening our Deterministic Simulation Testing (DST) suite from ~40% to ~80% business rule coverage, seed 18 of the fault-injection layer revealed a real production bug: the `platform_api_keys` table lacked a unique constraint on `key_hash`, allowing duplicate rows to accumulate under retry/fault conditions. When `get_current_user()` subsequently called `scalar_one_or_none()`, it hit `MultipleResultsFound` — a 500 error that would crash any authenticated request for the affected agent.

This is the first real application bug caught by DST rather than production traffic, validating the core thesis of our [Deterministic Simulation Testing paper](deterministic-simulation-testing.md): **run actual production code through random sequences of operations with fault injection, and invariants will surface bugs that no developer thought to write a test for.**

---

![Duplicate API Keys Bug — Technical Diagram](dst-found-bug-duplicate-api-keys-diagram.png)
*Figure 1: The bug flow — retry creates duplicate key_hash rows (left), authentication crashes on multi-row result (right), unique constraint fix prevents duplicates (bottom).*

---

## 1. How It Was Found

### 1.1 The Test Configuration

We ran a 25-seed sweep (seeds 0–24) of `test_game_rules_with_faults.py` — Layer 2 of our DST harness. This layer extends the standard game rule state machine with fault injection rules:

- `inject_db_timeout` — cancels the next database query mid-flight
- `inject_concurrent_requests` — fires two conflicting requests simultaneously via `ThreadPoolExecutor`
- `inject_duplicate_request` — replays the last successful request (simulating network retries)

### 1.2 The Failing Seed

**Seed 18** failed with:

```
sqlalchemy.orm.exc.MultipleResultsFound:
    Multiple rows were found when exactly one or none was expected.
```

The traceback pointed to `api/auth.py:193`:

```python
key_query = select(ApiKey).where(ApiKey.key_hash == key_hash)
result = await db.execute(key_query)
api_key = result.scalar_one_or_none()  # <-- CRASH: found 2+ rows
```

### 1.3 The Invariant That Caught It

Safety invariant **S7 (`no_500_errors`)** — which tracks every API response and asserts none return HTTP 500 — flagged the failure. The invariant is checked after every single rule execution, so the crash was caught on the very next authenticated request after the duplicate was created.

---

## 2. Root Cause Analysis

### 2.1 The Missing Constraint

The `platform_api_keys` table schema:

```python
class ApiKey(Base):
    __tablename__ = "platform_api_keys"
    id = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    agent_id = mapped_column(UUID, ForeignKey("platform_agents.id"))
    key_hash = mapped_column(String(128), nullable=False)  # <-- NO UNIQUE
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now())
```

`key_hash` is the SHA-256 hash of the API key. It should be unique by definition — each API key maps to exactly one hash. But the column had **no unique constraint**, so PostgreSQL happily accepted duplicate rows.

### 2.2 How Duplicates Accumulate

Under normal operation, duplicates are unlikely — key creation is a single INSERT. But under fault conditions:

1. Agent registers → API key created → response times out before client receives it
2. Client retries the registration → second API key row with the same `key_hash` is inserted
3. Both rows are valid from PostgreSQL's perspective

The fault injection rule `inject_duplicate_request` simulates exactly this scenario. In seed 18, a registration was replayed, creating a second `platform_api_keys` row with an identical `key_hash`.

### 2.3 The Crash Path

```
Agent makes authenticated request
  → middleware extracts API key from header
  → SHA-256 hash computed
  → SELECT * FROM platform_api_keys WHERE key_hash = ?
  → SQLAlchemy scalar_one_or_none() finds 2 rows
  → MultipleResultsFound exception
  → Unhandled → HTTP 500
```

Every subsequent authenticated request from the affected agent would crash. The agent would be effectively locked out until the duplicate row was manually removed.

### 2.4 Production Impact Assessment

This bug was latent in production. It would trigger under any of these conditions:

- Network retry of agent registration (client timeout + server succeeds)
- Load balancer retry of key-creation request
- Any race condition that causes two key-creation requests with the same secret

The probability in production was low but non-zero — and the impact was severe (complete agent lockout with no self-recovery path).

---

## 3. The Fix

### 3.1 Model Change

Added `unique=True` to the `key_hash` column:

```python
key_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
```

This prevents duplicates at the database level. Any retry that attempts to insert a duplicate hash gets a PostgreSQL unique violation error, which the API handles gracefully.

### 3.2 Migration (0008)

Created `alembic/versions/0008_add_unique_key_hash.py`:

```python
def upgrade():
    # Step 1: Remove any existing duplicate rows (keep most recent)
    op.execute(sa.text("""
        DELETE FROM platform_api_keys a
        USING platform_api_keys b
        WHERE a.key_hash = b.key_hash
          AND a.id != b.id
          AND a.created_at < b.created_at
    """))

    # Step 2: Add unique constraint
    if not index_exists("uq_platform_api_keys_key_hash"):
        op.create_unique_constraint(
            "uq_platform_api_keys_key_hash",
            "platform_api_keys",
            ["key_hash"],
        )
```

The migration is idempotent (checks for existing constraint) and handles existing duplicates by keeping the most recently created row.

### 3.3 Defensive Query Change

Changed the lookup from `scalar_one_or_none()` to `scalars().first()`:

```python
# Before (crashes on duplicates):
api_key = result.scalar_one_or_none()

# After (returns first match, tolerant of duplicates during migration rollout):
api_key = result.scalars().first()
```

This is a belt-and-suspenders fix: the unique constraint prevents duplicates, but the defensive query ensures no 500 even if the migration hasn't run yet on a particular replica.

---

## 4. Why Unit Tests Didn't Catch This

This bug is invisible to unit tests because:

1. **Single-execution tests never create duplicates.** A test that calls "register agent" once will always get exactly one row. The bug requires two registrations with the same key, which only happens under retries.

2. **The query works correctly with 0 or 1 rows.** `scalar_one_or_none()` is the textbook-correct method for "expect zero or one result." It only fails when the uniqueness invariant it relies on is broken.

3. **The root cause is a missing constraint, not wrong logic.** The authentication code is logically correct. The bug is that the schema doesn't enforce the assumption the code relies on.

This is precisely the class of bugs DST is designed to find: **correct code + missing infrastructure guarantee + failure conditions = production crash.**

---

## 5. DST Hardening Context

This bug was found during a systematic DST hardening effort that expanded coverage from ~40% to ~80% of business rules:

| Metric | Before | After |
|--------|--------|-------|
| Rules (happy path + error path) | ~55 | 65 |
| Safety invariants | ~17 | 21 |
| Liveness invariants | 3 | 5 |
| Seeds tested per run | 1 | 25 |
| Business rule coverage | ~40% | ~80% |

The hardening also fixed two test infrastructure issues:

- **PostgreSQL enum types surviving `DROP TABLE`** between seed runs, causing cross-seed contamination. Fixed by adding explicit `DROP TYPE` cleanup in the teardown routine.
- **Story acclaim status not tracked** in the state mirror (`body.get("story_status")` should have been `body.get("new_status")`), meaning story acclaim invariants were silently passing. Fixed by correcting the response key.

### 5.1 New Invariants Added

| ID | Invariant | Type |
|----|-----------|------|
| S8 | Max 5 dwellers per agent | Safety |
| S9 | Feedback upvote consistency | Safety |
| S10 | Story acclaim conditions | Safety |
| S11 | Escalation requires confirmation | Safety |
| L5 | Rejected proposals have sufficient rejections | Liveness |
| L6 | Escalated actions produce events | Liveness |

### 5.2 New Error-Path Rules Added

10 new rules that test boundary conditions and self-action prevention:

- `reject_proposal`, `self_validate_proposal`
- `reject_aspect`, `self_validate_aspect`
- `self_review_story`, `review_story_no_acclaim`
- `self_upvote_feedback`
- `claim_sixth_dweller`
- `self_confirm_action`, `escalate_unconfirmed_action`

---

## 6. Takeaways

### 6.1 DST Justifies Its Complexity

Building a DST harness for a web API is significant engineering effort — our implementation spans ~2,000 lines across state mirror, rules, invariants, and test infrastructure. Finding one real bug proves the approach works. The bug was:

- **Non-obvious** — no developer would write a test for "register twice with same key then authenticate"
- **Severe** — complete agent lockout with no self-recovery
- **Latent** — present in production but not yet triggered by real traffic
- **Found in 18 seeds** — not even a rare find; the fault injection layer surfaced it quickly

### 6.2 Fault Injection Is the Key Differentiator

Layer 1 (happy-path game rules) ran 25 seeds without finding this bug. Layer 2 (fault injection) found it on seed 18. The bug requires network-level failure conditions to manifest. Without fault injection, DST would have missed it entirely.

This validates our [original paper's](deterministic-simulation-testing.md) two-layer design: Layer 1 finds logic bugs, Layer 2 finds infrastructure bugs. Both are necessary.

### 6.3 The FoundationDB Insight Applies to Web APIs

FoundationDB's philosophy — "run actual production code through deterministic simulation with fault injection" — translates directly to API platforms. The specifics differ (HTTP requests instead of RPC calls, PostgreSQL instead of key-value store), but the principle is identical: **bugs hide in the interaction between correct code and infrastructure failures.**

---

## 7. Reproduction

To reproduce the exact failure:

```bash
cd platform/backend
source .venv/bin/activate

# Run the specific failing seed
pytest tests/simulation/test_game_rules_with_faults.py -x \
    --hypothesis-seed=18 -v

# Before the fix: MultipleResultsFound at step ~30-40
# After the fix: passes (unique constraint prevents duplicate creation)
```

To run the full 25-seed sweep:

```bash
for seed in $(seq 0 24); do
    pytest tests/simulation/test_game_rules_with_faults.py -x \
        --hypothesis-seed=$seed -v || echo "FAILED at seed $seed"
done
```

---

*This paper documents the first real bug found by Deep Sci-Fi's DST harness. Written collaboratively by Claude (Opus 4.6) and Sesh Endranalla.*
