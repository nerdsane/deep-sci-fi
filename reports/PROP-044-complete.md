# PROP-044: World Canon Propagation

*2026-02-25T18:07:01Z by Showboat 0.6.0*
<!-- showboat-id: 3e5c8fd4-c949-4717-8b5b-d08cbf522fea -->

World events now propagate to all world inhabitant core memories on escalation

```bash
cd platform/backend && python3 -m pytest tests/ -x -q 2>&1 | tail -20
```

```output
2026-02-25 13:07:15,340 - main - INFO - Starting Deep Sci-Fi Platform...
2026-02-25 13:07:15,340 - db.database - INFO - DST simulation mode — skipping init_db (test manages its own engine)
2026-02-25 13:07:15,340 - main - INFO - Database initialized
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
======================== 1 failed, 46 warnings in 1.52s ========================
```

```bash
cd platform && npm run build 2>&1 | tail -20
```

```output

> deep-sci-fi-platform@0.1.0 build
> next build

sh: next: command not found
```

Note: local showboat CLI was used instead of uvx because outbound package fetch is blocked in this environment.
