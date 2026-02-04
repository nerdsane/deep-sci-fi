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
#   2. skill.md endpoint tables are in sync with the API
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
EOF

chmod +x "$HOOKS_DIR/pre-commit"

echo "Git hooks installed successfully!"
echo ""
echo "The following hooks are now active:"
echo "  - pre-commit: Checks for missing database migrations"
echo "  - pre-commit: Checks skill.md endpoint tables are in sync"
echo ""
echo "To bypass hooks in emergencies: git commit --no-verify"
