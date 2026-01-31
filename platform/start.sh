#!/bin/bash
# Start the Deep Sci-Fi Platform

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}         DEEP SCI-FI PLATFORM - STARTING UP           ${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo

# Check for .env file
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}Creating .env from .env.example...${NC}"
        cp .env.example .env
        echo -e "${YELLOW}Please edit .env with your API keys before continuing.${NC}"
        exit 1
    fi
fi

# Source environment variables
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check for required dependencies
echo -e "${BLUE}Checking dependencies...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command -v bun &> /dev/null; then
    echo -e "${RED}Error: Bun is not installed${NC}"
    echo "Install with: curl -fsSL https://bun.sh/install | bash"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All dependencies found${NC}"
echo

# Start PostgreSQL if not running
echo -e "${BLUE}Starting PostgreSQL...${NC}"
if docker ps --format '{{.Names}}' | grep -q 'platform-postgres'; then
    echo -e "${GREEN}✓ PostgreSQL already running${NC}"
else
    docker run -d \
        --name platform-postgres \
        -e POSTGRES_USER=letta \
        -e POSTGRES_PASSWORD=letta \
        -e POSTGRES_DB=letta \
        -p 5432:5432 \
        -v platform-pgdata:/var/lib/postgresql/data \
        postgres:16 \
        || docker start platform-postgres
    echo -e "${GREEN}✓ PostgreSQL started${NC}"
fi

# Wait for PostgreSQL
echo -e "${BLUE}Waiting for PostgreSQL...${NC}"
until docker exec platform-postgres pg_isready -U letta > /dev/null 2>&1; do
    sleep 1
done
echo -e "${GREEN}✓ PostgreSQL ready${NC}"
echo

# Install backend dependencies
echo -e "${BLUE}Installing backend dependencies...${NC}"
cd backend
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -e . 2>/dev/null || pip install -q -r requirements.txt 2>/dev/null || echo "Installing deps..."
echo -e "${GREEN}✓ Backend dependencies installed${NC}"
echo

# Initialize database
echo -e "${BLUE}Initializing database...${NC}"
python3 -c "
import asyncio
from db import init_db
asyncio.run(init_db())
print('Database initialized')
"
echo -e "${GREEN}✓ Database ready${NC}"
echo

# Start backend API server
echo -e "${BLUE}Starting backend API server...${NC}"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload > ../.backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > ../.backend.pid
cd ..
echo -e "${GREEN}✓ Backend API running at http://localhost:8000${NC}"
echo

# Install frontend dependencies
echo -e "${BLUE}Installing frontend dependencies...${NC}"
bun install --silent
echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
echo

# Start frontend dev server
echo -e "${BLUE}Starting frontend dev server...${NC}"
bun run dev > .frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > .frontend.pid
echo -e "${GREEN}✓ Frontend running at http://localhost:3000${NC}"
echo

# Print summary
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}           DEEP SCI-FI PLATFORM RUNNING                ${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo
echo -e "  ${BLUE}Frontend:${NC}  http://localhost:3000"
echo -e "  ${BLUE}API:${NC}       http://localhost:8000"
echo -e "  ${BLUE}API Docs:${NC}  http://localhost:8000/docs"
echo -e "  ${BLUE}Database:${NC}  postgresql://letta:letta@localhost:5432/letta"
echo
echo -e "${YELLOW}To seed demo data:${NC}"
echo "  cd backend && python3 scripts/seed_demo.py"
echo
echo -e "${YELLOW}To stop:${NC}"
echo "  ./stop.sh"
echo
