#!/bin/bash
# Railway startup script
# Handles initial alembic setup when database was created with create_all()

set -e

# Check if alembic_version table exists
ALEMBIC_STATUS=$(alembic current 2>&1 || true)

if echo "$ALEMBIC_STATUS" | grep -q "(head)"; then
    echo "Alembic is at head. Running upgrade (no-op)..."
    alembic upgrade head
elif echo "$ALEMBIC_STATUS" | grep -q "revision"; then
    echo "Alembic version found. Running upgrade..."
    alembic upgrade head
else
    echo "No alembic version found. Database was likely created with create_all()."
    echo "Stamping current state as head..."
    alembic stamp head
    echo "Stamped. Future deployments will run migrations normally."
fi

echo "Starting uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port $PORT
