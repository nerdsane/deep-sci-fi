#!/bin/bash
#
# Check if skill.md endpoint tables are in sync with the API.
# Runs the sync script in --check mode against staged changes.
#
# Usage:
#   ./scripts/check-skill-endpoints.sh          # Check staged changes
#   ./scripts/check-skill-endpoints.sh --all    # Check unconditionally
#

set -e

REPO_ROOT=$(git rev-parse --show-toplevel)
SKILL_FILE="platform/public/skill.md"
API_DIR="platform/backend/api"
BACKEND_DIR="$REPO_ROOT/platform/backend"

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Determine what to check
if [ "$1" == "--all" ]; then
    RUN_CHECK=true
else
    # Only run if API routes or skill.md are staged
    STAGED_API=$(git diff --cached --name-only -- "$API_DIR" 2>/dev/null || true)
    STAGED_SKILL=$(git diff --cached --name-only -- "$SKILL_FILE" 2>/dev/null || true)
    STAGED_MAIN=$(git diff --cached --name-only -- "platform/backend/main.py" 2>/dev/null || true)

    if [ -n "$STAGED_API" ] || [ -n "$STAGED_SKILL" ] || [ -n "$STAGED_MAIN" ]; then
        RUN_CHECK=true
    else
        RUN_CHECK=false
    fi
fi

if [ "$RUN_CHECK" != "true" ]; then
    exit 0
fi

# Check if the backend venv exists
if [ ! -f "$BACKEND_DIR/.venv/bin/python" ]; then
    echo -e "${YELLOW}Skipping skill.md endpoint check (no backend venv found)${NC}"
    exit 0
fi

echo "Checking skill.md endpoint tables..."

cd "$BACKEND_DIR"
if .venv/bin/python scripts/sync_skill_endpoints.py --check 2>/dev/null; then
    echo -e "${GREEN}skill.md endpoint tables are in sync.${NC}"
else
    echo ""
    echo -e "${RED}==========================================${NC}"
    echo -e "${RED}SKILL.MD IS OUT OF DATE${NC}"
    echo -e "${RED}==========================================${NC}"
    echo ""
    echo "Endpoint tables or version in skill.md need updating."
    echo ""
    echo "To fix this:"
    echo "  1. cd platform/backend"
    echo "  2. source .venv/bin/activate"
    echo "  3. python scripts/sync_skill_endpoints.py"
    echo "     (this syncs endpoints AND auto-bumps the version)"
    echo "  4. git add platform/public/skill.md"
    echo ""
    echo -e "${RED}Commit blocked. Please run the sync script first.${NC}"
    exit 1
fi
