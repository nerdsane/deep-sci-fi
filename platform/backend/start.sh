#!/bin/bash
# Railway startup script
# Single idempotent migration handles both fresh and existing databases.
#
# Strategy:
# - Fresh DB: alembic upgrade head creates everything
# - Existing DB with stale alembic_version: fix version, then upgrade (idempotent no-op)

set -e

echo "Checking database state..."
python3 -c "
import asyncio, os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def fix_alembic_version():
    url = os.getenv('DATABASE_URL', 'postgresql://deepsci:deepsci@localhost:5432/deepsci')
    if url.startswith('postgresql://'):
        url = url.replace('postgresql://', 'postgresql+asyncpg://')
    if '?' in url:
        url = url.split('?')[0]

    import ssl
    connect_args = {}
    if 'supabase' in url or 'pooler' in url:
        connect_args['statement_cache_size'] = 0
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        connect_args['ssl'] = ssl_ctx

    engine = create_async_engine(url, connect_args=connect_args)
    async with engine.begin() as conn:
        # Check if alembic_version exists with a stale revision
        try:
            result = await conn.execute(text('SELECT version_num FROM alembic_version'))
            row = result.fetchone()
            if row and not row[0].startswith('000'):
                # Stale revision from old hash-based migrations - reset to 0001
                # so alembic upgrade head runs all numbered migrations in order
                await conn.execute(text(\"UPDATE alembic_version SET version_num = '0001'\"))
                print(f'Fixed stale alembic version: {row[0]} -> 0001')
            elif row:
                print('Alembic version already current.')
            else:
                print('Alembic version table empty, migrations will handle it.')
        except Exception:
            # Table doesn't exist yet (fresh DB) - that's fine
            print('Fresh database detected.')

    await engine.dispose()

asyncio.run(fix_alembic_version())
"

echo "Running database migrations..."
alembic upgrade head
echo "Database ready."

# Fetch skill.md for version detection (Railway root is backend/ only)
curl -sf https://deep-sci-fi.world/skill.md -o skill.md && echo "Fetched skill.md" || echo "Could not fetch skill.md, version detection disabled"

echo "Starting uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port $PORT
