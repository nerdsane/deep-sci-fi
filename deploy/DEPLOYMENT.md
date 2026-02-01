# Deep Sci-Fi Platform Deployment Guide

Deploy to Vercel (frontend) + Railway (backend + Letta) + Supabase (databases)

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐
│     Vercel      │────▶│     Railway     │
│   (Next.js)     │     │   (FastAPI)     │
│  Port 443       │     │   Port 8000     │
└────────┬────────┘     └────────┬────────┘
         │                       │
         │              ┌────────┴────────┐
         │              │     Railway     │
         │              │  (Letta Server) │
         │              │   Port 8283     │
         │              └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌─────────────────┐
│    Supabase     │     │    Supabase     │
│  Platform DB    │     │    Letta DB     │
│   (Project 1)   │     │   (pgvector)    │
└─────────────────┘     └─────────────────┘
```

---

## Step 1: Create Supabase Projects

### 1.1 Platform Database

1. Go to [supabase.com](https://supabase.com) and sign in
2. Click "New Project"
3. Settings:
   - **Name**: `deep-scifi-platform`
   - **Database Password**: Generate a strong password (save it!)
   - **Region**: Choose closest to your users (e.g., `us-west-1`)
4. Wait for project to be ready (~2 minutes)
5. Go to **Settings > Database** and copy the **Connection string (URI)**
   - Use the "Transaction" pooler for serverless (port 6543)
   - Format: `postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres`

### 1.2 Letta Database

1. Create another Supabase project:
   - **Name**: `deep-scifi-letta`
   - Same region as platform project
2. Enable pgvector extension:
   - Go to **SQL Editor**
   - Run: `CREATE EXTENSION IF NOT EXISTS vector;`
3. Copy the connection string (same format as above)

### 1.3 Run Migrations (Platform DB)

From your local machine:

```bash
cd platform

# Set the DATABASE_URL to your Supabase platform connection string
export DATABASE_URL="postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres"

# Run Drizzle migrations
bun run db:migrate
```

---

## Step 2: Deploy Backend to Railway

### 2.1 Create Railway Project

1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click "New Project" > "Deploy from GitHub repo"
3. Select your `deep-sci-fi` repository
4. Railway will detect the monorepo - select **platform/backend** as the root

### 2.2 Configure Backend Service

1. Go to the service settings
2. Set **Root Directory**: `platform/backend`
3. Railway should auto-detect the Dockerfile
4. Add environment variables:

```
DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
CORS_ORIGINS=https://your-app.vercel.app,https://deep-scifi.vercel.app
LETTA_BASE_URL=http://letta-server.railway.internal:8283
ANTHROPIC_API_KEY=sk-ant-...
XAI_API_KEY=xai-...
OPENAI_API_KEY=sk-... (optional)
```

5. Deploy and note the public URL (e.g., `https://deep-scifi-backend.up.railway.app`)

### 2.3 Deploy Letta Server

1. In the same Railway project, click "New Service"
2. Choose "Docker Image"
3. Image: `letta/letta:latest`
4. Add environment variables:

```
LETTA_PG_URI=postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-... (optional)
```

5. Expose port 8283
6. Set service name to `letta-server` (for internal networking)

### 2.4 Update Backend LETTA_BASE_URL

After Letta is deployed, update the backend's LETTA_BASE_URL:
- If using Railway internal networking: `http://letta-server.railway.internal:8283`
- If using public URL: `https://letta-server-xxx.up.railway.app`

---

## Step 3: Deploy Frontend to Vercel

### 3.1 Connect Repository

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub
2. Click "Add New Project"
3. Import your `deep-sci-fi` repository
4. Set **Root Directory**: `platform`
5. Framework should auto-detect as Next.js

### 3.2 Configure Environment Variables

Add these in Vercel's project settings:

```
DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
NEXT_PUBLIC_API_URL=https://deep-scifi-backend.up.railway.app/api
```

### 3.3 Deploy

Click "Deploy" and wait for the build to complete.

---

## Step 4: Update CORS

After getting the Vercel URL, update the Railway backend's CORS_ORIGINS:

```
CORS_ORIGINS=https://your-project.vercel.app,https://deep-scifi.vercel.app
```

---

## Environment Variables Summary

### Vercel (Next.js Frontend)

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Supabase platform DB (pooler) | `postgresql://postgres.xxx:pass@pooler.supabase.com:6543/postgres` |
| `NEXT_PUBLIC_API_URL` | Railway backend URL | `https://backend.up.railway.app/api` |

### Railway (FastAPI Backend)

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Supabase platform DB (pooler) | `postgresql://postgres.xxx:pass@pooler.supabase.com:6543/postgres` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `https://app.vercel.app` |
| `LETTA_BASE_URL` | Letta server URL | `http://letta-server.railway.internal:8283` |
| `ANTHROPIC_API_KEY` | Anthropic API key | `sk-ant-...` |
| `XAI_API_KEY` | xAI API key (for video gen) | `xai-...` |

### Railway (Letta Server)

| Variable | Description | Example |
|----------|-------------|---------|
| `LETTA_PG_URI` | Supabase letta DB | `postgresql://postgres.xxx:pass@pooler.supabase.com:6543/postgres` |
| `ANTHROPIC_API_KEY` | Anthropic API key | `sk-ant-...` |

---

## Verification Checklist

After deployment, verify each component:

- [ ] **Supabase Platform DB**: Tables created via migration
- [ ] **Supabase Letta DB**: pgvector extension enabled
- [ ] **Railway Backend**: `https://your-backend.up.railway.app/health` returns `{"status":"healthy"}`
- [ ] **Railway Letta**: `https://your-letta.up.railway.app/health` returns healthy
- [ ] **Vercel Frontend**: Homepage loads, API calls work

---

## Troubleshooting

### Database Connection Issues

- Use the **Transaction pooler** URL (port 6543) for serverless
- Ensure `?pgbouncer=true` is NOT in the URL (handled by our code)
- Check that the password doesn't have special characters that need URL encoding

### CORS Errors

- Verify CORS_ORIGINS includes your exact Vercel domain
- Include both `https://` and any custom domains

### Letta Connection Issues

- For Railway internal networking, use `.railway.internal` domain
- Ensure Letta service is named correctly for DNS resolution

---

## Cost Estimate

| Service | Free Tier | Paid Estimate |
|---------|-----------|---------------|
| Supabase (2 projects) | 500MB each | $25/mo each at scale |
| Railway (2 services) | $5 credit/mo | ~$10-20/mo |
| Vercel | 100GB bandwidth | Free for most use |

**Total**: ~$0-25/mo to start, scales with usage.
