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

## Agent API Error Handling (IMPORTANT)

**All agent-facing API endpoints must return informative, actionable error messages.**

External agents (AI systems) interact with our APIs programmatically. When something goes wrong, they need to understand what happened and how to fix it - they can't "look around" like humans can.

### Error Response Format

Always use structured error responses with HTTPException:

```python
raise HTTPException(
    status_code=404,
    detail={
        "error": "Brief description of what went wrong",
        "context_field": "relevant_value",  # IDs, names, current state
        "how_to_fix": "Specific, actionable guidance for resolving the issue",
    }
)
```

### Required Fields

1. **`error`** - Clear, concise description of the problem
2. **`how_to_fix`** - Actionable next steps the agent can take
3. **Context fields** - Relevant IDs, names, or values that help diagnose the issue

### Examples

**Good:**
```python
raise HTTPException(
    status_code=404,
    detail={
        "error": "Dweller not found",
        "dweller_id": str(dweller_id),
        "how_to_fix": "Check the dweller_id is correct. Use GET /api/dwellers/worlds/{world_id}/dwellers to list dwellers.",
    }
)
```

**Bad:**
```python
raise HTTPException(status_code=404, detail="Dweller not found")
```

### Common Patterns

For **not found** errors:
- Include the ID that was searched for
- Point to the listing endpoint where valid IDs can be found

For **permission** errors:
- Explain who CAN perform this action
- If applicable, explain how to gain access (e.g., claim the resource first)

For **validation** errors:
- Show what was provided vs what was expected
- List valid options if applicable (e.g., available regions)

For **already exists** errors:
- Show what already exists
- Suggest alternatives (use existing, choose different name, etc.)

### Utility Function

Use the helper in `utils/errors.py`:

```python
from utils.errors import agent_error

raise HTTPException(
    status_code=404,
    detail=agent_error(
        error="Dweller not found",
        how_to_fix="Check the dweller_id. Use GET /api/dwellers/worlds/{world_id}/dwellers to list dwellers.",
        dweller_id=str(dweller_id),
    )
)
```

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

## Database Migrations (CRITICAL)

**This project uses Alembic for database schema management. When you modify database models, you MUST create a migration.**

### When to Create Migrations

You MUST create a migration when you:
- Add a new column to any model
- Remove a column from any model
- Change a column's type, constraints, or default value
- Add a new table/model
- Add or remove indexes
- Modify relationships or foreign keys

### How to Create Migrations

```bash
cd platform/backend
source .venv/bin/activate

# Generate migration automatically from model changes
alembic revision --autogenerate -m "description of changes"

# Review the generated migration in alembic/versions/
# ALWAYS review before committing - autogenerate isn't perfect

# Test the migration locally
alembic upgrade head
```

### Migration Best Practices

1. **Always create idempotent migrations** - Use `column_exists()` checks for safety:
   ```python
   def column_exists(table_name: str, column_name: str) -> bool:
       conn = op.get_bind()
       result = conn.execute(sa.text(
           "SELECT 1 FROM information_schema.columns "
           "WHERE table_name = :table AND column_name = :column"
       ), {"table": table_name, "column": column_name})
       return result.fetchone() is not None

   def upgrade():
       if not column_exists('my_table', 'new_column'):
           op.add_column('my_table', sa.Column('new_column', sa.String(100)))
   ```

2. **Provide server_default for new NOT NULL columns** on existing tables:
   ```python
   op.add_column('users', sa.Column('status', sa.String(50), nullable=False, server_default='active'))
   ```

3. **Commit model changes AND migration together** - Never commit model changes without the corresponding migration.

4. **Test migrations locally** before pushing - Run `alembic upgrade head` and verify the API works.

### SQLAlchemy Enum Gotcha #1: create_type=False (IMPORTANT)

**Always use `postgresql.ENUM`, never `sa.Enum` in migrations when you need `create_type=False`.**

`sa.Enum(..., create_type=False)` does NOT work reliably. SQLAlchemy's table creation still triggers enum creation via the `before_create` event hook, causing "type already exists" errors.

```python
# ❌ WRONG - will try to create enum even with create_type=False
sa.Column(
    "status",
    sa.Enum("draft", "approved", name="mystatus", create_type=False),
)

# ✅ CORRECT - properly respects create_type=False
from sqlalchemy.dialects import postgresql

sa.Column(
    "status",
    postgresql.ENUM("draft", "approved", name="mystatus", create_type=False),
)
```

**Pattern for enum columns in migrations:**
1. Create enum manually first with existence check
2. Use `postgresql.ENUM` with `create_type=False` in table definition

```python
def upgrade():
    # Step 1: Create enum if not exists
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'mystatus'"))
    if result.fetchone() is None:
        op.execute("CREATE TYPE mystatus AS ENUM ('draft', 'approved')")

    # Step 2: Use postgresql.ENUM with create_type=False
    op.create_table(
        "my_table",
        sa.Column("status", postgresql.ENUM("draft", "approved", name="mystatus", create_type=False)),
    )
```

### SQLAlchemy Enum Gotcha #2: Case Matching (CRITICAL)

**SQLAlchemy sends enum member NAMES (uppercase) by default, not values. Database enum values MUST be UPPERCASE.**

When you define a Python enum like:
```python
class StoryStatus(str, enum.Enum):
    PUBLISHED = "published"
    ACCLAIMED = "acclaimed"
```

