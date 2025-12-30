#!/bin/bash

#
# DSF Stack Startup Script
# Starts: Letta Server (Docker) + optional letta-code UI
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Directories
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LETTA_DIR="$HOME/Development/letta"
LETTA_CODE_DIR="$HOME/Development/letta-code"

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   DSF Stack Startup Script                ║${NC}"
echo -e "${BLUE}║   Starting Letta + DSF Agent              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if port is in use
port_in_use() {
    lsof -i :"$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${YELLOW}[1/6] Checking prerequisites...${NC}"

if ! command_exists docker; then
    echo -e "${RED}✗ Docker not found. Please install Docker first.${NC}"
    exit 1
fi

if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
    echo -e "${RED}✗ docker-compose not found. Please install docker-compose.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker is installed${NC}"

# Check if directories exist
if [ ! -d "$LETTA_DIR" ]; then
    echo -e "${RED}✗ Letta directory not found at $LETTA_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Letta directory found${NC}"

# Check for Anthropic API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${YELLOW}⚠ ANTHROPIC_API_KEY not set in environment${NC}"

    # Check if .env exists in letta directory
    if [ -f "$LETTA_DIR/.env" ]; then
        echo -e "${GREEN}✓ Found .env file in letta directory${NC}"
    else
        echo -e "${RED}✗ No ANTHROPIC_API_KEY found. Please set it:${NC}"
        echo -e "   export ANTHROPIC_API_KEY=your_key_here"
        echo -e "   OR create $LETTA_DIR/.env with:"
        echo -e "   ANTHROPIC_API_KEY=your_key_here"
        exit 1
    fi
else
    echo -e "${GREEN}✓ ANTHROPIC_API_KEY is set${NC}"
fi

# Navigate to letta directory
cd "$LETTA_DIR"

# Check current branch
echo ""
echo -e "${YELLOW}[2/6] Checking Letta branch...${NC}"
CURRENT_BRANCH=$(git branch --show-current)

if [ "$CURRENT_BRANCH" != "evaluation-tools" ]; then
    echo -e "${YELLOW}⚠ Currently on branch: $CURRENT_BRANCH${NC}"
    echo -e "${YELLOW}⚠ Switching to evaluation-tools branch...${NC}"
    git checkout evaluation-tools
    echo -e "${GREEN}✓ Switched to evaluation-tools branch${NC}"
else
    echo -e "${GREEN}✓ Already on evaluation-tools branch${NC}"
fi

# Stop any existing containers
echo ""
echo -e "${YELLOW}[3/6] Stopping existing Letta containers...${NC}"
if docker compose -f dev-compose.yaml ps -q 2>/dev/null | grep -q .; then
    docker compose -f dev-compose.yaml down
    echo -e "${GREEN}✓ Stopped existing containers${NC}"
else
    echo -e "${GREEN}✓ No existing containers to stop${NC}"
fi

# Build and start Letta server
echo ""
echo -e "${YELLOW}[4/6] Building and starting Letta server with Docker...${NC}"
echo -e "${BLUE}This will:${NC}"
echo -e "  - Build Letta server from source (evaluation-tools branch)"
echo -e "  - Start PostgreSQL with pgvector"
echo -e "  - Expose server on http://localhost:8283"
echo ""

# Use dev-compose to build from source
docker compose -f dev-compose.yaml up -d --build

echo ""
echo -e "${GREEN}✓ Letta server starting...${NC}"

# Wait for server to be ready
echo ""
echo -e "${YELLOW}[5/6] Waiting for Letta server to be ready...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8283/v1/health >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Letta server is ready!${NC}"
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -e "${BLUE}  Waiting... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}✗ Letta server did not start within expected time${NC}"
    echo -e "${YELLOW}Check logs: docker compose -f dev-compose.yaml logs${NC}"
    exit 1
fi

# Summary
echo ""
echo -e "${YELLOW}[6/6] Startup complete!${NC}"
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Letta Stack Running                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Services:${NC}"
echo -e "  • Letta Server:  ${GREEN}http://localhost:8283${NC}"
echo -e "  • PostgreSQL:    ${GREEN}localhost:5432${NC}"
echo ""
echo -e "${BLUE}Logs:${NC}"
echo -e "  docker compose -f dev-compose.yaml logs -f"
echo ""
echo -e "${BLUE}Stop:${NC}"
echo -e "  docker compose -f dev-compose.yaml down"
echo ""

# Ask about starting letta-code
echo -e "${YELLOW}Start letta-code UI? (y/n)${NC} "
read -r START_LETTA_CODE

if [ "$START_LETTA_CODE" = "y" ] || [ "$START_LETTA_CODE" = "Y" ]; then
    if [ ! -d "$LETTA_CODE_DIR" ]; then
        echo -e "${RED}✗ letta-code directory not found at $LETTA_CODE_DIR${NC}"
    else
        echo ""
        echo -e "${YELLOW}Starting letta-code UI...${NC}"
        cd "$LETTA_CODE_DIR"

        # Start in a new terminal if possible, otherwise background
        if command_exists gnome-terminal; then
            gnome-terminal -- bash -c "cd $LETTA_CODE_DIR && bun run dev; exec bash"
            echo -e "${GREEN}✓ letta-code started in new terminal${NC}"
        elif command_exists xterm; then
            xterm -e "cd $LETTA_CODE_DIR && bun run dev; exec bash" &
            echo -e "${GREEN}✓ letta-code started in new terminal${NC}"
        else
            echo -e "${YELLOW}⚠ Starting letta-code in background...${NC}"
            echo -e "${YELLOW}⚠ Run manually in another terminal: cd $LETTA_CODE_DIR && bun run dev${NC}"
        fi
    fi
fi

# Test DSF Agent
echo ""
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${BLUE}Test DSF Agent:${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo ""
echo -e "  cd $SCRIPT_DIR"
echo -e "  python3 examples/simple_world.py"
echo ""
echo -e "${GREEN}Ready to build worlds! 🚀${NC}"
