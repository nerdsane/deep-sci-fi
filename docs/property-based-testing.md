# Property-Based Testing (DST)

Deterministic Simulation Testing for the Deep Sci-Fi API using Hypothesis stateful testing + Pydantic-driven data generation. Tests that any sequence of valid API calls maintains game rules.

## The 4-Tier Architecture

| Tier | File | What it tests | `max_examples` | `stateful_step_count` |
|------|------|---------------|----------------|----------------------|
| 1 - Deterministic | `test_game_rules.py` | ~95 rules, same data, varies rule order | 50 (200 in CI) | 30 |
| 2 - Fault injection | `test_game_rules_with_faults.py` | + concurrent race conditions (claims, reviews, approvals) | 50 | 30 |
| 3 - Fuzzing | `test_game_rules_with_fuzzing.py` | + Pydantic-driven data diversity (boundary values, all enums) | 30 | 20 |
| 4 - Fuzz + faults | `test_game_rules_with_fuzz_faults.py` | + fuzzed data under concurrency | 20 | 15 |

Each tier inherits everything from the previous. Tier 4 runs all ~95 deterministic rules, all ~10 fuzz rules, all 5 concurrent-fuzz rules, and all invariants.

## How `from_model()` Works

`pydantic_strategies.py:from_model(PydanticModel, overrides={})` reads Field constraints from a Pydantic model and builds a Hypothesis strategy that produces plain dicts.

### Mapping table

| Pydantic type | Hypothesis strategy | Constraint support |
|--------------|--------------------|--------------------|
| `str` | `st.text(alphabet=readable_chars)` | `min_length`, `max_length` |
| `int` | `st.integers()` | `ge`, `le`, `gt`, `lt` |
| `float` | `st.floats()` | `ge`, `le`, `gt`, `lt` |
| `bool` | `st.booleans()` | - |
| `Enum` | `st.sampled_from(list(EnumClass))` | - |
| `Literal[...]` | `st.sampled_from(literal_values)` | - |
| `Optional[X]` | `st.one_of(st.none(), strategy_for_X)` | - |
| `list[X]` | `st.lists(strategy_for_X)` | `min_length`, `max_length` |
| `BaseModel` (nested) | `from_model(NestedModel)` | recursive |
| `UUID` | `st.uuids()` | - |

### Example

```python
from pydantic_strategies import from_model, serialize
from api.events import EventCreateRequest

# Generates diverse dicts like:
# {"title": "Xk2...", "description": "Long fuzzed text...",
#  "year_in_world": 2030, "affected_regions": [], ...}
payload = data.draw(from_model(EventCreateRequest))
resp = client.post("/api/events/...", json=serialize(payload))
```

Use `overrides` to inject contextual values:
```python
payload = data.draw(from_model(DwellerCreateRequest, overrides={
    "origin_region": "North District",       # concrete value
    "current_region": st.sampled_from([...]), # strategy
}))
```

## How to Add a New Fuzz Rule

1. Add the rule method to `tests/simulation/rules/fuzz.py` in the `FuzzRulesMixin` class:

```python
@rule(data=st.data())
def fuzz_create_thing(self, data):
    """Create thing with fuzzed data."""
    agent = self._random_agent()
    payload = data.draw(from_model(ThingCreateRequest))
    resp = self.client.post(
        "/api/things",
        headers=self._headers(agent),
        json=serialize(payload),
    )
    self._track_response(resp, "fuzz create thing")
    assert resp.status_code < 500, f"Server error: {resp.text[:300]}"
    if resp.status_code == 200:
        # Track in state mirror so invariants work
        body = resp.json()
        self.state.things[body["id"]] = ThingState(...)
```

2. State tracking on success is required for invariants to verify the entity.

3. The rule automatically appears in Tier 3 (fuzzing) and Tier 4 (fuzz+faults) since both inherit from `FuzzRulesMixin`.

## How to Add a New Invariant

### Safety invariants (`invariants/safety.py`)

Checked after **every** rule step. Use for properties that must hold at all times.

```python
@invariant()
def s_my_invariant(self):
    """Description of what this checks."""
    for item_id, item in self.state.items.items():
        # Check state mirror
        assert some_condition, f"Item {item_id}: violation message"
        # Optionally verify against API
        resp = self.client.get(f"/api/items/{item_id}")
        if resp.status_code == 200:
            actual = resp.json()
            assert actual_matches_expected
```

### Liveness invariants (`invariants/liveness.py`)

Checked only at **teardown**. Use for eventual consistency properties.

```python
def _l_my_liveness_check(self):
    """L-XX: Description."""
    # ... assertions ...
```

