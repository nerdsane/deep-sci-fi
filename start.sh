#!/bin/bash

#
# DSF Stack Startup Script
# Starts: Letta Server (Docker) + optional letta-code UI
#

set -e

# Brand Colors - matching UI palette
CYAN='\033[38;2;0;255;204m'         # #00ffcc - main brand cyan
CYAN_BRIGHT='\033[38;2;0;255;255m'  # #00ffff - logo hover cyan
PURPLE='\033[38;2;170;0;255m'       # #aa00ff - accent purple
RED='\033[38;2;255;0;68m'           # #ff0044 - errors
NC='\033[0m' # No Color

# Directories
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LETTA_DIR="$SCRIPT_DIR/letta"
LETTA_CODE_DIR="$SCRIPT_DIR/letta-code"

echo -e "${CYAN_BRIGHT}╔════════════════════════════════════════════╗${NC}"
echo -e "${CYAN_BRIGHT}║   DSF Stack Startup Script                ║${NC}"
echo -e "${CYAN_BRIGHT}║   Starting Letta + DSF Agent              ║${NC}"
echo -e "${CYAN_BRIGHT}╚════════════════════════════════════════════╝${NC}"
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
echo -e "${PURPLE}[1/7] Checking prerequisites...${NC}"

if ! command_exists docker; then
    echo -e "${RED}✗ Docker not found. Please install Docker first.${NC}"
    exit 1
fi

if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
    echo -e "${RED}✗ docker-compose not found. Please install docker-compose.${NC}"
    exit 1
fi

echo -e "${CYAN_BRIGHT}✓ Docker is installed${NC}"

if ! command_exists bun; then
    echo -e "${PURPLE}⚠ Bun not found. Install from https://bun.sh to use Story Explorer gallery.${NC}"
else
    echo -e "${CYAN_BRIGHT}✓ Bun is installed${NC}"
fi

# Check if directories exist
if [ ! -d "$LETTA_DIR" ]; then
    echo -e "${RED}✗ Letta directory not found at $LETTA_DIR${NC}"
    exit 1
fi

echo -e "${CYAN_BRIGHT}✓ Letta directory found${NC}"

# Check for Anthropic API key in letta directory
if [ -f "$LETTA_DIR/.env" ]; then
    # Check if .env has ANTHROPIC_API_KEY
    if grep -q "ANTHROPIC_API_KEY=" "$LETTA_DIR/.env"; then
        echo -e "${CYAN_BRIGHT}✓ ANTHROPIC_API_KEY found in $LETTA_DIR/.env${NC}"
    else
        echo -e "${RED}✗ ANTHROPIC_API_KEY not found in $LETTA_DIR/.env${NC}"
        echo -e "${PURPLE}Please add to $LETTA_DIR/.env:${NC}"
        echo -e "   ANTHROPIC_API_KEY=your_key_here"
        exit 1
    fi
else
    echo -e "${RED}✗ $LETTA_DIR/.env not found${NC}"
    echo -e "${PURPLE}Please create $LETTA_DIR/.env with:${NC}"
    echo -e "   ANTHROPIC_API_KEY=your_key_here"
    exit 1
fi

# Navigate to letta directory
cd "$LETTA_DIR"

# Ensure .dsf directories exist in letta-code
if [ -d "$LETTA_CODE_DIR" ]; then
    mkdir -p "$LETTA_CODE_DIR/.dsf/worlds"
    mkdir -p "$LETTA_CODE_DIR/.dsf/stories"
    mkdir -p "$LETTA_CODE_DIR/.dsf/assets"
    echo -e "${CYAN_BRIGHT}✓ .dsf directories ready${NC}"
fi

# Check current branch
echo ""
echo -e "${PURPLE}[2/7] Checking Letta branch...${NC}"
CURRENT_BRANCH=$(git branch --show-current)

if [ "$CURRENT_BRANCH" != "evaluation-tools" ]; then
    echo -e "${PURPLE}⚠ Currently on branch: $CURRENT_BRANCH${NC}"
    echo -e "${PURPLE}⚠ Switching to evaluation-tools branch...${NC}"
    git checkout evaluation-tools
    echo -e "${CYAN_BRIGHT}✓ Switched to evaluation-tools branch${NC}"
else
    echo -e "${CYAN_BRIGHT}✓ Already on evaluation-tools branch${NC}"
fi

# Stop any existing containers
echo ""
echo -e "${PURPLE}[3/7] Stopping existing Letta containers...${NC}"
if docker compose -f dev-compose.yaml ps -q 2>/dev/null | grep -q .; then
    docker compose -f dev-compose.yaml down
    echo -e "${CYAN_BRIGHT}✓ Stopped existing containers${NC}"
