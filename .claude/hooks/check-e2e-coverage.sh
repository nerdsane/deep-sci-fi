#!/bin/bash
# PostToolUse hook: detects frontend file edits and reminds about E2E test updates.
#
# Hook type: PostToolUse (Edit|Write matcher)
# Input: JSON on stdin with tool_name, tool_input
# Output: JSON on stdout with additionalContext if frontend file detected
#
# Coordination:
#   Creates /tmp/claude-deepsci/{hash}/e2e-pending when frontend changed
#   Creates /tmp/claude-deepsci/{hash}/e2e-touched when e2e test changed
#   stop-verify-deploy.sh checks these markers before allowing session exit.
#   No session suffix — $PPID is NOT stable across hook invocations.

set -euo pipefail

INPUT=$(cat)

# Extract file_path from tool input
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""' 2>/dev/null || echo "")

if [ -z "$FILE_PATH" ]; then
  echo '{}'
  exit 0
fi

# Scope markers by project directory hash (no session suffix)
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")
PROJECT_HASH=$(printf '%s' "$PROJECT_ROOT" | cksum | cut -d' ' -f1)
MARKER_DIR="/tmp/claude-deepsci/$PROJECT_HASH"
mkdir -p "$MARKER_DIR"

# Clean stale markers (older than 4 hours)
find "$MARKER_DIR" -name 'e2e-pending' -mmin +240 -delete 2>/dev/null || true
find "$MARKER_DIR" -name 'e2e-touched' -mmin +240 -delete 2>/dev/null || true
# Also clean up old session-scoped markers from before this fix
find "$MARKER_DIR" -name 'e2e-pending-*' -delete 2>/dev/null || true
find "$MARKER_DIR" -name 'e2e-touched-*' -delete 2>/dev/null || true

# ─────────────────────────────────────────────────────────────────────────────
# Case 1: E2E test file was modified — mark as touched
# ─────────────────────────────────────────────────────────────────────────────
if echo "$FILE_PATH" | grep -qE 'platform/e2e/.*\.spec\.ts$'; then
  touch "$MARKER_DIR/e2e-touched"
  echo '{}'
  exit 0
fi

# ─────────────────────────────────────────────────────────────────────────────
# Case 2: Frontend file was modified — determine corresponding test file
# ─────────────────────────────────────────────────────────────────────────────

# Route mapping: frontend path pattern → e2e test file
TEST_FILE=""

if echo "$FILE_PATH" | grep -qE 'platform/app/page\.tsx$'; then
  TEST_FILE="smoke.spec.ts"
elif echo "$FILE_PATH" | grep -qE 'platform/app/how-it-works/'; then
  TEST_FILE="smoke.spec.ts"
elif echo "$FILE_PATH" | grep -qE 'platform/app/feed/'; then
  TEST_FILE="feed.spec.ts"
elif echo "$FILE_PATH" | grep -qE 'platform/app/worlds/'; then
  TEST_FILE="worlds.spec.ts"
elif echo "$FILE_PATH" | grep -qE 'platform/app/world/'; then
  TEST_FILE="worlds.spec.ts"
elif echo "$FILE_PATH" | grep -qE 'platform/app/proposals/'; then
  TEST_FILE="proposals.spec.ts"
elif echo "$FILE_PATH" | grep -qE 'platform/app/proposal/'; then
  TEST_FILE="proposals.spec.ts"
elif echo "$FILE_PATH" | grep -qE 'platform/app/agents/'; then
  TEST_FILE="agents.spec.ts"
elif echo "$FILE_PATH" | grep -qE 'platform/app/agent/'; then
  TEST_FILE="agents.spec.ts"
elif echo "$FILE_PATH" | grep -qE 'platform/app/stories/'; then
  TEST_FILE="stories.spec.ts"
elif echo "$FILE_PATH" | grep -qE 'platform/app/dweller/'; then
  TEST_FILE="dweller.spec.ts"
elif echo "$FILE_PATH" | grep -qE 'platform/app/aspect/'; then
  TEST_FILE="aspect.spec.ts"
elif echo "$FILE_PATH" | grep -qE 'platform/components/world/'; then
  TEST_FILE="worlds.spec.ts"
elif echo "$FILE_PATH" | grep -qE 'platform/components/feed/'; then
  TEST_FILE="feed.spec.ts"
elif echo "$FILE_PATH" | grep -qE 'platform/components/social/'; then
  TEST_FILE="multiple test files"
fi

if [ -n "$TEST_FILE" ]; then
  echo "$TEST_FILE" > "$MARKER_DIR/e2e-pending"

  cat <<ENDJSON
{
  "additionalContext": "You modified a frontend file ($FILE_PATH). The corresponding E2E test is platform/e2e/$TEST_FILE — consider updating it if you changed user-visible behavior. Run 'cd platform && bun run test:e2e' before pushing."
}
ENDJSON
  exit 0
fi

# Not a frontend file — no action needed
echo '{}'
