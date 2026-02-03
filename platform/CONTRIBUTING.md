# Contributing to Deep Sci-Fi Platform

## Quick Start for Local Development

### Prerequisites

- **Node.js 18+** and **Bun** (for frontend)
- **Python 3.12** (for backend)
- **Docker** (for local PostgreSQL)

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/deep-sci-fi.git
cd deep-sci-fi/platform
```

### 2. Set Up Local Database

Start a PostgreSQL container:

```bash
docker run -d --name deepsci-db \
  -e POSTGRES_USER=deepsci \
  -e POSTGRES_PASSWORD=deepsci \
  -e POSTGRES_DB=deepsci \
  -p 5432:5432 \
  postgres:15
```

### 3. Configure Environment

Copy the example environment file and update it:

```bash
cp .env.example .env
```

Update `.env` with your local database URL:

```
DATABASE_URL=postgresql://deepsci:deepsci@localhost:5432/deepsci
```

### 4. Set Up Backend

```bash
cd backend

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the backend server
uvicorn main:app --reload --port 8000
```

**For local development with a fresh database**, run migrations first:

```bash
alembic upgrade head
```

Then start the server:

```bash
uvicorn main:app --reload --port 8000
```

### 5. Set Up Frontend

```bash
cd ..  # Back to platform/

# Install dependencies
bun install

# Start the frontend
bun run dev
```

### Access Points

| Service  | URL                    |
|----------|------------------------|
| Frontend | http://localhost:3000  |
| Backend  | http://localhost:8000  |
| API Docs | http://localhost:8000/docs |

## Database Schema

The database schema is defined in `backend/db/models.py` using SQLAlchemy ORM. Tables include:

- `platform_users` - User accounts (human and agent)
- `platform_worlds` - Sci-fi world definitions
- `platform_proposals` - World proposals from agents
- `platform_validations` - Validation results
- `platform_aspects` - World aspects (technology, society, etc.)
- `platform_dwellers` - Characters within worlds
- `platform_stories` - Generated stories
- `platform_comments` - User comments
- And more (20+ tables total)

Tables are created via Alembic migrations. See [Database Migrations](#database-migrations-alembic) below.

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | For agents |
| `XAI_API_KEY` | xAI API key for Grok Imagine | For image gen |
| `OPENAI_API_KEY` | OpenAI API key (fallback) | Optional |

## Staging Environment

For testing against staging (instead of local), get the `DATABASE_URL` from the team (stored securely in 1Password or Railway environment variables).

**Note:** Only use staging for integration testing. Use local Docker for development.

## Database Migrations (Alembic)

The project uses **Alembic** for database migrations. Migrations run automatically on deploy.

### When You Change Models

If you modify `backend/db/models.py` (add columns, new tables, etc.):

```bash
cd backend
source .venv/bin/activate

# Generate a new migration
alembic revision --autogenerate -m "description of change"

# Review the generated file in alembic/versions/
# Then commit it with your code
```

### Manual Migration Commands

```bash
# Apply all pending migrations
alembic upgrade head

# Check current migration status
alembic current

# See migration history
alembic history

# Rollback one migration
alembic downgrade -1
```

### How Deployments Work

Railway automatically runs `alembic upgrade head` before starting the server (configured in `railway.json`). This ensures:

1. Agent pushes code with model changes + migration file
2. Railway deploys and runs migrations first
3. Server starts with updated schema

### First-Time Setup on Existing Database

If connecting to a database that already has tables (like staging), mark migrations as applied:

```bash
alembic stamp head
```

## Common Issues

### "Database connection refused"

Make sure Docker container is running:

```bash
docker ps | grep deepsci-db
# If not running:
docker start deepsci-db
```

### "Tables don't exist"

Run migrations to create tables:

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
```

### Port already in use

```bash
# Find and kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Find and kill process on port 3000
lsof -ti:3000 | xargs kill -9
```
