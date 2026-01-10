#!/bin/bash
# Pre-push review hook for TigerStyle development
# Runs a comprehensive review before pushing changes

set -e

BASE=${1:-main}
BRANCH=$(git branch --show-current)

echo "[REVIEW] Reviewing $BASE..$BRANCH"

# Get the repo root
REPO_ROOT=$(git rev-parse --show-toplevel)

# Get list of changed files
CHANGED_FILES=$(git diff --name-only "$BASE"..."$BRANCH" 2>/dev/null || git diff --name-only HEAD~5...HEAD)

echo "[REVIEW] Changed files: $(echo "$CHANGED_FILES" | wc -l | tr -d ' ')"

# 1. Check for new TODOs
echo ""
echo "[REVIEW] === Checking for new TODOs ==="
DIFF=$(git diff "$BASE"..."$BRANCH" 2>/dev/null || git diff HEAD~5...HEAD)
NEW_TODOS=$(echo "$DIFF" | grep '^\+' | grep -c 'TODO\|FIXME\|HACK' 2>/dev/null || echo "0")
if [ "$NEW_TODOS" -gt 0 ]; then
    echo "[REVIEW] ⚠ $NEW_TODOS new TODO/FIXME/HACK comments found"
    echo "$DIFF" | grep '^\+.*TODO\|^\+.*FIXME\|^\+.*HACK' | head -10
fi

# 2. Check vision file modifications
echo ""
echo "[REVIEW] === Checking vision file changes ==="
VISION_CHANGES=$(echo "$CHANGED_FILES" | grep '\.vision/' || true)
if [ -n "$VISION_CHANGES" ]; then
    echo "[REVIEW] ⚠ .vision/ files modified - verify intentional:"
    echo "$VISION_CHANGES"
fi

# 3. Check for test coverage
echo ""
echo "[REVIEW] === Checking test coverage ==="
CHANGED_TS=$(echo "$CHANGED_FILES" | grep '\.ts$\|\.tsx$' | grep -v '\.test\.\|spec\.' || true)
for file in $CHANGED_TS; do
    # Skip files in tests/ directories
    if echo "$file" | grep -q '/tests/\|/test/\|/__tests__/'; then
        continue
    fi

    # Look for corresponding test file
    TEST_FILE="${file%.ts}.test.ts"
    TEST_FILE2="${file%.tsx}.test.tsx"
    TEST_FILE3=$(echo "$file" | sed 's/src\//tests\//').test.ts

    if [ ! -f "$REPO_ROOT/$TEST_FILE" ] && [ ! -f "$REPO_ROOT/$TEST_FILE2" ] && [ ! -f "$REPO_ROOT/$TEST_FILE3" ]; then
        echo "[REVIEW] ⚠ No test file found for: $file"
    fi
done

# 4. Check submodule status
echo ""
echo "[REVIEW] === Checking submodule status ==="
cd "$REPO_ROOT"
SUBMODULE_STATUS=$(git submodule foreach --quiet 'echo "$name: $(git status --porcelain | wc -l | tr -d " ") uncommitted changes"' 2>/dev/null || true)
if [ -n "$SUBMODULE_STATUS" ]; then
    echo "$SUBMODULE_STATUS"
fi

# 5. Verify plan exists and is complete
echo ""
echo "[REVIEW] === Checking plan status ==="
PLAN=$(ls -t "$REPO_ROOT/.progress"/*.md 2>/dev/null | grep -v archive | grep -v templates | head -1)
if [ -n "$PLAN" ]; then
    STATE=$(grep -oP '^\*\*State:\*\*\s*\K\w+' "$PLAN" 2>/dev/null || echo "UNKNOWN")
    echo "[REVIEW] Active plan: $(basename "$PLAN")"
    echo "[REVIEW] Plan state: $STATE"

    if [ "$STATE" != "COMPLETE" ] && [ "$STATE" != "VERIFYING" ]; then
        echo "[REVIEW] ⚠ Plan not in VERIFYING or COMPLETE state"
    fi
else
    echo "[REVIEW] ⚠ No active plan found"
fi

# 6. Quick summary
echo ""
echo "[REVIEW] === Summary ==="
echo "[REVIEW] Branch: $BRANCH"
echo "[REVIEW] Files changed: $(echo "$CHANGED_FILES" | wc -l | tr -d ' ')"
echo "[REVIEW] New TODOs: $NEW_TODOS"

# 7. Remind about CI
echo ""
echo "[REVIEW] Remember: CI will run full review with Claude Opus 4.5"
echo "[REVIEW] Local review complete"
