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
#   3. Auto-run required reviewers (code + dst for DST-sensitive changes)
#   4. Review markers exist (code + dst for DST-sensitive changes)
#   5. Changed API routes declare response_model/responses
#   6. Changed API modules have route-prefix test coverage
#   7. Changed frontend files include mapped E2E spec updates
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

# Auto-run required reviewers using Claude reviewer prompts
if [ -f "$REPO_ROOT/scripts/run_required_reviews.sh" ]; then
    "$REPO_ROOT/scripts/run_required_reviews.sh" --staged
fi

# Require review markers (agent-agnostic parity with Claude pre-commit review gate)
if [ -f "$REPO_ROOT/scripts/check_review_markers.sh" ]; then
    "$REPO_ROOT/scripts/check_review_markers.sh" --staged
fi

# Run response_model coverage check on changed API files
if [ -f "$REPO_ROOT/scripts/check_response_model_coverage.py" ]; then
    python3 "$REPO_ROOT/scripts/check_response_model_coverage.py" --staged
fi

# Run API route-prefix test coverage check on changed API files
if [ -f "$REPO_ROOT/scripts/check_api_test_coverage.py" ]; then
    python3 "$REPO_ROOT/scripts/check_api_test_coverage.py" --staged
fi

# Run frontend->E2E mapping check on changed frontend files
if [ -f "$REPO_ROOT/scripts/check_frontend_e2e_mapping.py" ]; then
    python3 "$REPO_ROOT/scripts/check_frontend_e2e_mapping.py" --staged
fi

# Ensure skill.md edits bump version and header guidance
if [ -f "$REPO_ROOT/scripts/check_skill_version_bump.sh" ]; then
    "$REPO_ROOT/scripts/check_skill_version_bump.sh" --staged
fi
EOF

chmod +x "$HOOKS_DIR/pre-commit"

# Create pre-push hook (BLOCKING — requires DST coverage + test pass)
cat > "$HOOKS_DIR/pre-push" << 'PUSHEOF'
#!/bin/bash
#
# Pre-push hook for deep-sci-fi
# BLOCKING: Prevents push if:
#   1. Required reviewers fail (code + dst for DST-sensitive changes)
#   2. Review markers fail (code + dst for DST-sensitive changes)
#   3. Universal policy checks fail (response models, API tests, E2E mapping, skill version)
#   4. DST coverage check fails (new uncovered state-mutating endpoints)
#   5. DST simulation tests fail (seed 0)
#
# Skip with: git push --no-verify (emergencies only)
#

REPO_ROOT=$(git rev-parse --show-toplevel)
BACKEND="$REPO_ROOT/platform/backend"
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
REMOTE_REF="origin/$BRANCH"

# Build a diff range for commit-aware checks
if git show-ref --verify --quiet "refs/remotes/$REMOTE_REF"; then
    DIFF_RANGE="$REMOTE_REF...HEAD"
else
    DIFF_RANGE="HEAD~1...HEAD"
fi

# Universal policy checks (tool-agnostic parity with Claude-only hook checks)
if [ -f "$REPO_ROOT/scripts/run_required_reviews.sh" ]; then
    "$REPO_ROOT/scripts/run_required_reviews.sh" --diff-range "$DIFF_RANGE"
fi

if [ -f "$REPO_ROOT/scripts/check_review_markers.sh" ]; then
    "$REPO_ROOT/scripts/check_review_markers.sh" --diff-range "$DIFF_RANGE"
fi

if [ -f "$REPO_ROOT/scripts/check_response_model_coverage.py" ]; then
    python3 "$REPO_ROOT/scripts/check_response_model_coverage.py" --diff-range "$DIFF_RANGE"
fi

if [ -f "$REPO_ROOT/scripts/check_api_test_coverage.py" ]; then
    python3 "$REPO_ROOT/scripts/check_api_test_coverage.py" --diff-range "$DIFF_RANGE"
fi

if [ -f "$REPO_ROOT/scripts/check_frontend_e2e_mapping.py" ]; then
    python3 "$REPO_ROOT/scripts/check_frontend_e2e_mapping.py" --diff-range "$DIFF_RANGE"
fi

if [ -f "$REPO_ROOT/scripts/check_skill_version_bump.sh" ]; then
    "$REPO_ROOT/scripts/check_skill_version_bump.sh" --diff-range "$DIFF_RANGE"
fi

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
echo "  - pre-commit: Missing migrations"
echo "  - pre-commit: skill.md endpoint sync + version bump"
echo "  - pre-commit: auto-run required reviewers via codex review"
echo "  - pre-commit: review markers (code + dst for DST-sensitive changes)"
echo "  - pre-commit: API response_model and API route-prefix test coverage"
echo "  - pre-commit: Frontend->E2E mapped spec updates"
echo "  - pre-push:   auto-run required reviewers + marker check"
echo "  - pre-push:   universal policy checks against branch diff"
echo "  - pre-push:   BLOCKING — DST coverage + simulation test (seed 0)"
echo ""
echo "To bypass hooks in emergencies: git push --no-verify"