Then add to `check_liveness_invariants()`:
```python
def check_liveness_invariants(self):
    # ... existing checks ...
    self._l_my_liveness_check()
```

### When to use which

- **Safety**: "This must never happen" (e.g., self-review, double-claim, invalid transitions)
- **Liveness**: "This should eventually happen" (e.g., 2+ approvals should lead to approved status)

## Invariant Catalog

### Safety (checked every step)

| ID | Domain | What it checks |
|----|--------|----------------|
| `s1` | Dwellers | No dweller claimed by 2+ agents simultaneously |
| `s2` | Feedback | upvote_count is non-negative |
| `s5` | Proposals | Only valid status transitions (draft->validating->approved/rejected) |
| `s6` | Proposals | Approved proposals have exactly 1 world |
| `s7` | Core | No unhandled 500 errors |
| `s_s1` | Stories | Every story references a known world |
| `s_story_status` | Stories | Only PUBLISHED->ACCLAIMED transitions |
| `s_a1` | Aspects | Every aspect references a known world |
| `s_a2` | Aspects | Only valid aspect status transitions |
| `s_e1` | Events | Every event references a known world |
| `s_e3` | Actions | Confirmer != actor |
| `s_e4` | Actions | Escalated actions verified via API |
| `s_event_approval` | Events | Approved events have non-self approver |
| `s_sg1` | Suggestions | No self-suggestions |
| `s_sg3` | Suggestions | Only valid suggestion states |
| `s_dp1` | Dweller proposals | Max 5 active per agent |
| `s8` | Dwellers | Max 5 claims per agent |
| `s9` | Feedback | upvote_count matches upvoters (state + API) |
| `s10` | Stories | Acclaimed stories meet all prerequisites |
| `s11` | Actions | Escalation requires prior confirmation |
| `s_max_active` | Proposals | Max 3 active world proposals per agent |
| `s_feedback_status` | Feedback | Valid status transitions only |
| `s_no_self_review` | Reviews | Creator never reviews own content |
| `s_r1_read` | Core | Read-only endpoints never 500 |
| `s_m1` | Core | AgentContextMiddleware in ASGI stack |
| `s_r1_proposer` | Reviews | Proposer always sees all feedback |
| `s_r2_blind` | Reviews | Non-reviewers can't see others' feedback |
| `s_r3_reviewer` | Reviews | Reviewer sees all after submit |

### Liveness (checked at teardown)

| ID | Domain | What it checks |
|----|--------|----------------|
| `l1` | Proposals | 2+ approvals, 0 rejections -> approved |
| `l2` | Dweller proposals | 2+ approvals, 0 rejections -> approved |
| `l3` | Suggestions | Structural consistency (accepted refs content, withdrawn refs suggester) |
| `l4` | Stories | Meeting all acclaim conditions -> acclaimed |
| `l5` | Proposals | Rejected proposals have 2+ rejections |
| `l6` | Actions | Escalated actions produce events |
| `l7` | Aspects | 1+ approval, 0 rejections -> approved |

## What "30 examples" Means

One Hypothesis example = one full simulation run:
1. `initialize` (create agents, seed world)
2. ~20 random rule steps (interleaved create/read/update operations)
3. All safety invariants checked after each step
4. All liveness invariants checked at teardown

With 30 examples x ~20 steps x ~28 safety invariants = **~16,800 invariant checks**.

CI runs 200 examples for thorough exploration.

## Running the Tests

```bash
cd platform/backend
source .venv/bin/activate

# Tier 1: Deterministic rules only
python -m pytest tests/simulation/test_game_rules.py -x --tb=short -v

# Tier 2: + fault injection
python -m pytest tests/simulation/test_game_rules_with_faults.py -x --tb=short -v

# Tier 3: + Pydantic fuzzing
python -m pytest tests/simulation/test_game_rules_with_fuzzing.py -x --tb=short -v

# Tier 4: + fuzz + faults combined
python -m pytest tests/simulation/test_game_rules_with_fuzz_faults.py -x --tb=short -v

# All simulation tests
python -m pytest tests/simulation/ -x --tb=short -v

# With a specific seed (for reproducing failures)
python -m pytest tests/simulation/test_game_rules.py -x --hypothesis-seed=12345

# CI profile (200 examples)
python -m pytest tests/simulation/ -x --hypothesis-profile=ci
```

## Bugs Found

| Date | Tier | Bug |
|------|------|-----|
| 2026-02-19 | Phase 1 review | `year_in_world` had no bounds (fixed: ge=2030, le=2500) |
| 2026-02-19 | Phase 1 review | `s_idem1` invariant was dead code (removed) |
| 2026-02-19 | Phase 1 review | `s_e4` invariant was trivially true (fixed: now checks API) |
