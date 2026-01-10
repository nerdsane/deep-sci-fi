#!/bin/bash
# Pre-commit verification hook for TigerStyle development
# This hook runs before commits to ensure quality gates pass

set -e

echo "[GATE] Running pre-commit verification..."

# Get the repo root
REPO_ROOT=$(git rev-parse --show-toplevel)

# 1. Check for active plan in correct state
echo "[GATE] Checking plan state..."
PLAN=$(ls -t "$REPO_ROOT/.progress"/*.md 2>/dev/null | grep -v archive | grep -v templates | head -1)
if [ -n "$PLAN" ]; then
    STATE=$(grep -oP '^\*\*State:\*\*\s*\K\w+' "$PLAN" 2>/dev/null || echo "UNKNOWN")
    if [ "$STATE" != "VERIFYING" ] && [ "$STATE" != "COMPLETE" ]; then
        echo "[GATE] ⚠ Plan state is $STATE, not VERIFYING/COMPLETE"
        echo "[GATE] Consider updating plan state before committing"
        # Warning only - don't block
    else
        echo "[GATE] ✓ Plan state: $STATE"
    fi
else
    echo "[GATE] ⚠ No active plan found (consider creating .progress/ plan)"
fi

# 2. Run tests in letta-code if it exists and has changes
if [ -d "$REPO_ROOT/letta-code" ]; then
    LETTA_CODE_CHANGES=$(git diff --cached --name-only -- 'letta-code/*.ts' 'letta-code/*.tsx' 2>/dev/null || true)
    if [ -n "$LETTA_CODE_CHANGES" ]; then
        echo "[GATE] Running letta-code tests..."
        if (cd "$REPO_ROOT/letta-code" && bun test 2>/dev/null); then
            echo "[GATE] ✓ letta-code tests passed"
        else
            echo "[GATE] ✗ letta-code tests failed"
            exit 1
        fi
    fi
fi

# 3. Run typecheck in letta-code if it exists and has changes
if [ -d "$REPO_ROOT/letta-code" ] && [ -n "$LETTA_CODE_CHANGES" ]; then
    echo "[GATE] Running letta-code typecheck..."
    if (cd "$REPO_ROOT/letta-code" && bun run typecheck 2>/dev/null); then
        echo "[GATE] ✓ letta-code typecheck passed"
    else
        echo "[GATE] ✗ letta-code typecheck failed"
        exit 1
    fi
fi

# 4. Run typecheck in letta-ui if it exists and has changes
if [ -d "$REPO_ROOT/letta-ui" ]; then
    LETTA_UI_CHANGES=$(git diff --cached --name-only -- 'letta-ui/*.ts' 'letta-ui/*.tsx' 2>/dev/null || true)
    if [ -n "$LETTA_UI_CHANGES" ]; then
        echo "[GATE] Running letta-ui typecheck..."
        if (cd "$REPO_ROOT/letta-ui" && bun run typecheck 2>/dev/null); then
            echo "[GATE] ✓ letta-ui typecheck passed"
        else
            echo "[GATE] ✗ letta-ui typecheck failed"
            exit 1
        fi
    fi
fi

# 5. Check for console.log in staged TypeScript files (warning only)
echo "[GATE] Checking for debug statements..."
STAGED_TS=$(git diff --cached --name-only -- '*.ts' '*.tsx' | grep -v '.test.' | grep -v 'spec.' || true)
if [ -n "$STAGED_TS" ]; then
    CONSOLE_LOGS=$(echo "$STAGED_TS" | xargs grep -l 'console.log' 2>/dev/null || true)
    if [ -n "$CONSOLE_LOGS" ]; then
        echo "[GATE] ⚠ console.log found in staged files:"
        echo "$CONSOLE_LOGS"
        # Warning only
    fi
fi

# 6. Check for TODO/FIXME/HACK in staged files (warning only)
echo "[GATE] Checking for placeholders..."
if [ -n "$STAGED_TS" ]; then
    # Count new TODOs (lines being added)
    NEW_TODOS=$(git diff --cached -- $STAGED_TS | grep '^\+' | grep -c 'TODO\|FIXME\|HACK' 2>/dev/null || echo "0")
    if [ "$NEW_TODOS" -gt 0 ]; then
        echo "[GATE] ⚠ $NEW_TODOS new TODO/FIXME/HACK comments being added"
        # Warning only
    fi
fi

# 7. Check .vision/ files weren't accidentally modified (warning)
VISION_CHANGES=$(git diff --cached --name-only -- '.vision/*.md' 2>/dev/null || true)
if [ -n "$VISION_CHANGES" ]; then
    echo "[GATE] ⚠ .vision/ files modified - verify this is intentional:"
    echo "$VISION_CHANGES"
fi

echo "[GATE] ✓ Pre-commit verification complete"
exit 0
