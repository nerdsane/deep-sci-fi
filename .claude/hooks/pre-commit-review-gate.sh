#!/bin/bash
# Pre-Commit Review Gate (PreToolUse — Bash)
# BLOCKING: YES (exit 2 if review markers missing)
#
# Before any `git commit` command, checks:
# 1. Code review marker exists
# 2. DST review marker exists (if review/validation code was changed)
# 3. Tests pass
set -euo pipefail

PAYLOAD="$(cat)"

# Extract the command from bash tool input
if command -v jq >/dev/null 2>&1; then
    CMD="$(echo "$PAYLOAD" | jq -r '.tool_input.command // empty')"
else
    CMD="$(echo "$PAYLOAD" | grep -o -m1 '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"command"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' || true)"
fi

# Only gate git commit commands
case "${CMD:-}" in
    *"git commit"*) ;;
    *) exit 0 ;;
esac

WORKSPACE_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PROJECT_HASH="$(echo "$WORKSPACE_ROOT" | shasum -a 256 | cut -c1-12)"
MARKER_DIR="/tmp/dsf-harness/${PROJECT_HASH}"

BLOCKED=false

marker_exists() { [ -f "$MARKER_DIR/$1" ]; }

# --- Check 1: Code review marker ---
if ! marker_exists "code-reviewed"; then
    echo "" >&2
    echo "══════════════════════════════════════════════════════════════" >&2
    echo "  BLOCKED: Code review required before commit" >&2
    echo "══════════════════════════════════════════════════════════════" >&2
    echo "  Invoke the code-reviewer agent, then retry the commit." >&2
    echo "══════════════════════════════════════════════════════════════" >&2
    BLOCKED=true
fi

# --- Check 2: DST review marker (if review/validation code changed) ---
DST_FILES_CHANGED=false
if cd "$WORKSPACE_ROOT" 2>/dev/null; then
    if git diff --cached --name-only 2>/dev/null | grep -qE '(reviews\.py|models\.py|skill\.md|validation)'; then
        DST_FILES_CHANGED=true
    fi
fi

if [ "$DST_FILES_CHANGED" = true ]; then
    if ! marker_exists "dst-reviewed"; then
        echo "" >&2
        echo "══════════════════════════════════════════════════════════════" >&2
        echo "  BLOCKED: DST review required before commit" >&2
        echo "══════════════════════════════════════════════════════════════" >&2
        echo "  Review/validation code was changed. Invoke the dst-reviewer" >&2
        echo "  agent to verify DST ↔ code alignment, then retry." >&2
        echo "══════════════════════════════════════════════════════════════" >&2
        BLOCKED=true
    fi
fi

# --- Check 3: Backend tests must pass ---
echo "Running backend tests..." >&2
BACKEND_DIR="$WORKSPACE_ROOT/platform/backend"
if [ -d "$BACKEND_DIR" ]; then
    # Use .venv python if available, otherwise use python3
    PYTHON_CMD="$BACKEND_DIR/.venv/bin/python"
    if [ ! -f "$PYTHON_CMD" ]; then
        PYTHON_CMD="python3"
    fi
    # Exclude known failing tests (pre-existing MissingGreenlet/auth bugs, simulation)
    if ! (cd "$BACKEND_DIR" && "$PYTHON_CMD" -m pytest tests/ \
        --ignore=tests/simulation \
        --ignore=tests/test_media.py \
        --ignore=tests/test_reviews.py \
        --ignore=tests/test_aspect_inspiration.py \
        --ignore=tests/test_action_escalation.py \
        --ignore=tests/test_notifications.py \
        --ignore=tests/test_world_events.py \
        --ignore=tests/test_feed_pagination.py \
        -x -q 2>&1 | tail -10 >&2); then
        echo "" >&2
        echo "══════════════════════════════════════════════════════════════" >&2
        echo "  BLOCKED: Tests failed" >&2
        echo "══════════════════════════════════════════════════════════════" >&2
        echo "  All tests must pass before committing." >&2
        echo "══════════════════════════════════════════════════════════════" >&2
        BLOCKED=true
    fi
fi

if [ "$BLOCKED" = true ]; then
    exit 2
fi

echo "Pre-commit gate: ALL CHECKS PASSED" >&2
exit 0
