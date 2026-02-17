# PROP-007 Architecture: Local DST with Docker Postgres

## Approach: Testcontainers (Option 2)

Docker Compose works but requires manual lifecycle management. Testcontainers is better:
- Spins up a real Postgres container per test session
- Auto-cleanup on exit
- Same Postgres version as production (16)
- No persistent state to get stale

## Implementation

### 1. Add `testcontainers[postgres]` to dev dependencies
```
testcontainers[postgres]>=4.0
```

### 2. Create `tests/conftest.py` fixture
```python
@pytest.fixture(scope="session")
def postgres_container():
    """Spin up Postgres 16 in Docker for DST."""
    from testcontainers.postgres import PostgresContainer
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg.get_connection_url()

@pytest.fixture(scope="session")  
def test_db(postgres_container):
    """Run migrations against test Postgres, return engine."""
    engine = create_engine(postgres_container)
    # Run alembic migrations
    run_migrations(engine)
    return engine
```

### 3. Wire DST to use test DB
The existing `DeepSciFiBaseRules` creates a test client. Update it to use the testcontainers DB URL instead of expecting a pre-existing `deepsci` database.

### 4. Add `make test-dst` command
```makefile
test-dst:
	docker info > /dev/null 2>&1 || (echo "Docker not running" && exit 1)
	cd platform/backend && python -m pytest tests/simulation/ -x --tb=short
```

### 5. Update CI to match
CI already runs DST. Verify the testcontainers approach works there too (CI has Docker).

## Files Changed
- `platform/backend/pyproject.toml` — add testcontainers dep
- `platform/backend/tests/conftest.py` — add postgres fixture
- `platform/backend/tests/simulation/base.py` — use fixture DB URL
- `Makefile` — add test-dst target
- `.github/workflows/test.yml` — verify compatibility

## Risk Assessment
- **Database**: Creates ephemeral containers, never touches prod
- **Tests**: Existing tests should work unchanged (same Postgres)
- **CI**: May need Docker-in-Docker config adjustment
- **Rollback**: Remove dep + fixture, tests revert to current behavior

## Estimated Effort: 2-3 hours CC time
