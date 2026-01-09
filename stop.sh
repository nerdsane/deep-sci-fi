#!/bin/bash

#
# Deep Sci-Fi Stack Stop Script
# Stops: Web App + Letta Server (Docker) + PostgreSQL
#

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LETTA_DIR="$SCRIPT_DIR/letta"

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Deep Sci-Fi - Stop Script               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Stop Next.js web app
echo -e "${YELLOW}Stopping Next.js web app...${NC}"
if pgrep -f "next-server" > /dev/null || pgrep -f "next dev" > /dev/null; then
    pkill -f "next-server" 2>/dev/null
    pkill -f "next dev" 2>/dev/null
    echo -e "${GREEN}✓ Next.js stopped${NC}"
else
    echo -e "${YELLOW}⚠ Next.js was not running${NC}"
fi

# Stop WebSocket server
echo ""
echo -e "${YELLOW}Stopping WebSocket server...${NC}"
WS_PID_FILE="$SCRIPT_DIR/apps/web/.ws.pid"
if [ -f "$WS_PID_FILE" ]; then
    WS_PID=$(cat "$WS_PID_FILE")
    if kill -0 $WS_PID 2>/dev/null; then
        kill $WS_PID 2>/dev/null
        echo -e "${GREEN}✓ WebSocket server stopped (PID: $WS_PID)${NC}"
    else
        echo -e "${YELLOW}⚠ WebSocket server was not running${NC}"
    fi
    rm -f "$WS_PID_FILE"
else
    # Try to find and kill by process name
    if pgrep -f "ws-server.ts" > /dev/null; then
        pkill -f "ws-server.ts" 2>/dev/null
        echo -e "${GREEN}✓ WebSocket server stopped${NC}"
    else
        echo -e "${YELLOW}⚠ WebSocket server was not running${NC}"
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
    # Try to find and kill by process name
    if pgrep -f "letta-ui.*server.ts" > /dev/null; then
        pkill -f "letta-ui.*server.ts" 2>/dev/null
        echo -e "${GREEN}✓ Letta UI stopped${NC}"
    else
        echo -e "${YELLOW}⚠ Letta UI was not running${NC}"
    fi
fi

# Stop Letta containers
echo ""
echo -e "${YELLOW}Stopping Letta server containers...${NC}"
cd "$LETTA_DIR"

if docker compose -f dev-compose.yaml ps -q 2>/dev/null | grep -q .; then
    docker compose -f dev-compose.yaml down
    echo -e "${GREEN}✓ Letta containers stopped${NC}"
else
    echo -e "${YELLOW}⚠ No Letta containers were running${NC}"
fi

cd "$SCRIPT_DIR"

# Stop PostgreSQL container
echo ""
echo -e "${YELLOW}Stopping PostgreSQL...${NC}"
if docker ps | grep -q "deep-sci-fi-postgres"; then
    docker stop deep-sci-fi-postgres > /dev/null
    echo -e "${GREEN}✓ PostgreSQL stopped${NC}"
else
    echo -e "${YELLOW}⚠ PostgreSQL was not running${NC}"
fi

# Stop any letta-code processes if running
if pgrep -f "bun.*letta-code" > /dev/null; then
    echo ""
    echo -e "${YELLOW}Stopping letta-code processes...${NC}"
    pkill -f "bun.*letta-code" 2>/dev/null
    echo -e "${GREEN}✓ letta-code stopped${NC}"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  All services stopped!${NC}"
echo ""
echo -e "  To start again: ${YELLOW}./start.sh${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
