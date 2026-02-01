#!/bin/bash

# Deep Sci-Fi Platform - Stop Script
# Usage: ./stop.sh

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Deep Sci-Fi Platform - Stop Script       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Stop Next.js (platform)
echo -e "${YELLOW}Stopping Platform (Next.js)...${NC}"
if pgrep -f "next-server" > /dev/null || pgrep -f "next dev" > /dev/null; then
    pkill -f "next-server" 2>/dev/null
    pkill -f "next dev" 2>/dev/null
    echo -e "${GREEN}✓ Platform stopped${NC}"
else
    echo -e "${YELLOW}⚠ Platform was not running${NC}"
fi

# Stop Backend (FastAPI)
echo ""
echo -e "${YELLOW}Stopping Backend API...${NC}"
BACKEND_PID_FILE="$SCRIPT_DIR/platform/backend/.backend.pid"
if [ -f "$BACKEND_PID_FILE" ]; then
    BACKEND_PID=$(cat "$BACKEND_PID_FILE")
    if kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID 2>/dev/null
        echo -e "${GREEN}✓ Backend stopped (PID: $BACKEND_PID)${NC}"
    else
        echo -e "${YELLOW}⚠ Backend was not running${NC}"
    fi
    rm -f "$BACKEND_PID_FILE"
else
    if pgrep -f "uvicorn main:app" > /dev/null; then
        pkill -f "uvicorn main:app" 2>/dev/null
        echo -e "${GREEN}✓ Backend stopped${NC}"
    else
        echo -e "${YELLOW}⚠ Backend was not running${NC}"
    fi
fi

# Stop Letta UI
echo ""
echo -e "${YELLOW}Stopping Letta UI...${NC}"
UI_PID_FILE="$SCRIPT_DIR/letta-ui/.ui.pid"
if [ -f "$UI_PID_FILE" ]; then
    UI_PID=$(cat "$UI_PID_FILE")
    if kill -0 $UI_PID 2>/dev/null; then
        kill $UI_PID 2>/dev/null
        echo -e "${GREEN}✓ Letta UI stopped (PID: $UI_PID)${NC}"
    else
        echo -e "${YELLOW}⚠ Letta UI was not running${NC}"
    fi
    rm -f "$UI_PID_FILE"
else
    echo -e "${YELLOW}⚠ Letta UI was not running${NC}"
fi

# Stop Letta Server (Docker)
echo ""
echo -e "${YELLOW}Stopping Letta Server...${NC}"
if command -v docker &> /dev/null; then
    cd "$SCRIPT_DIR/letta"
    if docker compose -f dev-compose.yaml ps -q 2>/dev/null | grep -q .; then
        docker compose -f dev-compose.yaml down
        echo -e "${GREEN}✓ Letta server stopped${NC}"
    else
        echo -e "${YELLOW}⚠ Letta server was not running${NC}"
    fi
    cd "$SCRIPT_DIR"
else
    echo -e "${YELLOW}⚠ Docker not found${NC}"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  All services stopped!${NC}"
echo ""
echo -e "  To start again: ${YELLOW}./start.sh${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
