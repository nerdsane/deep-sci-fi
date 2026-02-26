# PROP-045: Arc-Aware Context

*2026-02-25T18:09:45Z by Showboat 0.6.0*
<!-- showboat-id: ece6639b-f70a-4193-9763-fcc699735146 -->

open_threads now surfaces in act/context - agents see reply obligations and unresolved narrative threads

```bash
cd platform/backend && python3 -m pytest tests/ -x -q 2>&1 | tail -20
```

```output
2026-02-25 13:09:55,723 - main - INFO - Starting Deep Sci-Fi Platform...
2026-02-25 13:09:55,723 - db.database - INFO - DST simulation mode — skipping init_db (test manages its own engine)
2026-02-25 13:09:55,724 - main - INFO - Database initialized
------------------------------ Captured log call -------------------------------
INFO     main:main.py:107 Starting Deep Sci-Fi Platform...
INFO     db.database:database.py:239 DST simulation mode — skipping init_db (test manages its own engine)
INFO     main:main.py:109 Database initialized
INFO     main:main.py:107 Starting Deep Sci-Fi Platform...
INFO     db.database:database.py:239 DST simulation mode — skipping init_db (test manages its own engine)
INFO     main:main.py:109 Database initialized
=============================== warnings summary ===============================
../../../../../../../opt/homebrew/lib/python3.14/site-packages/slowapi/extension.py:717: 46 warnings
  /opt/homebrew/lib/python3.14/site-packages/slowapi/extension.py:717: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(func):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
FAILED tests/simulation/test_game_rules.py::TestGameRules::runTest - Permissi...
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
======================== 1 failed, 46 warnings in 1.25s ========================
```
