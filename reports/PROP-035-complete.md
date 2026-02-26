# PROP-035: Arc Intelligence

## Notes
- Added momentum classification, days-since, health scoring, and AI summary generation plumbing for arcs.
- Added full arc detail page at `/arcs/[id]` with timeline, metadata, story thumbnails/timestamps, and related arcs in the same world.
- Added focused backend tests for momentum and health signal logic.

## Showboat Command Attempts
`uvx showboat` could not run in this sandbox because network access to PyPI is blocked (`Failed to fetch https://pypi.org/simple/showboat/`).

## Backend Test Tail
```text
/opt/homebrew/Cellar/python@3.14/3.14.3_1/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py:1143: in create_connection
    sock = await self._connect_sock(
/opt/homebrew/Cellar/python@3.14/3.14.3_1/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/base_events.py:1042: in _connect_sock
    await self.sock_connect(sock, address)
/opt/homebrew/Cellar/python@3.14/3.14.3_1/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/selector_events.py:645: in sock_connect
    return await fut
           ^^^^^^^^^
/opt/homebrew/Cellar/python@3.14/3.14.3_1/Frameworks/Python.framework/Versions/3.14/lib/python3.14/asyncio/selector_events.py:653: in _sock_connect
    sock.connect(address)
E   PermissionError: [Errno 1] Operation not permitted
=============================== warnings summary ===============================
../../../../../../../opt/homebrew/lib/python3.14/site-packages/slowapi/extension.py:717: 46 warnings
  /opt/homebrew/lib/python3.14/site-packages/slowapi/extension.py:717: DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16; use inspect.iscoroutinefunction() instead
    if asyncio.iscoroutinefunction(func):

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
ERROR tests/test_arcs.py::TestAssignStoryToArc::test_first_story_creates_arc
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
====== 5 passed, 2 skipped, 357 deselected, 46 warnings, 1 error in 0.52s ======
```

## Frontend Build Tail
```text
> deep-sci-fi-platform@0.1.0 build
> next build

sh: next: command not found
```

## Additional Validation Run
```text
cd platform/backend && python3 -m pytest tests/test_arcs.py -q -k ArcIntelligenceSignals

================= 5 passed, 7 deselected, 25 warnings in 0.04s =================
```
