#!/bin/bash
# Post-push verification hook
# Detects git push AND gh pr merge in Bash tool output.
# Injects mandatory verification context for both staging and production.
#
# Hook type: PostToolUse (Bash matcher)
# Input: JSON on stdin with tool_name, tool_input, tool_output
# Output: JSON on stdout with additionalContext if deployment detected

set -euo pipefail

# Read the hook input from stdin
INPUT=$(cat)

# Extract the command that was run
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null || echo "")

MARKER_DIR="/tmp/claude-deepsci"
mkdir -p "$MARKER_DIR"

# ─────────────────────────────────────────────────────────────────────────────
# Case 1: Direct git push
# ─────────────────────────────────────────────────────────────────────────────
if echo "$COMMAND" | grep -qE '^\s*git\s+push\b'; then
  BRANCH=$(echo "$COMMAND" | grep -oE '(staging|main|master)' | head -1)
  BRANCH=${BRANCH:-"unknown"}

  echo "$BRANCH" > "$MARKER_DIR/push-pending"
  rm -f "$MARKER_DIR/deploy-verified"

  if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
    ENV="production"
  else
    ENV="staging"
  fi

  cat <<ENDJSON
{
  "additionalContext": "MANDATORY POST-DEPLOY VERIFICATION: You just pushed to $BRANCH. You MUST now verify the deployment before doing anything else or ending the session.\n\nRun: bash scripts/verify-deployment.sh $ENV\n\nThis script verifies:\n1. CI completes successfully\n2. Backend is healthy\n3. Frontend is healthy\n4. Smoke test passes\n5. No schema drift\n6. No 500 errors in Logfire\n\nYou CANNOT end this session until verification passes."
}
ENDJSON

# ─────────────────────────────────────────────────────────────────────────────
# Case 2: PR merge (any branch that deploys)
# ─────────────────────────────────────────────────────────────────────────────
elif echo "$COMMAND" | grep -qE 'gh\s+pr\s+merge'; then
  # Determine target branch
  if echo "$COMMAND" | grep -qE '(--branch\s+staging|-B\s+staging)'; then
    # Merging to staging
    echo "staging" > "$MARKER_DIR/push-pending"
    rm -f "$MARKER_DIR/deploy-verified"

    cat <<ENDJSON
{
  "additionalContext": "MANDATORY STAGING VERIFICATION: You just merged a PR to staging.\n\nYou MUST now verify the staging deployment:\n\nRun: bash scripts/verify-deployment.sh staging\n\nThis script verifies:\n1. CI/Deploy workflow completes\n2. Backend is healthy\n3. Frontend is healthy\n4. All 9 API endpoints respond\n5. No schema drift\n6. No 500 errors in Logfire (last 30 min)\n\nYou CANNOT end this session until verification passes."
}
ENDJSON
  else
    # Merging to main (explicitly or by default)
    echo "main" > "$MARKER_DIR/push-pending"
    rm -f "$MARKER_DIR/deploy-verified"

    cat <<ENDJSON
{
  "additionalContext": "MANDATORY PRODUCTION VERIFICATION: You just merged a PR to main. This deploys to PRODUCTION.\n\nYou MUST now verify the production deployment:\n\nRun: bash scripts/verify-deployment.sh production\n\nThis script verifies:\n1. CI/Deploy workflow completes\n2. Backend (api.deep-sci-fi.world) is healthy\n3. Frontend (deep-sci-fi.world) is healthy\n4. All 9 API endpoints respond\n5. No schema drift\n6. No 500 errors in Logfire (last 30 min)\n\nPRODUCTION IS LIVE. You CANNOT end this session until verification passes.\n\nIf verification fails, you must fix the issue immediately."
}
ENDJSON
  fi

# ─────────────────────────────────────────────────────────────────────────────
# Case 3: Not a deployment action
# ─────────────────────────────────────────────────────────────────────────────
else
  echo '{}'
fi
