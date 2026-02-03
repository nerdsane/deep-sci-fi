#!/bin/bash
#
# Check if database model changes have corresponding migrations.
# This script compares staged changes in models.py against migrations.
#
# Usage:
#   ./scripts/check-migrations.sh          # Check staged changes
#   ./scripts/check-migrations.sh --all    # Check all uncommitted changes
#

set -e

MODELS_FILE="platform/backend/db/models.py"
MIGRATIONS_DIR="platform/backend/alembic/versions"

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Check if we're in the repo root
if [ ! -f "$MODELS_FILE" ]; then
    echo -e "${RED}Error: Must run from repository root${NC}"
    exit 1
fi

# Determine what to check
if [ "$1" == "--all" ]; then
    # Check all uncommitted changes
    MODEL_CHANGES=$(git diff HEAD -- "$MODELS_FILE" 2>/dev/null || true)
    MIGRATION_CHANGES=$(git diff HEAD -- "$MIGRATIONS_DIR"/*.py 2>/dev/null || true)
    CHECK_TYPE="uncommitted"
else
    # Check only staged changes (for pre-commit)
    MODEL_CHANGES=$(git diff --cached -- "$MODELS_FILE" 2>/dev/null || true)
    MIGRATION_CHANGES=$(git diff --cached -- "$MIGRATIONS_DIR"/*.py 2>/dev/null || true)
    CHECK_TYPE="staged"
fi

# Extract added/modified columns from model changes
COLUMN_CHANGES=$(echo "$MODEL_CHANGES" | grep -E '^\+.*mapped_column|^\+.*Mapped\[|^\+.*Column\(' | grep -v '^\+\+\+' || true)

if [ -z "$MODEL_CHANGES" ]; then
    echo -e "${GREEN}No model changes detected.${NC}"
    exit 0
fi

if [ -n "$COLUMN_CHANGES" ]; then
    echo -e "${YELLOW}======================================${NC}"
    echo -e "${YELLOW}DATABASE MODEL CHANGES DETECTED${NC}"
    echo -e "${YELLOW}======================================${NC}"
    echo ""
    echo "The following column changes were found in $CHECK_TYPE files:"
    echo ""
    echo "$COLUMN_CHANGES" | head -20
    echo ""

    if [ -z "$MIGRATION_CHANGES" ]; then
        echo -e "${RED}======================================${NC}"
        echo -e "${RED}ERROR: NO MIGRATION FOUND!${NC}"
        echo -e "${RED}======================================${NC}"
        echo ""
        echo "You modified database models but did not create a migration."
        echo ""
        echo "To fix this:"
        echo "  1. cd platform/backend"
        echo "  2. source .venv/bin/activate"
        echo "  3. alembic revision --autogenerate -m 'description of changes'"
        echo "  4. Review the generated migration"
        echo "  5. git add the migration file"
        echo ""
        echo "See CLAUDE.md for more details on migrations."
        echo ""

        # In pre-commit mode, block the commit
        if [ "$CHECK_TYPE" == "staged" ]; then
            echo -e "${RED}Commit blocked. Please create a migration first.${NC}"
            exit 1
        else
            echo -e "${YELLOW}Warning: Remember to create a migration before committing.${NC}"
            exit 0
        fi
    else
        echo -e "${GREEN}Migration changes detected - good!${NC}"
        echo ""
        echo "Migration files modified:"
        echo "$MIGRATION_CHANGES" | grep -E '^\+\+\+' | sed 's/+++ b\//  /' || true
        echo ""
    fi
else
    echo -e "${GREEN}Model changes don't appear to affect database schema.${NC}"
fi

exit 0
