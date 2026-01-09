#!/bin/bash

# Deep Sci-Fi - One-Command Startup Script
# Usage: ./start.sh

set -e  # Exit on any error

echo "🌌 Deep Sci-Fi - Starting Everything..."
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if .env exists in apps/web
if [ ! -f "apps/web/.env" ]; then
    print_warning ".env not found, creating from .env.example..."
    cp apps/web/.env.example apps/web/.env

    # Generate NEXTAUTH_SECRET
    SECRET=$(openssl rand -base64 32)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|NEXTAUTH_SECRET=\".*\"|NEXTAUTH_SECRET=\"$SECRET\"|" apps/web/.env
    else
        # Linux
        sed -i "s|NEXTAUTH_SECRET=\".*\"|NEXTAUTH_SECRET=\"$SECRET\"|" apps/web/.env
    fi

    print_success ".env created with random NEXTAUTH_SECRET"
    print_warning "Using existing ANTHROPIC_API_KEY from .env.example"
else
    print_success ".env already exists"
fi

# 1. Start PostgreSQL
echo ""
echo "📦 Starting PostgreSQL..."
if docker ps | grep -q deep-sci-fi-postgres; then
    print_success "PostgreSQL already running"
else
    if docker ps -a | grep -q deep-sci-fi-postgres; then
        print_warning "Starting existing PostgreSQL container..."
        docker start deep-sci-fi-postgres
    else
        print_warning "Creating new PostgreSQL container..."
        docker run -d \
            --name deep-sci-fi-postgres \
            -e POSTGRES_USER=deepscifi \
            -e POSTGRES_PASSWORD=dev_password_change_in_production \
            -e POSTGRES_DB=deep_sci_fi_dev \
            -p 5432:5432 \
            pgvector/pgvector:pg16

        # Wait for PostgreSQL to be ready
        echo "Waiting for PostgreSQL to be ready..."
        sleep 5
    fi
    print_success "PostgreSQL running on localhost:5432"
fi

# 2. Start Letta Server
echo ""
echo "🤖 Starting Letta Server..."
cd letta
if docker-compose ps | grep -q "letta.*Up"; then
    print_success "Letta server already running"
else
    print_warning "Starting Letta server..."
    docker-compose up -d

    # Wait for Letta to be ready
    echo "Waiting for Letta server to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:8283/health > /dev/null 2>&1; then
            print_success "Letta server ready on localhost:8283"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "Letta server failed to start"
            exit 1
        fi
        sleep 1
    done
fi
cd ..

# 3. Link local packages and install dependencies
echo ""
echo "📚 Checking dependencies..."
if [ ! -d "apps/web/node_modules" ]; then
    print_warning "Setting up local packages..."

    # Create symlinks for local packages (workaround for npm workspace issues)
    mkdir -p apps/web/node_modules/@deep-sci-fi
    cd apps/web/node_modules/@deep-sci-fi

    # Remove existing symlinks if any
    rm -f letta types db

    # Create symlinks
    ln -s ../../../../packages/letta letta
    ln -s ../../../../packages/types types
    ln -s ../../../../packages/db db

    cd ../../../..

    print_warning "Installing dependencies (this may take a few minutes)..."
    cd apps/web
    npm install --legacy-peer-deps
    cd ../..
    print_success "Dependencies installed"
else
    print_success "Dependencies already installed"
fi

# 4. Setup database
echo ""
echo "🗄️  Setting up database..."

# Run Prisma commands from packages/db where Prisma is installed
cd packages/db

# Ensure Prisma dependencies are installed
if [ ! -d "node_modules/.bin" ]; then
    print_warning "Installing Prisma dependencies..."
    npm install --legacy-peer-deps
fi

# Export DATABASE_URL from apps/web/.env for Prisma
export DATABASE_URL=$(grep "^DATABASE_URL=" ../../apps/web/.env | cut -d '=' -f2- | tr -d '"')

# Check if database is already set up
if npx prisma db execute --stdin <<< "SELECT 1 FROM \"User\" LIMIT 1;" 2>/dev/null; then
    print_success "Database already set up"
else
    print_warning "Pushing database schema..."
    npx prisma db push --skip-generate
    print_success "Database schema created"
fi

# Always generate Prisma client
print_warning "Generating Prisma client..."
npx prisma generate

# Copy Prisma binary to web app (needed for Next.js with symlinked packages)
print_warning "Copying Prisma binary to web app..."
mkdir -p ../../apps/web/node_modules/.prisma/client
cp -r node_modules/.prisma/client/* ../../apps/web/node_modules/.prisma/client/
cd ../..
print_success "Prisma client generated and binary copied"

# 5. Start the web app
echo ""
echo "🚀 Starting web app..."
echo ""
print_success "All services ready!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🌌 Deep Sci-Fi is starting..."
echo ""
echo "  Web App:        http://localhost:3000"
echo "  Letta Server:   http://localhost:8283"
echo "  PostgreSQL:     localhost:5432"
echo ""
echo "  Press Ctrl+C to stop"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd apps/web
npm run dev
