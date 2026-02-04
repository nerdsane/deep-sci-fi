#!/bin/bash
# Railway startup script
# Ensures database schema is fully in sync with models.
#
# Strategy:
# 1. create_all() to ensure all tables exist (idempotent - skips existing)
# 2. Stamp alembic to base migration point (tables now exist)
# 3. Run upgrade head to apply column-level changes (all idempotent)

set -e

echo "Step 1: Creating any missing tables..."
python3 -c "
import asyncio
from db.database import engine, Base
from db import models  # register all models

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

asyncio.run(create_tables())
print('Tables synced.')
"

echo "Step 2: Running migrations for column-level changes..."
alembic stamp 93bbfb2c4512
alembic upgrade head
echo "Schema sync complete."

echo "Starting uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port $PORT
