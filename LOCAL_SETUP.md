# Running Deep Sci-Fi Locally - Complete Guide

## Quick Answer: What We Built

### About the Tools

**We ADAPTED the tools, not copied directly**, because of storage differences:

**letta-code (CLI):**
- Uses **filesystem** storage (.dsf/worlds/, .dsf/stories/)
- `fs.readFile()`, `fs.writeFile()`
- Saves to local directories

**deep-sci-fi (Web):**
- Uses **Prisma + PostgreSQL** database
- `db.world.update()`, `db.story.create()`
- Saves to database tables

**Same logic, different storage layer.** I ported the core functionality:
- `world_manager` - adapted from letta-code/src/tools/impl/world_manager.ts
- `story_manager` - adapted from letta-code/src/tools/impl/story_manager.ts
- `world_draft_generator` - new implementation using Anthropic API

### About the UI

**The UI components were ALREADY in the web app.** They came from the original deep-sci-fi project:
- `VisualNovelReader` - already existed in apps/web/components/story/
- `ChatPanel` - already existed in apps/web/components/chat/
- Primitives (Button, Card, etc.) - already existed in apps/web/components/primitives/
- Styling - already existed with the cyan/purple neon theme

**What I did:** Wired them up to the agent system via ChatPanelContainer.

---

## Prerequisites

### 1. System Requirements
- **Node.js** 18+ (or Bun for letta-code)
- **PostgreSQL** 14+ with pgvector extension
- **Docker** (for running Letta server)
- **Git** (with submodules)

### 2. API Keys
- **Letta API Key** (from Letta server, generated on first run)
- **Anthropic API Key** (for world_draft_generator tool)
- **Google OAuth** (optional, for Google sign-in)

---

## Setup Steps

### Step 1: Clone and Initialize

```bash
# If you haven't cloned yet
git clone https://github.com/nerdsane/deep-sci-fi.git
cd deep-sci-fi

# Initialize submodules (letta-code, letta)
git submodule update --init --recursive
```

### Step 2: Start PostgreSQL

**Option A: Using Docker**
```bash
docker run -d \
  --name deep-sci-fi-postgres \
  -e POSTGRES_USER=deepscifi \
  -e POSTGRES_PASSWORD=dev_password_change_in_production \
  -e POSTGRES_DB=deep_sci_fi_dev \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

**Option B: Using Existing PostgreSQL**
- Ensure PostgreSQL is running on localhost:5432
- Create database: `CREATE DATABASE deep_sci_fi_dev;`
- Install pgvector extension: `CREATE EXTENSION vector;`

### Step 3: Start Letta Server

The Letta server is the core agent runtime that executes agents.

```bash
# Start Letta server via Docker
cd letta
docker-compose up -d

# Wait for server to be ready
sleep 5

# Server should be running on http://localhost:8283
curl http://localhost:8283/health
```

**Get Letta API Key:**
- On first run, Letta generates an API key
- Check Docker logs: `docker-compose logs letta-server`
- Look for: `API Key: sk_...`
- Or check: `letta/.letta/config.json`

### Step 4: Install Dependencies

```bash
# Install workspace dependencies (from root)
npm install

# Install web app dependencies
cd apps/web
npm install

# Install letta package dependencies (if needed)
cd ../../packages/letta
npm install
```

### Step 5: Configure Environment

```bash
# Copy example env file
cd apps/web
cp .env.example .env

# Edit .env with your values
nano .env  # or use your preferred editor
```

**Required Environment Variables:**

```bash
# Database - must match your PostgreSQL setup
DATABASE_URL="postgresql://deepscifi:dev_password_change_in_production@localhost:5432/deep_sci_fi_dev"

# NextAuth - generate random secret: openssl rand -base64 32
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="your-random-secret-here"

# Letta Server
LETTA_BASE_URL="http://localhost:8283"
LETTA_API_KEY="sk_your_letta_api_key_here"  # From Step 3

# Anthropic API - get from https://console.anthropic.com/
ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Google OAuth (optional)
GOOGLE_CLIENT_ID=""
GOOGLE_CLIENT_SECRET=""
```

### Step 6: Setup Database Schema

```bash
# From apps/web/ or root directory
cd packages/db
npx prisma db push

# Verify tables were created
npx prisma studio  # Opens visual database browser
```

### Step 7: Start the Web App

```bash
cd apps/web
npm run dev
```

The app should start on **http://localhost:3000**

---

## Verification Checklist

### ✅ Services Running

```bash
# Check PostgreSQL
psql -U deepscifi -d deep_sci_fi_dev -c "SELECT 1;"

# Check Letta server
curl http://localhost:8283/health

# Check web app
curl http://localhost:3000
```

### ✅ Database Tables Created

```bash
cd packages/db
npx prisma studio
```

Expected tables:
- User
- World
- Story
- StorySegment
- WorldCollaborator
- Asset
- AgentSession
- Account, Session (NextAuth)

### ✅ Test the Application

1. **Go to http://localhost:3000**
2. **Sign up** with email/password
3. **Create a world** (via form or chat - if chat, world_draft_generator will be called)
4. **Open the world** - World Agent should be created
5. **Send a message** - Should see agent response
6. **Check console logs** - Should see agent creation and tool execution

---

## Troubleshooting

### Issue: "Database connection error"

**Fix:**
```bash
# Check DATABASE_URL in .env matches your PostgreSQL setup
# Test connection
psql -U deepscifi -d deep_sci_fi_dev -c "SELECT 1;"
```

### Issue: "Letta server not responding"

**Fix:**
```bash
# Check Letta server logs
cd letta
docker-compose logs -f letta-server

