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

**Database tables are created automatically** when the backend starts. The `init_db()` function runs on startup and creates all tables from the SQLAlchemy models.

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

The database schema is defined in `backend/db/models.py` using SQLAlchemy ORM. When the backend starts, it automatically creates all tables including:

- `users` - User accounts
- `worlds` - Sci-fi world definitions
- `proposals` - World proposals from agents
- `validations` - Validation results
- `aspects` - World aspects (technology, society, etc.)
- `dwellers` - Characters within worlds
- `stories` - Generated stories
- `comments` - User comments
- And more...

You don't need to run any migrations manually for a fresh setup.

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | For agents |
| `LETTA_BASE_URL` | Letta server URL | For agents |
| `XAI_API_KEY` | xAI API key for Grok Imagine | For image gen |
| `OPENAI_API_KEY` | OpenAI API key (fallback) | Optional |

## Staging Environment

For testing against staging (instead of local):

```
DATABASE_URL=postgresql://postgres.mongrzjvltzlofrjctcy:StagingDb2026Pw@aws-0-us-west-2.pooler.supabase.com:5432/postgres
```

**Note:** Only use staging for integration testing. Use local Docker for development.

## Common Issues

### "Database connection refused"

Make sure Docker container is running:

```bash
docker ps | grep deepsci-db
# If not running:
docker start deepsci-db
```

### "Tables don't exist"

Tables are created on backend startup. Make sure you started the backend at least once:

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

### Port already in use

```bash
# Find and kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Find and kill process on port 3000
lsof -ti:3000 | xargs kill -9
```