else
    echo -e "${CYAN_BRIGHT}✓ No existing containers to stop${NC}"
fi

# Build and start Letta server
echo ""
echo -e "${PURPLE}[4/7] Building and starting Letta server with Docker...${NC}"
echo -e "${CYAN}This will:${NC}"
echo -e "  - Build Letta server from source (evaluation-tools branch)"
echo -e "  - Start PostgreSQL with pgvector"
echo -e "  - Expose server on http://localhost:8283"
echo ""

# Use dev-compose to build from source
docker compose -f dev-compose.yaml up -d --build

echo ""
echo -e "${CYAN_BRIGHT}✓ Letta server starting...${NC}"

# Wait for server to be ready
echo ""
echo -e "${PURPLE}[5/7] Waiting for Letta server to be ready...${NC}"
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8283/v1/health >/dev/null 2>&1; then
        echo -e "${CYAN_BRIGHT}✓ Letta server is ready!${NC}"
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo -e "${CYAN}  Waiting... ($RETRY_COUNT/$MAX_RETRIES)${NC}"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}✗ Letta server did not start within expected time${NC}"
    echo -e "${PURPLE}Check logs: docker compose -f dev-compose.yaml logs${NC}"
    exit 1
fi

# Start Story Explorer Gallery (optional)
echo ""
echo -e "${PURPLE}[6/7] Story Explorer Gallery...${NC}"

if command_exists bun && [ -d "$LETTA_CODE_DIR" ]; then
    # Check if port 3030 is available
    if port_in_use 3030; then
        echo -e "${PURPLE}⚠ Port 3030 already in use. Gallery might already be running.${NC}"
    else
        cd "$LETTA_CODE_DIR"
        echo -e "${CYAN_BRIGHT}✓ Starting Story Explorer gallery on http://localhost:3030${NC}"

        # Start gallery in background
        nohup bun run gallery > "$LETTA_CODE_DIR/.gallery.log" 2>&1 &
        GALLERY_PID=$!
        echo $GALLERY_PID > "$LETTA_CODE_DIR/.gallery.pid"

        # Wait a moment for it to start
        sleep 2

        if kill -0 $GALLERY_PID 2>/dev/null; then
            echo -e "${CYAN_BRIGHT}✓ Story Explorer running (PID: $GALLERY_PID)${NC}"
        else
            echo -e "${RED}✗ Failed to start gallery. Check $LETTA_CODE_DIR/.gallery.log${NC}"
        fi
    fi
else
    if ! command_exists bun; then
        echo -e "${PURPLE}⚠ Bun not installed - Story Explorer unavailable${NC}"
    else
        echo -e "${PURPLE}⚠ letta-code directory not found - Story Explorer unavailable${NC}"
    fi
fi

# Summary
echo ""
echo -e "${PURPLE}[7/7] Startup complete!${NC}"
echo ""
echo -e "${CYAN_BRIGHT}╔════════════════════════════════════════════╗${NC}"
echo -e "${CYAN_BRIGHT}║   Letta Stack Running                     ║${NC}"
echo -e "${CYAN_BRIGHT}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Services:${NC}"
echo -e "  • Letta Server:  ${CYAN_BRIGHT}http://localhost:8283${NC}"
echo -e "  • PostgreSQL:    ${CYAN_BRIGHT}localhost:5432${NC}"
echo ""
echo -e "${CYAN}Logs:${NC}"
echo -e "  docker compose -f dev-compose.yaml logs -f"
echo ""
echo -e "${CYAN}Stop:${NC}"
echo -e "  docker compose -f dev-compose.yaml down"
echo ""

# Start letta-code UI
if [ ! -d "$LETTA_CODE_DIR" ]; then
    echo -e "${RED}✗ letta-code directory not found at $LETTA_CODE_DIR${NC}"
    echo ""
else
    echo ""
    echo -e "${PURPLE}Starting letta-code UI in this terminal...${NC}"
    echo -e "${CYAN}Connecting to: http://localhost:8283${NC}"
    echo ""
    cd "$LETTA_CODE_DIR"

    # Set LETTA_BASE_URL to connect to local server instead of cloud
    # Run in foreground so user can interact with it
    echo -e "${CYAN_BRIGHT}Ready to build worlds! 🚀${NC}"
    echo ""
    LETTA_BASE_URL=http://localhost:8283 bun run dev
fi
