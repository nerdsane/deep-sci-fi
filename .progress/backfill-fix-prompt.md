# Fix: Relationship Backfill Bugs

Two bugs preventing the backfill from running. Fix both.

## Bug 1: float / Decimal in relationship_service.py

**File:** `platform/backend/utils/relationship_service.py`

In `_recompute_scores_for_dwellers()`, the line:
```python
max_raw = max_result.scalar() or 1.0
```
...returns a PostgreSQL `Decimal` (not a Python float), because the SUM expression on integer columns returns NUMERIC in Postgres. Then:
```python
rel.combined_score = round(_raw_score(rel) / max_raw, 6)
```
...fails with `TypeError: unsupported operand type(s) for /: 'float' and 'decimal.Decimal'`.

**Fix:** Cast to float explicitly:
```python
max_raw = float(max_result.scalar() or 1.0)
```

That single line change in `_recompute_scores_for_dwellers()`. Nothing else needs to change.

## Bug 2: statement_cache_size=0 missing from backfill script

**File:** `scripts/materialize_relationships_and_arcs.py`

The script creates an engine:
```python
engine = create_async_engine(database_url, echo=False)
```

Supabase uses PgBouncer in transaction mode, which doesn't support prepared statements. Need to add `statement_cache_size=0` in `connect_args`:

```python
engine = create_async_engine(
    database_url,
    echo=False,
    connect_args={"statement_cache_size": 0},
)
```

## Steps

1. Fix `platform/backend/utils/relationship_service.py` — the `float()` cast
2. Fix `scripts/materialize_relationships_and_arcs.py` — add `connect_args`
3. Run the existing test suite: `cd platform/backend && python -m pytest tests/ -x -q 2>&1 | tail -20`
4. Commit to staging branch: `git checkout staging && git add -A && git commit -m "fix: float/Decimal score normalization + backfill statement_cache_size"`
5. Merge to main: `git checkout main && git merge staging && git push origin main`

## Showboat

After the fix and commit, create a minimal showboat doc:

```bash
uvx showboat init reports/backfill-fix-complete.md "Backfill Bug Fixes"
uvx showboat note reports/backfill-fix-complete.md "Two bugs prevented relationship backfill from running. Fixed float/Decimal type mismatch in score normalization and added statement_cache_size=0 for Supabase PgBouncer compatibility."
uvx showboat exec reports/backfill-fix-complete.md bash "cd platform/backend && python -m pytest tests/ -x -q 2>&1 | tail -15"
```

DO NOT COMMIT until both fixes are in and tests pass.
DO NOT CREATE showboat doc until commit is done.
