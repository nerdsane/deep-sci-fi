# Deploy to Vercel + Railway + Supabase

**Created:** 2026-01-31
**Status:** IN_PROGRESS

---

## Goal

Deploy the full Deep Sci-Fi platform to production:
- **Frontend (Next.js)** → Vercel
- **Backend (FastAPI)** → Railway
- **Letta Server** → Railway
- **Platform DB** → Supabase (project 1)
- **Letta DB** → Supabase (project 2, with pgvector)

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│     Vercel      │     │     Railway     │
│   (Next.js)     │────▶│   (FastAPI)     │
│  deep-scifi.app │     │   /api/*        │
└────────┬────────┘     └────────┬────────┘
         │                       │
         │              ┌────────┴────────┐
         │              │     Railway     │
         │              │  (Letta Server) │
         │              │   port 8283     │
         │              └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│    Supabase     │     │    Supabase     │
│  Platform DB    │     │    Letta DB     │
│  (project 1)    │     │   (pgvector)    │
└─────────────────┘     └─────────────────┘
```

---

## Phases

### Phase 1: Supabase Setup ⬜
- [ ] Create Supabase project: `deep-scifi-platform`
- [ ] Create Supabase project: `deep-scifi-letta`
- [ ] Enable pgvector extension on letta project
- [ ] Run Drizzle migrations on platform DB
- [ ] Get connection strings

### Phase 2: Backend Prep ✅
- [x] Create Dockerfile for FastAPI backend
- [x] Create railway.toml for backend
- [x] Update CORS for production domains (reads from CORS_ORIGINS env)
- [x] Update database connection for async Supabase (pgbouncer compatible)

### Phase 3: Railway Deployment ⬜
- [ ] Deploy FastAPI backend to Railway
- [ ] Deploy Letta server to Railway
- [ ] Configure environment variables
- [ ] Verify health endpoints

### Phase 4: Vercel Deployment ⬜
- [ ] Create vercel.json if needed
- [ ] Configure environment variables
- [ ] Deploy to Vercel
- [ ] Update API routes to point to Railway backend

### Phase 5: Integration & Testing ⬜
- [ ] Test full flow: frontend → backend → Letta → DBs
- [ ] Configure custom domain (if any)
- [ ] Verify CORS working correctly

---

## Environment Variables Needed

### Vercel (Next.js)
```
DATABASE_URL=postgresql://... (Supabase platform)
NEXT_PUBLIC_API_URL=https://backend.railway.app
```

### Railway (FastAPI)
```
DATABASE_URL=postgresql://... (Supabase platform)
LETTA_BASE_URL=http://letta-server.railway.internal:8283
ANTHROPIC_API_KEY=...
XAI_API_KEY=...
```

### Railway (Letta)
```
LETTA_PG_URI=postgresql://... (Supabase letta)
ANTHROPIC_API_KEY=...
```

---

## Files to Create/Modify

1. `platform/backend/Dockerfile` - Containerize FastAPI
2. `platform/backend/railway.json` - Railway config
3. `platform/vercel.json` - Vercel config (if needed)
4. `platform/backend/main.py` - Update CORS for production
5. `platform/drizzle.config.ts` - Ensure works with Supabase

---

## Files Created

- `platform/backend/Dockerfile` - FastAPI container
- `platform/backend/.dockerignore` - Docker ignore rules
- `platform/backend/railway.toml` - Railway deployment config
- `platform/vercel.json` - Vercel deployment config
- `deploy/DEPLOYMENT.md` - Step-by-step deployment guide
- `deploy/railway-letta.toml` - Letta Railway config reference

## Code Changes

- `platform/backend/main.py` - CORS now reads from CORS_ORIGINS env var
- `platform/backend/db/database.py` - Supabase pgbouncer compatibility
- `platform/lib/db/index.ts` - Serverless-optimized Postgres client

## Findings

- Supabase uses pgbouncer which requires `prepared_statement_cache_size=0` for asyncpg
- postgres.js needs `prepare: false` for Supabase pooler
- Railway internal networking uses `.railway.internal` domain
- Vercel sets `VERCEL=1` env var, useful for detecting serverless context

