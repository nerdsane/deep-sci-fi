# Property-Based API Testing

**Status: COMPLETE — All 3 DST test suites passing**

## Implementation Summary

### Files Created

1. **`platform/backend/tests/simulation/pydantic_strategies.py`** (~170 lines)
   - `from_model(model_cls, overrides={})` — generates Hypothesis strategies from Pydantic models
   - `serialize(data)` — converts UUIDs, enums to JSON-serializable form
   - Reads `model_fields` metadata: `MinLen`, `MaxLen`, `Ge`, `Le`, enum members, nested models
   - Uses readable text alphabet (no random bytes)
   - Overrides accept concrete values OR Hypothesis strategies

2. **`platform/backend/tests/simulation/test_game_rules_with_fuzzing.py`** (~280 lines)
   - `FuzzedGameRules(DeepSciFiGameRules)` — inherits all 49+ rules + 20 safety + 7 liveness invariants
   - 10 fuzz rules: `fuzz_create_proposal`, `fuzz_create_feedback`, `fuzz_add_region`, `fuzz_create_dweller`, `fuzz_create_story`, `fuzz_create_aspect`, `fuzz_create_event`, `fuzz_submit_review`, `fuzz_validate_proposal`, `fuzz_revise_proposal`
   - Settings: `max_examples=30`, `stateful_step_count=20`

### Files Modified

3. **`platform/backend/tests/simulation/conftest.py`** (2 fixes)
   - `_teardown_db`: replaced DROP/CREATE with TRUNCATE CASCADE (avoids enum duplication errors between Hypothesis examples)
   - `_create_engine_and_setup`: added admin user bootstrap (User + ApiKey records for test-admin-key)

### Verification Results

- All 10 fuzz rules import and register correctly
- 140 total methods on FuzzedGameRules (inherited + fuzz)
- Boundary values verified: year_setting hits [2030, 2500], age hits [0, 200]
- Full enum coverage: 6/6 FeedbackCategory, 4/4 FeedbackPriority
- All Pydantic models generate valid data
- **test_game_rules.py** — PASSED (12.51s)
- **test_game_rules_with_faults.py** — PASSED (14.28s)
- **test_game_rules_with_fuzzing.py** — PASSED (8.70s)

### Pre-existing DST Infrastructure Issues (FIXED)

1. **Enum duplication between Hypothesis examples**: `_teardown_db` used `drop_all` which removed tables but not enum types. `create_all` then tried `CREATE TYPE` without `IF NOT EXISTS`. Fixed by using `TRUNCATE CASCADE` — keeps schema intact, only clears data.

2. **Missing admin user after TRUNCATE**: `ArcRulesMixin.detect_arcs()` uses `_admin_headers()` but `get_admin_user()` needs a DB record. Fixed by bootstrapping admin User + ApiKey in `_create_engine_and_setup`.

---

## Original Design Document

**Inspired by:** [Bombadil](https://github.com/antithesishq/bombadil) (Antithesis) — property-based fuzzing for web UIs.
**Our version:** The same concept applied to backend APIs, using tools we already have.

### What This Catches That Current DST Doesn't

| Bug Class | Current DST (always same data) | With Fuzzing |
|-----------|-------------------------------|--------------|
| Year boundaries (2030, 2500) | Never (always 2089) | Tested at ge/le bounds |
| Max-length strings | Never (~80 chars) | Generated up to max_length |
| All enum values | 1 value per enum | All variants sampled |
| Min-length boundary | Never (always well over) | Strings at exact min_length |
| Empty optional fields | Always populated | Sometimes None |
| Age boundaries (0, 200) | Always 30 | ge=0, le=200 tested |
| Diverse causal chains | Same 3 steps | Varied years, events, reasoning |
| Nested model diversity | Same structure | Varied nested content |
