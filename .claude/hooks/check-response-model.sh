#!/bin/bash
# PostToolUse hook: when a backend API file is created or modified,
# check that all endpoints have response_model= or responses=.
#
# Hook type: PostToolUse (Edit|Write matcher)
# Input: JSON on stdin with tool_name, tool_input
# Output: JSON with additionalContext if untyped endpoints detected
#
# Enforces full Pydantic response coverage — every endpoint must declare
# its response shape via response_model= or responses= (for SSE/complex).

set -euo pipefail

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""' 2>/dev/null || echo "")

if [ -z "$FILE_PATH" ]; then
  echo '{}'
  exit 0
fi

# Only trigger for backend API files
if ! echo "$FILE_PATH" | grep -qE 'platform/backend/api/.*\.py$'; then
  echo '{}'
  exit 0
fi

# Skip __init__.py
if echo "$FILE_PATH" | grep -qE '__init__\.py$'; then
  echo '{}'
  exit 0
fi

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")
FULL_PATH="$REPO_ROOT/$FILE_PATH"

if [ ! -f "$FULL_PATH" ]; then
  echo '{}'
  exit 0
fi

# Find endpoint decorators missing both response_model= and responses=
# Strategy: extract decorator lines, filter out those with response_model or responses
MISSING=""
while IFS= read -r line; do
  LINE_NUM=$(echo "$line" | cut -d: -f1)
  LINE_TEXT=$(echo "$line" | cut -d: -f2-)

  # Skip include_in_schema=False (admin/internal endpoints)
  if echo "$LINE_TEXT" | grep -q 'include_in_schema=False'; then
    continue
  fi

  # Check if this decorator has response_model= or responses=
  if ! echo "$LINE_TEXT" | grep -qE 'response_model=|responses='; then
    MISSING="${MISSING}  Line ${LINE_NUM}: ${LINE_TEXT}\n"
  fi
done < <(grep -n '@router\.\(get\|post\|put\|patch\|delete\)(' "$FULL_PATH" 2>/dev/null || true)

if [ -z "$MISSING" ]; then
  echo '{}'
  exit 0
fi

# Count missing
MISSING_COUNT=$(echo -e "$MISSING" | grep -c '.' || echo "0")

cat <<ENDJSON
{
  "additionalContext": "⚠️ MISSING response_model= IN $FILE_PATH\n\n${MISSING_COUNT} endpoint(s) have no response_model= or responses= parameter:\n\n$(echo -e "$MISSING")\n\nEvery endpoint MUST declare its response shape:\n  - Use response_model=MySchema for standard endpoints\n  - Use responses={200: {\"model\": MySchema}} for SSE or complex responses\n  - Use include_in_schema=False for admin-only internal endpoints\n\nAdd a Pydantic response schema in platform/backend/schemas/ and wire it to the endpoint decorator."
}
ENDJSON
