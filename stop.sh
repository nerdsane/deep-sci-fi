#!/bin/bash

#
# DSF Stack Stop Script
# Stops: Letta Server (Docker) + letta-code UI
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

LETTA_DIR="$HOME/Development/letta"

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   DSF Stack Stop Script                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Stop Letta containers
echo -e "${YELLOW}Stopping Letta server containers...${NC}"
cd "$LETTA_DIR"

if docker compose -f dev-compose.yaml ps -q 2>/dev/null | grep -q .; then
    docker compose -f dev-compose.yaml down
    echo -e "${GREEN}✓ Letta containers stopped${NC}"
else
    echo -e "${YELLOW}⚠ No Letta containers were running${NC}"
fi

# Stop letta-code if running
echo ""
echo -e "${YELLOW}Checking for letta-code processes...${NC}"
if pgrep -f "bun.*letta-code" > /dev/null; then
    echo -e "${YELLOW}Found letta-code processes. Kill them? (y/n)${NC} "
    read -r KILL_LETTA_CODE

    if [ "$KILL_LETTA_CODE" = "y" ] || [ "$KILL_LETTA_CODE" = "Y" ]; then
        pkill -f "bun.*letta-code"
        echo -e "${GREEN}✓ letta-code processes stopped${NC}"
    fi
else
    echo -e "${GREEN}✓ No letta-code processes found${NC}"
fi

echo ""
echo -e "${GREEN}All services stopped!${NC}"
