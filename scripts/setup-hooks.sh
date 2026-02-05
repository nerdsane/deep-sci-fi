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

# Create pre-push hook (informational, not blocking)
cat > "$HOOKS_DIR/pre-push" << 'EOF'
#!/bin/bash
REPO_ROOT=$(git rev-parse --show-toplevel)
changed=$(git diff --name-only @{push}.. 2>/dev/null | grep "platform/backend/api/" || true)
if [ -n "$changed" ]; then
    echo ""
    echo "  [DST] API files changed. CI will run simulation tests."
    echo "  Local: cd platform/backend && pytest tests/simulation/ -v --hypothesis-seed=0 -x"
    echo ""
fi
EOF
chmod +x "$HOOKS_DIR/pre-push"

echo "Git hooks installed successfully!"
echo ""
echo "The following hooks are now active:"
echo "  - pre-commit: Checks for missing database migrations"
echo "  - pre-commit: Checks skill.md endpoints and version are in sync"
echo "  - pre-push: Informational DST reminder when API files change"
echo ""
echo "To bypass hooks in emergencies: git commit --no-verify"
