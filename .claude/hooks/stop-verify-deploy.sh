#!/bin/bash
# Stop hook: blocks session end if a git push happened without deploy verification
#
# Hook type: Stop
# Input: JSON on stdin (session context)
# Output: JSON on stdout — { "decision": "block", "reason": "..." } or {}
#
# Coordination:
#   post-push-verify.sh creates /tmp/claude-deepsci/{hash}/push-pending
#   verify-deployment.sh creates /tmp/claude-deepsci/{hash}/deploy-verified
#   Markers are scoped by project directory hash to isolate worktrees/sessions.
#   This hook blocks if push-pending exists but deploy-verified does not.

set -euo pipefail

# Scope markers by project directory to avoid cross-session interference
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")
PROJECT_HASH=$(printf '%s' "$PROJECT_ROOT" | cksum | cut -d' ' -f1)
MARKER_DIR="/tmp/claude-deepsci/$PROJECT_HASH"
PUSH_MARKER="$MARKER_DIR/push-pending"
VERIFY_MARKER="$MARKER_DIR/deploy-verified"

if [ -f "$PUSH_MARKER" ]; then
  BRANCH=$(cat "$PUSH_MARKER" 2>/dev/null || echo "unknown")

  if [ ! -f "$VERIFY_MARKER" ]; then
    # Push happened but no verification — block
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

# No pending push, or verification done — allow stop
echo '{}'
