#!/bin/bash
#
# DST Coverage Check — for pre-commit hook
# Only triggers if api/ files are staged
#

REPO_ROOT=$(git rev-parse --show-toplevel)

STAGED_API=$(git diff --cached --name-only -- "platform/backend/api/" | head -1)
if [ -n "$STAGED_API" ]; then
    echo "  [DST] Checking endpoint coverage..."
    cd "$REPO_ROOT/platform/backend" || exit 0

    if [ -d ".venv" ] && [ -f ".venv/bin/python" ]; then
        .venv/bin/python "../../scripts/check_dst_coverage.py" --check
        exit_code=$?
        if [ $exit_code -ne 0 ]; then
            echo ""
            echo "  [DST] FAIL: Uncovered state-mutating endpoints detected."
            echo "  Add DST rules for the new endpoints in tests/simulation/rules/"
            echo ""
            exit $exit_code
        fi
        echo "  [DST] Coverage check passed."
    else
        echo "  [DST] Skipping — no .venv found. Run from backend venv to enable."
    fi
fi
