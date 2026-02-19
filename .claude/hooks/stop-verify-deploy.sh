#!/bin/bash
# Stop hook: blocks session end if a push happened without verification
#
# Hook type: Stop
# Input: JSON on stdin (session context)
# Output: JSON on stdout — { "decision": "block", "reason": "..." } or {}
#
# Coordination:
#   post-push-verify.sh creates /tmp/claude-deepsci/{hash}/push-pending
#   verify-deployment.sh creates /tmp/claude-deepsci/{hash}/deploy-verified
#   Markers are scoped by project directory hash (no session suffix —
#   $PPID is NOT stable across hook invocations in Claude Code).

set -euo pipefail

# Scope markers by project directory hash
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")
PROJECT_HASH=$(printf '%s' "$PROJECT_ROOT" | cksum | cut -d' ' -f1)
MARKER_DIR="/tmp/claude-deepsci/$PROJECT_HASH"
PUSH_MARKER="$MARKER_DIR/push-pending"
VERIFY_MARKER="$MARKER_DIR/deploy-verified"

if [ -f "$PUSH_MARKER" ]; then
  BRANCH=$(cat "$PUSH_MARKER" 2>/dev/null || echo "unknown")

  if [ ! -f "$VERIFY_MARKER" ]; then
    # Pushed but hasn't verified — block
    if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
      ENV="production"
    else
      ENV="staging"
    fi

    cat <<ENDJSON
{
  "decision": "block",
  "reason": "You pushed to $BRANCH but haven't verified the deployment. Run: bash scripts/verify-deployment.sh $ENV\n\nVerification checks: CI status, deployment health, smoke test, schema drift.\n\nYou cannot end this session until deployment is verified."
}
ENDJSON
    exit 0
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Check 2: E2E test coverage for frontend changes
# ─────────────────────────────────────────────────────────────────────────────
E2E_PENDING="$MARKER_DIR/e2e-pending"
E2E_TOUCHED="$MARKER_DIR/e2e-touched"

if [ -f "$E2E_PENDING" ] && [ ! -f "$E2E_TOUCHED" ]; then
  TEST_FILE=$(cat "$E2E_PENDING")
  cat <<ENDJSON
{
  "decision": "block",
  "reason": "You modified frontend files but didn't update the corresponding E2E test ($TEST_FILE). Update the test and run 'cd platform && bun run test:e2e' before ending the session."
}
ENDJSON
  exit 0
fi

# ─────────────────────────────────────────────────────────────────────────────
# Check 3: Clean up review markers on successful exit
# ─────────────────────────────────────────────────────────────────────────────
DSF_MARKER_DIR="/tmp/dsf-harness/$(echo "$PROJECT_ROOT" | shasum -a 256 | cut -c1-12)"
rm -f "$DSF_MARKER_DIR/code-reviewed" "$DSF_MARKER_DIR/dst-reviewed" 2>/dev/null

# Clean up all markers on successful exit
rm -f "$PUSH_MARKER" "$VERIFY_MARKER" "$E2E_PENDING" "$E2E_TOUCHED" 2>/dev/null

# No pending push and no unmatched frontend edits — allow stop
echo '{}'
