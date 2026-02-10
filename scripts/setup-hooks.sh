#!/bin/bash
#
# Setup git hooks for the deep-sci-fi repository
#

set -e

REPO_ROOT=$(git rev-parse --show-toplevel)
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "Setting up git hooks..."

# Create pre-commit hook
cat > "$HOOKS_DIR/pre-commit" << 'EOF'
#!/bin/bash
#
# Pre-commit hook for deep-sci-fi
# Checks:
#   1. Database model changes have corresponding migrations
#   2. skill.md endpoint tables and version are in sync
#

# Get the repository root
REPO_ROOT=$(git rev-parse --show-toplevel)

# Run migration check
if [ -f "$REPO_ROOT/scripts/check-migrations.sh" ]; then
    "$REPO_ROOT/scripts/check-migrations.sh"
fi

# Run skill.md endpoint table check
if [ -f "$REPO_ROOT/scripts/check-skill-endpoints.sh" ]; then
    "$REPO_ROOT/scripts/check-skill-endpoints.sh"
fi

# Run DST endpoint coverage check
if [ -f "$REPO_ROOT/scripts/check-dst-coverage.sh" ]; then
    "$REPO_ROOT/scripts/check-dst-coverage.sh"
fi
EOF

chmod +x "$HOOKS_DIR/pre-commit"

# Create pre-push hook (BLOCKING — requires DST coverage + test pass)
cat > "$HOOKS_DIR/pre-push" << 'PUSHEOF'
#!/bin/bash
#
# Pre-push hook for deep-sci-fi
# BLOCKING: Prevents push if:
#   1. DST coverage check fails (new uncovered state-mutating endpoints)
#   2. DST simulation tests fail (seed 0)
#
# Skip with: git push --no-verify (emergencies only)
#

REPO_ROOT=$(git rev-parse --show-toplevel)
BACKEND="$REPO_ROOT/platform/backend"

# Check if backend venv exists
if [ ! -d "$BACKEND/.venv" ] || [ ! -f "$BACKEND/.venv/bin/python" ]; then
    echo "  [DST] Skipping — no .venv found at $BACKEND/.venv"
    exit 0
fi

# Check if any relevant files changed (backend API, simulation tests, or strategies)
changed=$(git diff --name-only @{push}.. 2>/dev/null | grep -E "platform/backend/(api/|tests/simulation/|db/)" || true)
if [ -z "$changed" ]; then
    exit 0
fi

echo ""
echo "  ┌──────────────────────────────────────────┐"
echo "  │  DST Pre-Push Gate                        │"
echo "  │  Backend files changed — running checks   │"
echo "  └──────────────────────────────────────────┘"
echo ""

cd "$BACKEND" || exit 1

# Step 1: DST Coverage Check
echo "  [1/2] Checking DST endpoint coverage..."
.venv/bin/python "../../scripts/check_dst_coverage.py" --check 2>&1
coverage_exit=$?
if [ $coverage_exit -ne 0 ]; then
    echo ""
    echo "  ✗ PUSH BLOCKED: Uncovered state-mutating endpoints detected."
    echo "  Add DST rules in tests/simulation/rules/ for new endpoints."
    echo "  Or add to KNOWN_UNCOVERED in scripts/check_dst_coverage.py."
    echo "  Skip with: git push --no-verify"
    echo ""
    exit 1
fi
echo "  ✓ All state-mutating endpoints covered."
echo ""

# Step 2: DST Simulation Test (seed 0)
echo "  [2/2] Running DST simulation test (seed 0)..."
.venv/bin/python -m pytest tests/simulation/test_game_rules.py -x \
    --hypothesis-seed=0 -q --tb=line --no-header 2>&1
test_exit=$?
if [ $test_exit -ne 0 ]; then
    echo ""
    echo "  ✗ PUSH BLOCKED: DST simulation test failed."
    echo "  Fix failing invariants before pushing."
    echo "  Run: pytest tests/simulation/test_game_rules.py -x --hypothesis-seed=0 -v"
    echo "  Skip with: git push --no-verify"
    echo ""
    exit 1
fi
echo "  ✓ DST simulation test passed."
echo ""
echo "  ✓ All DST checks passed. Push proceeding."
echo ""
PUSHEOF
chmod +x "$HOOKS_DIR/pre-push"

echo "Git hooks installed successfully!"
echo ""
echo "The following hooks are now active:"
echo "  - pre-commit: Checks for missing database migrations"
echo "  - pre-commit: Checks skill.md endpoints and version are in sync"
echo "  - pre-commit: Checks DST endpoint coverage (when API files staged)"
echo "  - pre-push:   BLOCKING — DST coverage + simulation test (seed 0)"
echo ""
echo "To bypass hooks in emergencies: git push --no-verify"
