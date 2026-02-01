# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Deep Sci-Fi is a **social platform for AI-generated sci-fi worlds**. Users browse, explore, and engage with algorithmically-curated sci-fi worlds through a Netflix-style discovery experience.

**Architecture:**
- **platform/** - Next.js frontend + FastAPI backend (the main product)
- **letta/** - Agent execution backend (submodule)
- **letta-ui/** - Agent observability dashboard (debugging tool)
- **ots/** - Open Trajectory Standard library (submodule)

## Post-Task Verification (CRITICAL)

**After completing ANY implementation task, always automatically verify:**
- No hacks or temporary workarounds left in code
- No placeholder implementations (TODO, FIXME, stub functions that don't actually work)
- No code that appears to work but doesn't actually function properly
- No silent failures (errors caught but not logged or handled)
- All error handling is explicit and appropriate
- All edge cases are properly handled
- No console.log statements left for debugging
- No commented-out code blocks
- All TypeScript types are properly defined (no `any` unless absolutely necessary)

**This verification happens automatically after task completion. User can also trigger it manually with `/no-cap` command.**

## Vision-Aligned Planning (MANDATORY)

**STOP. Before starting ANY non-trivial task (3+ steps, multi-file, or research required), you MUST follow this workflow. No exceptions.**

### Directories

```
.vision/     → Project vision documents (long-lived north star) - READ IF EXISTS
.progress/   → Timestamped task plans (per-task tracking) - CREATE BEFORE CODING
```

### Before Starting - DO THIS FIRST

1. **Check `.vision/`** - If exists, read whatever vision files are there
2. **Check `.progress/`** - Read existing plans to understand current state
3. **Create plan** - Save `.progress/NNN_YYYYMMDD_HHMMSS_task-name.md` BEFORE writing code (NNN = next sequence number)
4. **If no `.vision/`** and task is significant: Offer to help create relevant vision docs

**Planning is important, but be pragmatic.** Small fixes don't need full plans. Use judgment.

### Commands

- **`/remind`** - Refresh TigerStyle workflow in context
- `/planning-with-files` - Full workflow details
- `/no-cap` - Verify implementation quality (no hacks, placeholders, or silent failures)

## Git Workflow (IMPORTANT)

**After implementing any fix, change, or feature that has been discussed and completed:**

1. **Always commit your changes** with conventional commit format:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `refactor:` for code refactoring
   - `docs:` for documentation changes
   - `chore:` for maintenance tasks

2. **Always push to the current branch**

## Start Everything (Fresh)

When user says "start everything" - run all services fresh:

```bash
# 1. Kill existing processes
pkill -f "letta server" 2>/dev/null || true
pkill -f "uvicorn main:app" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
pkill -f "bun run dev" 2>/dev/null || true

# 2. Reset Letta DB (optional - for clean slate)
cd letta
rm -rf .persist/pgdata-test
docker compose -f dev-compose.yaml down -v
docker compose -f dev-compose.yaml up -d letta_db
sleep 5
set -a; source .env; set +a
source .venv/bin/activate
export LETTA_PG_URI="postgresql://letta:letta@localhost:5434/letta"
alembic upgrade head

# 3. Start Letta server
letta server --port 8283 --debug > /tmp/letta.log 2>&1 &

# 4. Start Backend
cd ../platform/backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000 > /tmp/backend.log 2>&1 &

# 5. Start Frontend
cd ..
bun run dev > /tmp/frontend.log 2>&1 &

# 6. Start Letta UI
cd ../letta-ui
PORT=4000 LETTA_BASE_URL=http://localhost:8283 bun run dev > /tmp/letta-ui.log 2>&1 &
```

**Access Points after startup:**
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Letta: http://localhost:8283
- Letta UI: http://localhost:4000

## Development Commands

### Platform (Next.js Frontend + FastAPI Backend)

The main product lives in `platform/`.

```bash
cd platform

# Frontend (Next.js)
bun install           # Install dependencies
bun run dev           # Start dev server (http://localhost:3000)
bun run build         # Production build
bun run typecheck     # TypeScript type checking
bun run lint          # ESLint

# Database (Drizzle ORM)
bun run db:generate   # Generate migrations
bun run db:migrate    # Run migrations
bun run db:studio     # Open Drizzle Studio

# Backend (FastAPI)
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Letta Server (Agent Backend - FROM SOURCE)

We run Letta from the submodule source (not Docker image) for development.

```bash
cd letta

# First time setup:
/opt/homebrew/opt/python@3.12/bin/python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,server]"

# Start server (also starts PostgreSQL container):
./start-letta.sh

# Or manually:
docker compose -f dev-compose.yaml up -d letta_db   # Start DB only
source .venv/bin/activate
export LETTA_PG_URI="postgresql://letta:letta@localhost:5434/letta"
letta server --port 8283 --debug
```

### Letta UI (Debugging Dashboard)

```bash
cd letta-ui
bun install
LETTA_BASE_URL=http://localhost:8283 bun run dev   # http://localhost:4000
```

## Platform Architecture

### Frontend (Next.js 14 + React 18)

```
platform/
├── app/                    # Next.js App Router
│   ├── page.tsx           # Home feed
│   ├── worlds/page.tsx    # World catalog
│   ├── world/[id]/page.tsx # World detail
│   └── api/               # API routes (proxy to backend)
├── components/
│   ├── ui/                # Base UI components
│   ├── layout/            # Header, Footer, Nav
│   ├── world/             # World-specific components
│   ├── social/            # Comments, reactions
│   ├── feed/              # Feed container
│   └── video/             # Video player
├── drizzle/               # Database schema & migrations
└── types/                 # TypeScript types
```

### Backend (FastAPI + Python)

```
platform/backend/
├── main.py                # FastAPI app entry
├── api/
│   ├── feed.py           # Feed endpoints
│   ├── worlds.py         # World CRUD
│   ├── social.py         # Social features
│   └── agents.py         # Agent API
├── agents/
│   ├── orchestrator.py   # 5-agent system coordinator
│   ├── world_creator.py  # World generation
│   ├── storyteller.py    # Story generation
│   ├── critic.py         # Quality evaluation
│   └── production.py     # Asset production
├── db/
│   ├── database.py       # Database connection
│   └── models.py         # SQLAlchemy models
└── video/
    └── grok_imagine.py   # Video generation
```

### 5-Agent System

The platform uses a multi-agent pipeline for world creation:

1. **Orchestrator** - Coordinates the pipeline
2. **World Creator** - Generates world concepts and lore
3. **Storyteller** - Creates narratives within worlds
4. **Critic** - Evaluates quality and consistency
5. **Production** - Generates final assets (images, videos)

## Environment Setup

1. Copy environment files:
```bash
cp platform/.env.example platform/.env
```

2. Required variables:
```
DATABASE_URL=           # PostgreSQL connection string
ANTHROPIC_API_KEY=      # For Claude models
LETTA_BASE_URL=         # Letta server URL (http://localhost:8283)
```

## Access Points

- **Platform**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Letta Server**: http://localhost:8283
- **Letta UI**: http://localhost:4000
- **Drizzle Studio**: http://localhost:4983

## Submodule Management

```bash
# Update submodules
git submodule update --remote --merge

# Commit updates
git add letta ots
git commit -m "chore: update submodules"
```
