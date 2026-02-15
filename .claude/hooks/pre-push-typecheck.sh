#!/bin/bash
# Pre-push type check hook
# Blocks git push if TypeScript doesn't compile.
#
# Hook type: PreToolUse (Bash matcher)
# Triggers on: git push commands
# Output: { "decision": "block", "reason": "..." } or {}

set -euo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null || echo "")

# Only trigger on git push
if ! echo "$COMMAND" | grep -qE '^\s*git\s+push\b'; then
  echo '{}'
  exit 0
fi

PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")
PLATFORM_DIR="$PROJECT_ROOT/platform"

# Check if there are frontend changes since last push
# (comparing working tree to the remote tracking branch)
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
REMOTE_REF="origin/$BRANCH"

# Check if any .ts/.tsx files changed
FRONTEND_CHANGED=$(git diff --name-only "$REMOTE_REF" HEAD 2>/dev/null | grep -E '\.(ts|tsx)$' || true)

if [ -z "$FRONTEND_CHANGED" ]; then
  # No frontend changes — skip typecheck
  echo '{}'
  exit 0
fi

# Run TypeScript type check
if [ -d "$PLATFORM_DIR" ]; then
  cd "$PLATFORM_DIR"

  # Check if node_modules exists
  if [ ! -d "node_modules" ]; then
    cat <<ENDJSON
{
  "decision": "block",
  "reason": "Cannot run type check: node_modules not found in platform/. Run 'cd platform && bun install' first."
}
ENDJSON
    exit 0
  fi

  # Run tsc --noEmit
  TSC_OUTPUT=$(npx tsc --noEmit 2>&1) || {
    # TypeScript compilation failed
    # Truncate output if too long
    TRUNCATED=$(echo "$TSC_OUTPUT" | head -30)
    LINE_COUNT=$(echo "$TSC_OUTPUT" | wc -l | tr -d ' ')

    if [ "$LINE_COUNT" -gt 30 ]; then
      TRUNCATED="$TRUNCATED
... ($LINE_COUNT total lines, showing first 30)"
    fi

    # Escape for JSON
    ESCAPED=$(echo "$TRUNCATED" | jq -Rs .)

    cat <<ENDJSON
{
  "decision": "block",
  "reason": "TypeScript compilation failed. Fix these errors before pushing:\n\n$( echo "$TRUNCATED" | sed 's/"/\\"/g; s/$/\\n/' | tr -d '\n' )"
}
ENDJSON
    exit 0
  }

  # TypeScript compiled successfully
  echo '{}'
else
  echo '{}'
fi
