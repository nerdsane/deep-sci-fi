#!/bin/bash
# Railway startup script
# Ensures database schema is in sync with models via idempotent migrations.
#
# Strategy: Stamp to the last non-idempotent migration (93bbfb2c4512),
# then run upgrade head. All migrations after that point use column_exists()
# checks so they safely skip existing columns and add missing ones.

set -e

echo "Ensuring database schema is up to date..."
alembic stamp 93bbfb2c4512
alembic upgrade head
echo "Schema sync complete."

echo "Starting uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port $PORT
