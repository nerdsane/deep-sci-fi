#!/bin/bash
# Post-push verification hook
# Detects git push AND gh pr merge in Bash tool output.
# Injects mandatory verification context for both staging and production.
#
# Hook type: PostToolUse (Bash matcher)
# Input: JSON on stdin with tool_name, tool_input, tool_output
# Output: JSON on stdout with additionalContext if deployment detected
#
# Session isolation: markers are scoped by project directory hash.
# $PPID is NOT stable across hook invocations in Claude Code, so we
# don't use it. Parallel sessions on the same project share markers.

set -euo pipefail

# Read the hook input from stdin
INPUT=$(cat)

# Extract the command that was run
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null || echo "")

# Scope markers by project directory hash (no session suffix — $PPID is unstable)
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")
PROJECT_HASH=$(printf '%s' "$PROJECT_ROOT" | cksum | cut -d' ' -f1)
MARKER_DIR="/tmp/claude-deepsci/$PROJECT_HASH"
mkdir -p "$MARKER_DIR"

# Clean up stale markers (older than 4 hours)
find "$MARKER_DIR" -name 'push-pending' -mmin +240 -delete 2>/dev/null || true
find "$MARKER_DIR" -name 'deploy-verified' -mmin +240 -delete 2>/dev/null || true
# Also clean up old session-scoped markers from before this fix
find "$MARKER_DIR" -name 'push-pending-*' -delete 2>/dev/null || true
find "$MARKER_DIR" -name 'deploy-verified-*' -delete 2>/dev/null || true

# ─────────────────────────────────────────────────────────────────────────────
# Case 1: Direct git push
# ─────────────────────────────────────────────────────────────────────────────
if echo "$COMMAND" | grep -qE '^\s*git\s+(-C\s+\S+\s+)?push\b'; then
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
  # Extract PR number from command (e.g., "gh pr merge 27 ..." → "27")
  PR_NUMBER=$(echo "$COMMAND" | grep -oE 'gh\s+pr\s+merge\s+([0-9]+)' | grep -oE '[0-9]+' || echo "")

  # Extract --repo / -R flag if present (e.g., "--repo arni-labs/deep-sci-fi")
  REPO_FLAG=""
  REPO_VALUE=$(echo "$COMMAND" | grep -oE '(-R|--repo)[[:space:]]+[^[:space:]]+' | sed 's/^-R[[:space:]]*//' | sed 's/^--repo[[:space:]]*//' || echo "")
  if [ -n "$REPO_VALUE" ]; then
    REPO_FLAG="--repo $REPO_VALUE"
  fi

  # Determine target branch and merge commit SHA via gh CLI
  TARGET_BRANCH=""
  MERGE_SHA=""
  if [ -n "$PR_NUMBER" ] && command -v gh &>/dev/null; then
    # Query the actual PR to get base branch and merge commit
    # shellcheck disable=SC2086
    PR_JSON=$(gh pr view "$PR_NUMBER" $REPO_FLAG --json baseRefName,mergeCommit 2>/dev/null || echo "{}")
    TARGET_BRANCH=$(echo "$PR_JSON" | jq -r '.baseRefName // ""' 2>/dev/null || echo "")
    MERGE_SHA=$(echo "$PR_JSON" | jq -r '.mergeCommit.oid // ""' 2>/dev/null || echo "")
  fi

  # Fallback: detect from command flags if gh query failed
  if [ -z "$TARGET_BRANCH" ]; then
    if echo "$COMMAND" | grep -qE '(--branch\s+staging|-B\s+staging)'; then
      TARGET_BRANCH="staging"
    else
      TARGET_BRANCH="main"
    fi
  fi

  # Map branch to environment
  if [ "$TARGET_BRANCH" = "main" ] || [ "$TARGET_BRANCH" = "master" ]; then
    ENV="production"
  else
    ENV="staging"
  fi

  echo "$TARGET_BRANCH" > "$MARKER_DIR/push-pending"
  rm -f "$MARKER_DIR/deploy-verified"

  # Build --sha flag if we have the merge commit
  SHA_FLAG=""
  SHA_NOTE=""
  if [ -n "$MERGE_SHA" ]; then
    SHA_FLAG=" --sha $MERGE_SHA"
    SHA_NOTE="\\n\\nMerge commit: ${MERGE_SHA:0:7}"
  fi

  # Build human-readable PR label
  if [ -n "$PR_NUMBER" ]; then
    PR_LABEL="PR #${PR_NUMBER}"
  else
    PR_LABEL="a PR"
  fi

  if [ "$ENV" = "staging" ]; then
    cat <<ENDJSON
{
  "additionalContext": "MANDATORY STAGING VERIFICATION: You just merged ${PR_LABEL} to ${TARGET_BRANCH}.${SHA_NOTE}\n\nYou MUST now verify the staging deployment:\n\nRun: bash scripts/verify-deployment.sh staging${SHA_FLAG}\n\nThis script verifies:\n1. CI/Deploy workflow completes\n2. Backend is healthy\n3. Frontend is healthy\n4. All 9 API endpoints respond\n5. No schema drift\n6. No 500 errors in Logfire (last 30 min)\n\nYou CANNOT end this session until verification passes."
}
ENDJSON
  else
    cat <<ENDJSON
{
  "additionalContext": "MANDATORY PRODUCTION VERIFICATION: You just merged ${PR_LABEL} to ${TARGET_BRANCH}. This deploys to PRODUCTION.${SHA_NOTE}\n\nYou MUST now verify the production deployment:\n\nRun: bash scripts/verify-deployment.sh production${SHA_FLAG}\n\nThis script verifies:\n1. CI/Deploy workflow completes\n2. Backend (api.deep-sci-fi.world) is healthy\n3. Frontend (deep-sci-fi.world) is healthy\n4. All 9 API endpoints respond\n5. No schema drift\n6. No 500 errors in Logfire (last 30 min)\n\nPRODUCTION IS LIVE. You CANNOT end this session until verification passes.\n\nIf verification fails, you must fix the issue immediately."
}
ENDJSON
  fi

# ─────────────────────────────────────────────────────────────────────────────
# Case 3: Not a deployment action
# ─────────────────────────────────────────────────────────────────────────────
else
  echo '{}'
fi
