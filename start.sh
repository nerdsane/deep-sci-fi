#!/bin/bash

# Deep Sci-Fi Platform - Startup Script
# Usage: ./start.sh

set -e

echo "🌌 Deep Sci-Fi Platform - Starting..."
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check platform/.env
if [ ! -f "platform/.env" ]; then
    if [ -f "platform/.env.example" ]; then
        print_warning ".env not found, creating from .env.example..."
        cp platform/.env.example platform/.env
        print_success ".env created - please configure your API keys"
    else
        print_error "No .env.example found in platform/"
        exit 1
    fi
else
    print_success "platform/.env exists"
fi

# 1. Start Letta Server (if docker available)
echo ""
echo "🤖 Starting Letta Server..."
cd "$SCRIPT_DIR/letta"
if command -v docker &> /dev/null; then
    if docker compose -f dev-compose.yaml ps 2>/dev/null | grep -q "Up"; then
        print_success "Letta server already running"
    else
        print_warning "Starting Letta server..."
        docker compose -f dev-compose.yaml up -d

        echo "Waiting for Letta server..."
        for i in {1..30}; do
            if curl -s http://localhost:8285/health > /dev/null 2>&1; then
                print_success "Letta server ready on localhost:8285"
                break
            fi
            if [ $i -eq 30 ]; then
                print_warning "Letta server may still be starting..."
            fi
            sleep 1
        done
    fi
else
    print_warning "Docker not found - skipping Letta server"
fi
cd "$SCRIPT_DIR"

# 2. Start Letta UI (debugging dashboard)
echo ""
echo "📊 Starting Letta UI..."
cd "$SCRIPT_DIR/letta-ui"

if [ ! -d "node_modules" ]; then
    print_warning "Installing Letta UI dependencies..."
    bun install
fi

# Kill existing Letta UI
if [ -f ".ui.pid" ]; then
    OLD_PID=$(cat .ui.pid)
    if kill -0 $OLD_PID 2>/dev/null; then
        print_warning "Stopping existing Letta UI..."
        kill $OLD_PID 2>/dev/null || true
        sleep 1
    fi
    rm -f .ui.pid
fi

LETTA_BASE_URL=http://localhost:8285 PORT=4000 bun run dev > .ui.log 2>&1 &
UI_PID=$!
echo $UI_PID > .ui.pid
print_success "Letta UI starting on localhost:4000 (PID: $UI_PID)"
cd "$SCRIPT_DIR"

# 3. Start Backend (FastAPI)
echo ""
echo "🐍 Starting Backend API..."
cd "$SCRIPT_DIR/platform/backend"

# Kill existing backend
if [ -f ".backend.pid" ]; then
    OLD_PID=$(cat .backend.pid)
    if kill -0 $OLD_PID 2>/dev/null; then
        print_warning "Stopping existing backend..."
        kill $OLD_PID 2>/dev/null || true
        sleep 1
    fi
    rm -f .backend.pid
fi

# Create venv if needed
if [ ! -d ".venv" ]; then
    print_warning "Creating Python virtual environment..."
    python3 -m venv .venv
fi

# Activate and install deps
source .venv/bin/activate
if [ -f "requirements.txt" ]; then
    pip install -q -r requirements.txt
fi

# Start backend
uvicorn main:app --reload --port 8000 > .backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > .backend.pid
print_success "Backend API starting on localhost:8000 (PID: $BACKEND_PID)"
deactivate 2>/dev/null || true
cd "$SCRIPT_DIR"

# 4. Start Platform (Next.js)
echo ""
echo "🚀 Starting Platform..."
cd "$SCRIPT_DIR/platform"

if [ ! -d "node_modules" ]; then
    print_warning "Installing platform dependencies..."
    bun install
fi

echo ""
print_success "All services starting!"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  🌌 Deep Sci-Fi Platform"
echo ""
echo -e "  Platform:       ${GREEN}http://localhost:3000${NC}"
echo -e "  Backend API:    ${GREEN}http://localhost:8000${NC}"
echo -e "  Letta UI:       ${GREEN}http://localhost:4000${NC}"
echo -e "  Letta Server:   ${GREEN}http://localhost:8285${NC}"
echo ""
echo -e "  Press Ctrl+C to stop"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

bun run dev
