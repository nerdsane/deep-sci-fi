#!/bin/bash
# PostToolUse hook: when a backend API file is created or modified,
# check that integration tests exist for all endpoints in that file.
#
# Hook type: PostToolUse (Edit|Write matcher)
# Input: JSON on stdin with tool_name, tool_input
# Output: JSON with additionalContext if untested endpoints detected
#
# This catches the exact class of bugs where CC creates a new endpoint
# but never writes a test that actually hits it via HTTP.

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

# Extract route decorators from the API file
ROUTES=$(grep -oE '@router\.(get|post|put|patch|delete)\("([^"]+)"' "$FULL_PATH" 2>/dev/null | sed 's/@router\.\(get\|post\|put\|patch\|delete\)("/\1 /g' | sed 's/"$//' || true)

if [ -z "$ROUTES" ]; then
  echo '{}'
  exit 0
fi

# Extract the router prefix
PREFIX=$(grep -oE 'prefix="([^"]+)"' "$FULL_PATH" 2>/dev/null | head -1 | sed 's/prefix="//;s/"//' || echo "")

# Get the module name (e.g., "arcs" from "arcs.py")
MODULE=$(basename "$FILE_PATH" .py)

# Look for test files that reference this module's endpoints
TEST_DIR="$REPO_ROOT/platform/backend/tests"
E2E_DIR="$REPO_ROOT/platform/e2e"

# Search for any test that hits these endpoints
TESTED_ROUTES=""
if [ -d "$TEST_DIR" ]; then
  TESTED_ROUTES=$(grep -rn "$PREFIX" "$TEST_DIR" --include="*.py" 2>/dev/null | grep -v __pycache__ | grep -v .venv || true)
fi
if [ -d "$E2E_DIR" ]; then
  TESTED_ROUTES="$TESTED_ROUTES$(grep -rn "$PREFIX" "$E2E_DIR" --include="*.ts" 2>/dev/null || true)"
fi

# Count routes vs tested routes
ROUTE_COUNT=$(echo "$ROUTES" | grep -c '.' || echo "0")
TESTED_COUNT=0
if [ -n "$TESTED_ROUTES" ]; then
  TESTED_COUNT=$(echo "$TESTED_ROUTES" | grep -c '.' || echo "0")
fi

if [ "$TESTED_COUNT" -eq 0 ] && [ "$ROUTE_COUNT" -gt 0 ]; then
  cat <<ENDJSON
{
  "additionalContext": "⚠️ UNTESTED API ENDPOINTS DETECTED in $FILE_PATH\n\nYou created/modified $ROUTE_COUNT endpoint(s) under prefix '$PREFIX' but NO tests exist that hit these routes.\n\nRoutes found:\n$(echo "$ROUTES" | sed 's/^/  /')\n\nYou MUST write integration tests that:\n1. Actually send HTTP requests to each new endpoint\n2. Assert the status code is 200 (not 404, not 422)\n3. Assert the response shape matches the expected schema\n4. Test with empty data and with populated data\n\nPut tests in platform/backend/tests/test_${MODULE}.py or add to an existing test file.\nRun: cd platform/backend && python3 -m pytest tests/test_${MODULE}.py -v\n\nDo NOT push without these tests. A 'tsc pass' and 'pytest pass' mean nothing if no test actually hits your new endpoint."
}
ENDJSON
  exit 0
fi

echo '{}'
