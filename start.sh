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
echo -e "${PURPLE}[1/8] Checking prerequisites...${NC}"

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

# Environment setup
echo ""
echo -e "${PURPLE}[2/8] Setting up environment variables...${NC}"

ROOT_ENV="$SCRIPT_DIR/.env"
ROOT_ENV_EXAMPLE="$SCRIPT_DIR/.env.example"

# Check if root .env exists
if [ ! -f "$ROOT_ENV" ]; then
    echo -e "${CYAN}Creating .env from .env.example...${NC}"
    if [ -f "$ROOT_ENV_EXAMPLE" ]; then
        cp "$ROOT_ENV_EXAMPLE" "$ROOT_ENV"
        echo -e "${CYAN_BRIGHT}✓ Created $ROOT_ENV${NC}"
    else
        echo -e "${RED}✗ .env.example not found${NC}"
        exit 1
    fi
fi

# Check if .env has placeholder values
if grep -q "ANTHROPIC_API_KEY=sk-ant-\.\.\." "$ROOT_ENV" || grep -q "ANTHROPIC_API_KEY=$" "$ROOT_ENV"; then
    echo ""
    echo -e "${RED}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ACTION REQUIRED: Configure your API keys                    ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${PURPLE}Your .env file needs to be configured with real API keys.${NC}"
    echo ""
    echo -e "${CYAN}Required:${NC}"
    echo -e "  • ANTHROPIC_API_KEY - Get from https://console.anthropic.com/${NC}"
    echo ""
    echo -e "${CYAN}Optional but recommended:${NC}"
    echo -e "  • OPENAI_API_KEY - For image generation and GPT models${NC}"
    echo -e "  • NOTION_TOKEN - For publishing stories to Notion${NC}"
    echo ""
    echo -e "${PURPLE}Please edit: $ROOT_ENV${NC}"
    echo ""
    read -p "Press Enter after you've configured your .env file..."
    echo ""

    # Verify they actually filled it out
    if grep -q "ANTHROPIC_API_KEY=sk-ant-\.\.\." "$ROOT_ENV" || grep -q "ANTHROPIC_API_KEY=$" "$ROOT_ENV"; then
        echo -e "${RED}✗ ANTHROPIC_API_KEY still not configured${NC}"
        echo -e "${PURPLE}Please edit $ROOT_ENV and add your Anthropic API key${NC}"
        exit 1
    fi
fi

# Run setup-env.sh to distribute variables to submodules
echo -e "${CYAN}Distributing environment variables to submodules...${NC}"
if [ -f "$SCRIPT_DIR/setup-env.sh" ]; then
    "$SCRIPT_DIR/setup-env.sh"
else
    echo -e "${RED}✗ setup-env.sh not found${NC}"
    exit 1
fi

# Verify letta/.env was created and has ANTHROPIC_API_KEY
if [ ! -f "$LETTA_DIR/.env" ]; then
    echo -e "${RED}✗ Failed to create $LETTA_DIR/.env${NC}"
    exit 1
fi

if ! grep -q "ANTHROPIC_API_KEY=" "$LETTA_DIR/.env" || grep -q "ANTHROPIC_API_KEY=$" "$LETTA_DIR/.env"; then
    echo -e "${RED}✗ ANTHROPIC_API_KEY not properly configured${NC}"
    exit 1
fi

echo -e "${CYAN_BRIGHT}✓ Environment configured successfully${NC}"

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
echo -e "${PURPLE}[3/8] Checking Letta branch...${NC}"
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
echo -e "${PURPLE}[4/8] Stopping existing Letta containers...${NC}"
if docker compose -f dev-compose.yaml ps -q 2>/dev/null | grep -q .; then
    docker compose -f dev-compose.yaml down
    echo -e "${CYAN_BRIGHT}✓ Stopped existing containers${NC}"
else
    echo -e "${CYAN_BRIGHT}✓ No existing containers to stop${NC}"
fi

# Build and start Letta server
echo ""
echo -e "${PURPLE}[5/8] Building and starting Letta server with Docker...${NC}"
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
echo -e "${PURPLE}[6/8] Waiting for Letta server to be ready...${NC}"
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

# Start Letta Web UI
echo ""
echo -e "${PURPLE}[7/9] Starting Letta Web UI...${NC}"

LETTA_UI_DIR="$SCRIPT_DIR/letta-ui"

if command_exists bun && [ -d "$LETTA_UI_DIR" ]; then
    # Check if port 3000 is available
    if port_in_use 3000; then
        echo -e "${PURPLE}⚠ Port 3000 already in use. Web UI might already be running.${NC}"
    else
        cd "$LETTA_UI_DIR"
        echo -e "${CYAN_BRIGHT}✓ Starting Letta Web UI on http://localhost:3000${NC}"

        # Start web UI in background
        LETTA_BASE_URL=http://localhost:8283 nohup bun run dev > "$LETTA_UI_DIR/.ui.log" 2>&1 &
        UI_PID=$!
        echo $UI_PID > "$LETTA_UI_DIR/.ui.pid"

        # Wait a moment for it to start
        sleep 2

        if kill -0 $UI_PID 2>/dev/null; then
            echo -e "${CYAN_BRIGHT}✓ Letta Web UI running (PID: $UI_PID)${NC}"
        else
            echo -e "${RED}✗ Failed to start web UI. Check $LETTA_UI_DIR/.ui.log${NC}"
        fi
    fi
