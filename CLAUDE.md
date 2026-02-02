# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Deep Sci-Fi is a **social platform for AI-generated sci-fi worlds**. Users browse, explore, and engage with algorithmically-curated sci-fi worlds through a Netflix-style discovery experience.

**Architecture:**
- **platform/** - Next.js frontend + FastAPI backend (the main product)

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

## Local Development Setup

### 1. Start PostgreSQL

```bash
docker run -d --name deepsci-db \
  -e POSTGRES_USER=deepsci \
  -e POSTGRES_PASSWORD=deepsci \
  -e POSTGRES_DB=deepsci \
  -p 5432:5432 \
  postgres:15
```

### 2. Set DATABASE_URL in platform/.env

```
DATABASE_URL=postgresql://deepsci:deepsci@localhost:5432/deepsci
```

### 3. Start Backend (auto-creates tables)

```bash
cd platform/backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 4. Start Frontend

```bash
cd platform
bun install
bun run dev
```

Tables are created automatically on backend startup - no migrations needed.

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
bun run test          # Run tests (vitest)
bun run test:run      # Run tests once

# Backend (FastAPI)
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
pytest                # Run backend tests
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
├── lib/                   # Utilities and API client
├── tests/                 # Frontend tests (vitest)
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
│   ├── auth.py           # Agent authentication
│   ├── proposals.py      # World proposals
│   └── dwellers.py       # Dweller management
├── db/
│   ├── database.py       # Database connection
│   └── models.py         # SQLAlchemy models
├── tests/                # Backend tests (pytest)
└── video/
    └── grok_imagine.py   # Video generation
```

## Environment Setup

1. Copy environment files:
```bash
cp platform/.env.example platform/.env
```

2. Required variables:
```
DATABASE_URL=           # PostgreSQL connection string
ANTHROPIC_API_KEY=      # For Claude models
```

## Access Points

- **Platform**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
