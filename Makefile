.PHONY: test-dst

# Run DST (Deterministic Stateful Tests) against a containerized Postgres.
# Requires Docker to be running. testcontainers spins up Postgres automatically.
test-dst:
	@docker info > /dev/null 2>&1 || (echo "ERROR: Docker is not running. Start Docker and try again." && exit 1)
	cd platform/backend && python -m pytest tests/simulation/ -x --tb=short
