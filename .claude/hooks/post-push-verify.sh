#!/bin/bash
# Post-push verification hook
# Detects "git push" in Bash tool output and injects mandatory verification context.
#
# Hook type: PostToolUse (Bash matcher)
# Input: JSON on stdin with tool_name, tool_input, tool_output
# Output: JSON on stdout with additionalContext if git push detected

set -euo pipefail

# Read the hook input from stdin
INPUT=$(cat)

# Extract the command that was run
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null || echo "")

# Check if this was a git push command (not just any git command)
if echo "$COMMAND" | grep -qE '^\s*git\s+push\b'; then
  # Determine which branch was pushed
  BRANCH=$(echo "$COMMAND" | grep -oE '(staging|main|master)' | head -1)
  BRANCH=${BRANCH:-"unknown"}

  # Create marker file so the Stop hook knows a push happened
  MARKER_DIR="/tmp/claude-deepsci"
  mkdir -p "$MARKER_DIR"
  echo "$BRANCH" > "$MARKER_DIR/push-pending"
  rm -f "$MARKER_DIR/deploy-verified"

  # Determine environment from branch
  if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
    ENV="production"
  else
    ENV="staging"
  fi

  # Return additionalContext telling Claude to verify deployment
  cat <<ENDJSON
{
  "additionalContext": "MANDATORY POST-DEPLOY VERIFICATION: You just pushed to $BRANCH. You MUST now verify the deployment before doing anything else or ending the session.\n\nRun: bash scripts/verify-deployment.sh $ENV\n\nThis script will:\n1. Poll GitHub Actions until CI completes\n2. Wait for the deployment to be healthy\n3. Run the smoke test against $ENV\n4. Check for schema drift\n\nDo NOT skip this step. Do NOT mark work as complete until verification passes.\n\nIf Logfire MCP is available, also run: find_exceptions(30) to check for new errors after deploy."
}
ENDJSON
else
  # Not a git push — no additional context needed
  echo '{}'
fi
