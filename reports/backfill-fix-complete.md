# Backfill Bug Fixes

*2026-02-19T04:50:08Z by Showboat 0.6.0*
<!-- showboat-id: 7f2d767c-f358-4c4d-8bd1-087fc638494b -->

Two bugs prevented relationship backfill from running. Fixed float/Decimal type mismatch in score normalization and added statement_cache_size=0 for Supabase PgBouncer compatibility.

```bash
cd /Users/openclaw/workspace/Development/deep-sci-fi/platform/backend && source .venv/bin/activate && python -m pytest tests/ -x -q 2>&1 | tail -15
```

```output
________ TestValidationThreshold.test_single_approval_keeps_validating _________
tests/test_agent_round1_features.py:115: in test_single_approval_keeps_validating
    assert response.status_code == 200
E   assert 404 == 200
E    +  where 404 = <Response [404 Not Found]>.status_code
=============================== warnings summary ===============================
.venv/lib/python3.14/site-packages/slowapi/extension.py:717: 46 warnings
  /Users/openclaw/workspace/Development/deep-sci-fi/platform/backend/.venv/lib/python3.14/site-packages/slowapi/extension.py:717: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(func):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/test_agent_round1_features.py::TestValidationThreshold::test_single_approval_keeps_validating
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
================== 1 failed, 12 passed, 46 warnings in 54.99s ==================
```