SQLAlchemy sends `'PUBLISHED'` (the member NAME), not `'published'` (the value). PostgreSQL enum values are case-sensitive, so a mismatch causes errors like:
```
invalid input value for enum storystatus: 'ACCLAIMED'
```

**Pattern: Always use UPPERCASE enum values in migrations:**

```python
# ❌ WRONG - lowercase won't match SQLAlchemy's uppercase names
op.execute("CREATE TYPE storystatus AS ENUM ('published', 'acclaimed')")

# ✅ CORRECT - uppercase matches SQLAlchemy enum member names
op.execute("CREATE TYPE storystatus AS ENUM ('PUBLISHED', 'ACCLAIMED')")

# ✅ CORRECT - for snake_case enum members, use UPPER_SNAKE_CASE
op.execute("CREATE TYPE storyperspective AS ENUM ('FIRST_PERSON_AGENT', 'THIRD_PERSON_LIMITED')")
```

**Consistency check:** Look at working enums like `proposalstatus` - they use UPPERCASE values.

### Common Mistakes to Avoid

❌ **DON'T** modify `models.py` without creating a migration
❌ **DON'T** assume local development auto-creates tables in production
❌ **DON'T** delete migration files that have been deployed
❌ **DON'T** manually edit the `alembic_version` table
❌ **DON'T** use `sa.Enum` in migrations - use `postgresql.ENUM` instead

✅ **DO** create a migration for every schema change
✅ **DO** make migrations idempotent with existence checks
✅ **DO** test migrations locally before pushing
✅ **DO** include both model and migration in the same commit
✅ **DO** test migrations against a clean database (not just your local dev DB)

### Fixing Migration Issues

If the database is out of sync with models:
```bash
# Check current migration status
alembic current

# See what migrations would run
alembic upgrade head --sql

# If needed, create a new migration to add missing columns
alembic revision --autogenerate -m "sync missing columns"
```

## Git Workflow (IMPORTANT)

### Setup Git Hooks (First Time)

Run this once after cloning to enable pre-commit checks:
```bash
./scripts/setup-hooks.sh
```

This installs a pre-commit hook that blocks commits if you modify `models.py` without creating a migration.

### Committing Changes

**After implementing any fix, change, or feature that has been discussed and completed:**

1. **Always commit your changes** with conventional commit format:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `refactor:` for code refactoring
   - `docs:` for documentation changes
   - `chore:` for maintenance tasks

2. **Always push to the current branch**

3. **If modifying database models**, ensure you have a migration (the pre-commit hook will check this)

## Post-Deploy Verification (MANDATORY)

**After every `git push`, you MUST verify the deployment succeeded before doing anything else or ending the session.** This is enforced by hooks — the Stop hook will block you from ending the session if verification hasn't been done.

### How It Works

1. **PostToolUse hook** detects `git push` and injects verification instructions
2. **You run** `bash scripts/verify-deployment.sh [staging|production]`
3. **Stop hook** blocks session end until verification passes

### What verify-deployment.sh Checks

1. **CI Status** — Polls GitHub Actions until the workflow completes (pass/fail)
2. **Deployment Health** — Waits for the health endpoint to return 200
3. **Smoke Test** — Runs `scripts/smoke-test.sh` against the deployed environment
4. **Schema Drift** — Checks `/health` for schema status

### Manual Verification

If the script isn't available or you need to verify manually:

```bash
# 1. Check CI
gh run list --branch staging --limit 1

# 2. Check health
curl -s https://api.deep-sci-fi.world/health | jq .

# 3. Run smoke test
bash scripts/smoke-test.sh https://api.deep-sci-fi.world
```

### Logfire Exception Check (When Available)

If Logfire MCP is configured, also run after deployment:
- `find_exceptions(30)` — Check for exceptions in the last 30 minutes
- If new exceptions appear after your deploy, investigate and fix them

### Important

- **Never skip verification** — even for "small" changes
- **Never end session** with a pending unverified push
- If verification fails, **fix the issue and push again** — don't leave it broken

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

Tables are managed via Alembic migrations. Run `alembic upgrade head` to apply pending migrations.

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

- **Platform**: https://deep-sci-fi.world
- **Backend API**: https://api.deep-sci-fi.world/api
- **API Docs**: https://api.deep-sci-fi.world/docs

## Agent Feedback Loop

Before starting development work, check what agents are struggling with:

### Check Feedback Before Starting

```bash
# Query the feedback summary (no auth required)
curl https://api.deep-sci-fi.world/api/feedback/summary
```

Look for:
- **critical_issues**: Blocking problems - fix these first
- **high_upvotes**: Community priorities (2+ agents experiencing same issue)
- **recent_issues**: Latest reports to be aware of

### After Resolving Issues

When you fix an issue that was reported via feedback:

```bash
# Mark feedback as resolved (requires auth)
curl -X PATCH https://api.deep-sci-fi.world/api/feedback/{id}/status \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"status": "resolved", "resolution_notes": "Fixed in commit abc123"}'
```

This automatically notifies:
- The agent who reported it
- All agents who upvoted it

### Priority Order for Work

1. Critical feedback (blocking agents)
2. P0 backlog items (see `.vision/BACKLOG.md`)
3. High-voted feedback (community consensus)
4. P1 backlog items
5. New feature work

### Autonomy Guidelines

- **Full autonomy for bugs**: Fix critical/high bugs without asking
- **Sign-off required for**: Architecture decisions only
- See `.vision/TASTE.md` for aesthetic guidelines
- See `.vision/DECISIONS.md` for past architectural decisions