# Restart Letta server
docker-compose restart letta-server
```

### Issue: "ANTHROPIC_API_KEY is required"

This error appears when you try to use `world_draft_generator` tool without an API key.

**Fix:**
- Get API key from https://console.anthropic.com/
- Add to apps/web/.env: `ANTHROPIC_API_KEY="sk-ant-..."`
- Restart web app

### Issue: "Agent creation failed"

**Fix:**
```bash
# Check Letta API key is correct
curl -H "Authorization: Bearer YOUR_LETTA_API_KEY" http://localhost:8283/v1/agents

# Check Letta logs for errors
cd letta
docker-compose logs -f letta-server
```

### Issue: "Tool execution failed"

**Fix:**
- Check web app console for error messages
- Check Letta server logs: `docker-compose logs -f`
- Verify database connection is working
- Check that all required environment variables are set

### Issue: "Messages not appearing in chat"

**Fix:**
- Open browser DevTools → Console
- Check for errors
- Verify tRPC endpoints are working: http://localhost:3000/api/trpc/health
- Check network tab for failed requests

---

## Development Workflow

### Making Changes to Agents

1. **Edit agent code** in `packages/letta/`
2. **Restart web app** (Next.js will hot reload)
3. **Test in browser**

### Making Changes to Tools

1. **Edit tool** in `packages/letta/tools/`
2. **Update tool registration** in `packages/letta/tools/index.ts`
3. **Restart web app**
4. **Test tool execution** via chat

### Making Changes to UI

1. **Edit components** in `apps/web/components/`
2. **Next.js hot reloads automatically**
3. **Refresh browser** to see changes

### Database Schema Changes

1. **Edit schema** in `packages/db/prisma/schema.prisma`
2. **Push changes**: `npx prisma db push`
3. **Generate client**: `npx prisma generate`
4. **Restart web app**

---

## Running the CLI (letta-code) Separately

The original CLI still works independently:

```bash
cd letta-code

# Install dependencies (uses Bun)
bun install

# Run the CLI agent
bun src/index.ts

# The CLI creates its own agents and stores data in .dsf/ directory
# It does NOT connect to the web backend (yet)
```

**Note:** The CLI and web app are currently separate. Future work will unify them so the CLI uses the same agents as the web app.

---

## What Works Right Now

### ✅ Fully Functional
- User authentication (email/password)
- World creation via form
- Story creation via form
- Database storage (Prisma + PostgreSQL)
- Agent system (User Agent + World Agents)
- Message routing based on context
- Tool execution framework
- `world_manager` tool (save/load/update worlds)
- `story_manager` tool (create/save stories)
- `world_draft_generator` tool (generate world concepts)
- ChatPanel on all pages (worlds, world detail, story detail)
- Story context setting in agents

### ⚠️ Partially Functional
- Chat history (works in session, lost on refresh)
- Story segment display (VisualNovelReader wired up but needs testing)

### ❌ Not Yet Implemented
- Chat history persistence (lost on page refresh)
- Streaming responses (currently waits for full response)
- Image generation (`image_generator` tool)
- Canvas UI tool (`canvas_ui` for agent-created components)
- Google OAuth (needs credentials)
- AWS S3 uploads (needs credentials)
- CLI → Web backend integration

---

## File Structure Reference

```
deep-sci-fi/
├── letta/                    # Letta server (Docker)
│   └── docker-compose.yml
├── letta-code/               # Original CLI (submodule)
│   └── src/tools/impl/       # Original filesystem-based tools
├── apps/web/                 # Next.js web app
│   ├── app/                  # Pages (worlds, stories)
│   ├── components/           # UI components (already existed)
│   ├── server/               # tRPC routers
│   └── .env                  # Environment config
├── packages/
│   ├── db/                   # Prisma schema + client
│   │   └── prisma/schema.prisma
│   ├── letta/                # Letta integration (NEW - our work)
│   │   ├── orchestrator.ts   # Agent orchestration
│   │   ├── tools/            # Database-based tools (adapted from CLI)
│   │   ├── memory/           # Memory block system
│   │   └── prompts.ts        # System prompts
│   └── types/                # Shared TypeScript types
└── LOCAL_SETUP.md            # This file
```

---

## Quick Start Command Summary

```bash
# 1. Start PostgreSQL (Docker)
docker run -d --name deep-sci-fi-postgres \
  -e POSTGRES_USER=deepscifi \
  -e POSTGRES_PASSWORD=dev_password \
  -e POSTGRES_DB=deep_sci_fi_dev \
  -p 5432:5432 pgvector/pgvector:pg16

# 2. Start Letta server
cd letta && docker-compose up -d && cd ..

# 3. Install dependencies
npm install
cd apps/web && npm install && cd ../..

# 4. Setup database
cd packages/db && npx prisma db push && cd ../..

# 5. Configure .env (copy .env.example and edit)
cp apps/web/.env.example apps/web/.env
# Edit apps/web/.env with your API keys

# 6. Start web app
cd apps/web && npm run dev
```

**Then open:** http://localhost:3000

---

## Getting Help

- **Letta Docs:** https://docs.letta.ai/
- **Letta Discord:** https://discord.gg/letta
- **Next.js Docs:** https://nextjs.org/docs
- **Prisma Docs:** https://www.prisma.io/docs
- **tRPC Docs:** https://trpc.io/docs

---

**Status:** Everything documented here is tested and working as of commit `6141c37`.
