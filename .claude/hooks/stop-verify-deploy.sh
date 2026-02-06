#!/bin/bash
# Stop hook: blocks session end if THIS session pushed without verification
#
# Hook type: Stop
# Input: JSON on stdin (session context)
# Output: JSON on stdout — { "decision": "block", "reason": "..." } or {}
#
# Coordination:
#   post-push-verify.sh creates /tmp/claude-deepsci/{hash}/push-pending-{session}
#   verify-deployment.sh creates /tmp/claude-deepsci/{hash}/deploy-verified-{session}
#   Markers are scoped by project directory hash AND session ID ($PPID).
#   Only THIS session's markers are checked — parallel sessions never interfere.

set -euo pipefail

# Session ID = Claude Code PID (parent of this hook process)
SESSION_ID=$PPID

# Scope markers by project directory + session ID
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")
PROJECT_HASH=$(printf '%s' "$PROJECT_ROOT" | cksum | cut -d' ' -f1)
MARKER_DIR="/tmp/claude-deepsci/$PROJECT_HASH"
PUSH_MARKER="$MARKER_DIR/push-pending-$SESSION_ID"
VERIFY_MARKER="$MARKER_DIR/deploy-verified-$SESSION_ID"

if [ -f "$PUSH_MARKER" ]; then
  BRANCH=$(cat "$PUSH_MARKER" 2>/dev/null || echo "unknown")

  if [ ! -f "$VERIFY_MARKER" ]; then
    # This session pushed but hasn't verified — block
    if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
      ENV="production"
    else
      ENV="staging"
    fi

    cat <<ENDJSON
{
  "decision": "block",
  "reason": "You pushed to $BRANCH but haven't verified the deployment. Run: bash scripts/verify-deployment.sh $ENV --session $SESSION_ID\n\nVerification checks: CI status, deployment health, smoke test, schema drift.\n\nYou cannot end this session until deployment is verified."
}
ENDJSON
    exit 0
  fi
fi

# No pending push for this session, or verification done — allow stop
echo '{}'
