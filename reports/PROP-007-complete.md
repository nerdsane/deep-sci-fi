# Local DST with Docker Postgres (PROP-007)

*2026-02-17T21:02:02Z by Showboat 0.6.0*
<!-- showboat-id: 7450d527-464e-4af7-a7cc-6fc43f07f943 -->

Added testcontainers[postgres]>=4.0 to platform/backend/pyproject.toml dev dependencies

CI (deploy.yml) already sets TEST_DATABASE_URL explicitly — testcontainers code path is guarded by 'if not os.environ.get(TEST_DATABASE_URL)', so CI remains unchanged and continues using its postgres service container. No CI changes needed.

Installed: testcontainers-4.14.1 and docker-7.1.0 into platform/backend/.venv

Verified: conftest loads without crashing when Docker is unavailable (prints WARNING and falls back to localhost). pytest --collect-only correctly discovers 2 test items (TestGameRules + TestGameRulesWithFaults). Docker/Postgres not available in this environment — tests would require Docker to actually run.

## Final State (2026-02-17)

**What shipped:**
- `testcontainers[postgres]>=4.0` added to `pyproject.toml` (dev) and `requirements.txt`
- `tests/conftest.py` — auto-starts `pgvector/pgvector:pg15` container if `TEST_DATABASE_URL` not set; falls back gracefully (skips `@requires_postgres` tests) when Docker unavailable
- `tests/simulation/conftest.py` — same auto-start; falls back to `localhost:5432/deepsci_test` with a clear WARNING; `atexit` cleanup registered
- `Makefile` — `make test-dst` target guards on `docker info`, then runs simulation suite via pytest

**Behaviour matrix:**

| Environment | `TEST_DATABASE_URL` set? | Outcome |
|---|---|---|
| Local dev (Docker running) | No | testcontainers spins up pgvector:pg15 automatically |
| Local dev (no Docker) | No | main conftest skips `@requires_postgres`; sim conftest falls back to localhost |
| CI | Yes (service container) | testcontainers block skipped entirely — no change to CI |

**No CI changes required.** The guard `if not os.environ.get("TEST_DATABASE_URL")` ensures the existing CI postgres service container continues to be used as-is.