else
    if ! command_exists bun; then
        echo -e "${PURPLE}⚠ Bun not installed - Web UI unavailable${NC}"
    else
        echo -e "${PURPLE}⚠ letta-ui directory not found - Web UI unavailable${NC}"
    fi
fi

# Start Agent Bus (required for bidirectional communication)
echo ""
echo -e "${PURPLE}[8/10] Starting Agent Bus...${NC}"

if command_exists bun && [ -d "$LETTA_CODE_DIR" ]; then
    # Check if port 8284 is available
    if port_in_use 8284; then
        echo -e "${PURPLE}⚠ Port 8284 already in use. Agent Bus might already be running.${NC}"
    else
        cd "$LETTA_CODE_DIR"
        echo -e "${CYAN_BRIGHT}✓ Starting Agent Bus on ws://localhost:8284${NC}"

        # Start Agent Bus in background
        nohup bun run agent-bus > "$LETTA_CODE_DIR/.agent-bus.log" 2>&1 &
        AGENT_BUS_PID=$!
        echo $AGENT_BUS_PID > "$LETTA_CODE_DIR/.agent-bus.pid"

        # Wait a moment for it to start
        sleep 1

        if kill -0 $AGENT_BUS_PID 2>/dev/null; then
            echo -e "${CYAN_BRIGHT}✓ Agent Bus running (PID: $AGENT_BUS_PID)${NC}"
        else
            echo -e "${RED}✗ Failed to start Agent Bus. Check $LETTA_CODE_DIR/.agent-bus.log${NC}"
        fi
    fi
else
    if ! command_exists bun; then
        echo -e "${PURPLE}⚠ Bun not installed - Agent Bus unavailable${NC}"
    else
        echo -e "${PURPLE}⚠ letta-code directory not found - Agent Bus unavailable${NC}"
    fi
fi

# Start Story Explorer Gallery (optional)
echo ""
echo -e "${PURPLE}[9/10] Story Explorer Gallery...${NC}"

if command_exists bun && [ -d "$LETTA_CODE_DIR" ]; then
    # Check if port 3030 is available
    if port_in_use 3030; then
        echo -e "${PURPLE}⚠ Port 3030 already in use. Gallery might already be running.${NC}"
    else
        cd "$LETTA_CODE_DIR"
        echo -e "${CYAN_BRIGHT}✓ Starting Story Explorer gallery on http://localhost:3030${NC}"

        # Start gallery in background
        nohup bun run canvas > "$LETTA_CODE_DIR/.gallery.log" 2>&1 &
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
echo -e "${PURPLE}[10/10] Startup complete!${NC}"
echo ""
echo -e "${CYAN_BRIGHT}╔════════════════════════════════════════════╗${NC}"
echo -e "${CYAN_BRIGHT}║   DSF Stack Running                       ║${NC}"
echo -e "${CYAN_BRIGHT}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Services:${NC}"
echo -e "  • Letta Server:     ${CYAN_BRIGHT}http://localhost:8283${NC}"
echo -e "  • Letta Web UI:     ${CYAN_BRIGHT}http://localhost:3000${NC} ${PURPLE}(dashboard, trajectories, analytics)${NC}"
echo -e "  • Agent Bus:        ${CYAN_BRIGHT}ws://localhost:8284${NC} ${PURPLE}(bidirectional canvas<->agent)${NC}"
echo -e "  • Story Gallery:    ${CYAN_BRIGHT}http://localhost:3030${NC} ${PURPLE}(browse worlds & stories)${NC}"
echo -e "  • PostgreSQL:       ${CYAN_BRIGHT}localhost:5432${NC}"
echo ""
echo -e "${CYAN}Logs:${NC}"
echo -e "  • Server:     docker compose -f dev-compose.yaml logs -f"
echo -e "  • Web UI:     tail -f letta-ui/.ui.log"
echo -e "  • Agent Bus:  tail -f letta-code/.agent-bus.log"
echo -e "  • Gallery:    tail -f letta-code/.gallery.log"
echo ""
echo -e "${CYAN}Stop:${NC}"
echo -e "  • Server:     docker compose -f dev-compose.yaml down"
echo -e "  • Web UI:     kill \$(cat letta-ui/.ui.pid)"
echo -e "  • Agent Bus:  kill \$(cat letta-code/.agent-bus.pid)"
echo -e "  • Gallery:    kill \$(cat letta-code/.gallery.pid)"
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
