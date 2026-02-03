#!/bin/bash
# Stop the Deep Sci-Fi Platform

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Stopping Deep Sci-Fi Platform...${NC}"

# Stop backend
if [ -f ".backend.pid" ]; then
    PID=$(cat .backend.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        echo -e "${GREEN}✓ Backend stopped${NC}"
    fi
    rm -f .backend.pid
fi

# Stop frontend
if [ -f ".frontend.pid" ]; then
    PID=$(cat .frontend.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        echo -e "${GREEN}✓ Frontend stopped${NC}"
    fi
    rm -f .frontend.pid
fi

# Optionally stop PostgreSQL
echo
read -p "Stop PostgreSQL container? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker stop platform-postgres 2>/dev/null && echo -e "${GREEN}✓ PostgreSQL stopped${NC}"
fi

echo
echo -e "${GREEN}Platform stopped.${NC}"
