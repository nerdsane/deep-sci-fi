#!/bin/bash
#
# Verify Deployment for Deep Sci-Fi Platform
#
# BLOCKING verification — session cannot end until ALL checks pass.
# Polls GitHub Actions, verifies both frontend and backend, checks Logfire.
#
# Usage:
#   ./scripts/verify-deployment.sh                  # Verify staging (default)
#   ./scripts/verify-deployment.sh production       # Verify production
#   ./scripts/verify-deployment.sh local            # Verify local (skip CI/Logfire)
#
# Note: --session flag is accepted but ignored (session scoping was removed
# because $PPID is not stable across Claude Code hook invocations).
#
# Exit codes:
#   0 = all checks passed
#   1 = one or more checks failed (BLOCKS session end)

set -euo pipefail

# Parse arguments
ENVIRONMENT="staging"
OVERRIDE_SHA=""
while [ $# -gt 0 ]; do
  case "$1" in
    --session) shift 2 ;;  # deprecated, ignored (session scoping removed)
    --sha)
      if [ $# -lt 2 ]; then
        echo "Error: --sha requires a value" >&2; exit 1
      fi
      OVERRIDE_SHA="$2"; shift 2
      ;;
    staging|production|local) ENVIRONMENT="$1"; shift ;;
    *) shift ;;
  esac
done
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Get GitHub repo from origin remote (not upstream)
# gh defaults to 'upstream' if it exists, but we want 'origin' for deployments
GITHUB_REPO=$(git -C "$PROJECT_ROOT" remote get-url origin 2>/dev/null | sed -E 's|.*github.com[:/]||; s|\.git$||' || echo "")

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Timeouts — generous to ensure we never escape without verification
MAX_CI_WAIT=1800      # 30 minutes for CI
MAX_HEALTH_WAIT=600   # 10 minutes for health checks
POLL_INTERVAL=15

case "$ENVIRONMENT" in
  staging)
    BACKEND_URL="https://api-staging.deep-sci-fi.world"
    FRONTEND_URL="https://staging.deep-sci-fi.world"
    BRANCH="staging"
    ;;
  production)
    BACKEND_URL="https://api.deep-sci-fi.world"
    FRONTEND_URL="https://deep-sci-fi.world"
    BRANCH="main"
    ;;
  local)
    BACKEND_URL="http://localhost:8000"
    FRONTEND_URL="http://localhost:3000"
    BRANCH=""
    ;;
  *)
    echo -e "${RED}Unknown environment: $ENVIRONMENT${NC}"
    echo "Usage: $0 [staging|production|local]"
    exit 1
    ;;
esac

echo -e "${CYAN}======================================${NC}"
echo -e "${CYAN}  BLOCKING Deployment Verification${NC}"
echo -e "${CYAN}  Environment: $ENVIRONMENT${NC}"
echo -e "${CYAN}======================================${NC}"
echo ""
echo -e "${YELLOW}This verification is MANDATORY.${NC}"
echo -e "${YELLOW}Session cannot end until all checks pass.${NC}"
echo ""

FAILED=0

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Wait for CI / Deploy workflow to complete
# ─────────────────────────────────────────────────────────────────────────────
if [ -n "$BRANCH" ]; then
  echo -e "${CYAN}[Step 1/6] Waiting for GitHub Actions CI (ALL workflows)...${NC}"

  if ! command -v gh &> /dev/null; then
    echo -e "${RED}  ERROR: gh CLI not installed${NC}"
    echo "  Install: https://cli.github.com/"
    FAILED=1
  else
    ELAPSED=0
    CI_PASSED=false

    # Get the expected commit SHA for CI matching.
    # Priority: --sha flag > remote branch tip > local HEAD
    if [ -n "$OVERRIDE_SHA" ]; then
      FULL_EXPECTED_SHA="$OVERRIDE_SHA"
    else
      CURRENT_BRANCH=$(git -C "$PROJECT_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
      if [ "$CURRENT_BRANCH" = "$BRANCH" ]; then
        # On the target branch — local HEAD is correct
        FULL_EXPECTED_SHA=$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || echo "")
      else
        # Different branch (e.g., verifying main from staging after PR merge)
        # Fetch the latest commit from the remote
        FULL_EXPECTED_SHA=$(git -C "$PROJECT_ROOT" ls-remote origin "$BRANCH" 2>/dev/null | head -1 | cut -f1 || echo "")
        if [ -z "$FULL_EXPECTED_SHA" ]; then
          # Fallback: fetch and use origin/<branch>
          git -C "$PROJECT_ROOT" fetch origin "$BRANCH" --quiet 2>/dev/null || true
          FULL_EXPECTED_SHA=$(git -C "$PROJECT_ROOT" rev-parse "origin/$BRANCH" 2>/dev/null || echo "")
        fi
      fi
    fi
    EXPECTED_SHA="${FULL_EXPECTED_SHA:0:7}"
    if [ -n "$EXPECTED_SHA" ]; then
      echo -e "  Expected commit: ${EXPECTED_SHA}"
    fi

    while [ $ELAPSED -lt $MAX_CI_WAIT ]; do
      # Fetch recent runs across push/workflow_dispatch workflows on this branch
      # Skip pull_request-triggered workflows (e.g. PR Review) — they run on PR merge commits,
      # not the branch HEAD, and would block verification with stale failures.
      ALL_RUNS=$(gh run list --repo "$GITHUB_REPO" --branch "$BRANCH" --limit 20 --json workflowName,status,conclusion,databaseId,headSha,event 2>/dev/null || echo '[]')
      ALL_RUNS=$(echo "$ALL_RUNS" | jq '[.[] | select(.event != "pull_request")]')

      # Filter to only runs matching the expected commit SHA (if we have it)
      if [ -n "$FULL_EXPECTED_SHA" ]; then
        MATCHING_RUNS=$(echo "$ALL_RUNS" | jq --arg sha "$FULL_EXPECTED_SHA" '[.[] | select(.headSha == $sha)]')
        MATCHING_COUNT=$(echo "$MATCHING_RUNS" | jq 'length')

        if [ "$MATCHING_COUNT" -eq 0 ]; then
          echo -e "  No CI runs yet for commit ${EXPECTED_SHA}... waiting (${ELAPSED}s / ${MAX_CI_WAIT}s)"
          sleep $POLL_INTERVAL
          ELAPSED=$((ELAPSED + POLL_INTERVAL))
          continue
        fi

        # Use only runs matching our commit
        ALL_RUNS="$MATCHING_RUNS"
      fi

      if [ "$ALL_RUNS" = "[]" ] || [ -z "$ALL_RUNS" ]; then
        echo -e "${YELLOW}  No workflow runs found for branch $BRANCH${NC}"
        echo -e "${YELLOW}  Continuing with other checks...${NC}"
        break
      fi

      # Get the most recent run per workflow (jq: group by workflow, take first of each)
      LATEST_PER_WORKFLOW=$(echo "$ALL_RUNS" | jq '[group_by(.workflowName)[] | sort_by(.databaseId) | reverse | .[0]]')
      TOTAL_WORKFLOWS=$(echo "$LATEST_PER_WORKFLOW" | jq 'length')

      # Check if any are still running
      PENDING_COUNT=$(echo "$LATEST_PER_WORKFLOW" | jq '[.[] | select(.status != "completed")] | length')

      if [ "$PENDING_COUNT" -gt 0 ]; then
        PENDING_NAMES=$(echo "$LATEST_PER_WORKFLOW" | jq -r '[.[] | select(.status != "completed") | "\(.workflowName) (\(.status))"] | join(", ")')
        echo -e "  Waiting on $PENDING_COUNT/$TOTAL_WORKFLOWS workflows: $PENDING_NAMES (${ELAPSED}s / ${MAX_CI_WAIT}s max)"
        sleep $POLL_INTERVAL
        ELAPSED=$((ELAPSED + POLL_INTERVAL))
        continue
      fi

      # All completed — check for failures
      FAILED_WORKFLOWS=$(echo "$LATEST_PER_WORKFLOW" | jq -r '[.[] | select(.conclusion != "success" and .conclusion != "skipped")] | length')

      if [ "$FAILED_WORKFLOWS" -gt 0 ]; then
        FAILED_NAMES=$(echo "$LATEST_PER_WORKFLOW" | jq -r '[.[] | select(.conclusion != "success" and .conclusion != "skipped") | "\(.workflowName) (\(.conclusion)) @ \(.headSha[0:7])"] | join(", ")')
        echo -e "${RED}  ✗ $FAILED_WORKFLOWS/$TOTAL_WORKFLOWS workflows failed: $FAILED_NAMES${NC}"
        echo -e "${RED}    Fix ALL workflows before proceeding. Check: gh run list --branch $BRANCH${NC}"
        FAILED=1
      else
        echo -e "${GREEN}  ✓ All $TOTAL_WORKFLOWS workflows passed${NC}"
        # List each workflow for visibility
        echo "$LATEST_PER_WORKFLOW" | jq -r '.[] | "    ✓ \(.workflowName): \(.conclusion) @ \(.headSha[0:7])"' | while read -r line; do
          echo -e "${GREEN}$line${NC}"
        done
        CI_PASSED=true
      fi
      break
    done

    if [ $ELAPSED -ge $MAX_CI_WAIT ] && [ "$CI_PASSED" = false ]; then
      echo -e "${RED}  ✗ Timed out waiting for CI (${MAX_CI_WAIT}s)${NC}"
      FAILED=1
    fi
  fi
else
  echo -e "${YELLOW}[Step 1/6] Skipped CI check (local environment)${NC}"
fi

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Verify Backend is healthy
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}[Step 2/6] Verifying Backend (${BACKEND_URL})...${NC}"

ELAPSED=0
BACKEND_HEALTHY=false

while [ $ELAPSED -lt $MAX_HEALTH_WAIT ]; do
  HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health" --max-time 10 2>/dev/null || echo "000")

  if [ "$HEALTH_STATUS" = "200" ]; then
    BACKEND_HEALTHY=true
    echo -e "${GREEN}  ✓ Backend healthy (HTTP 200)${NC}"
    break
  else
    echo -e "  Backend not ready (HTTP $HEALTH_STATUS)... (${ELAPSED}s / ${MAX_HEALTH_WAIT}s)"
    sleep $POLL_INTERVAL
    ELAPSED=$((ELAPSED + POLL_INTERVAL))
  fi
done

if [ "$BACKEND_HEALTHY" = false ]; then
  echo -e "${RED}  ✗ Backend not healthy after ${MAX_HEALTH_WAIT}s${NC}"
  FAILED=1
fi

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Verify Frontend is healthy
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}[Step 3/6] Verifying Frontend (${FRONTEND_URL})...${NC}"

ELAPSED=0
FRONTEND_HEALTHY=false

while [ $ELAPSED -lt $MAX_HEALTH_WAIT ]; do
  # Check that frontend returns 200 and contains expected content
  FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL" --max-time 10 2>/dev/null || echo "000")

  if [ "$FRONTEND_STATUS" = "200" ]; then
    # Verify it's actually our app (not an error page)
    FRONTEND_CONTENT=$(curl -s "$FRONTEND_URL" --max-time 10 2>/dev/null || echo "")
    if echo "$FRONTEND_CONTENT" | grep -q "Deep Sci-Fi\|deep-sci-fi\|__NEXT"; then
      FRONTEND_HEALTHY=true
      echo -e "${GREEN}  ✓ Frontend healthy (HTTP 200, content verified)${NC}"
      break
    else
      echo -e "  Frontend returned 200 but content not recognized... (${ELAPSED}s)"
    fi
  else
    echo -e "  Frontend not ready (HTTP $FRONTEND_STATUS)... (${ELAPSED}s / ${MAX_HEALTH_WAIT}s)"
  fi

  sleep $POLL_INTERVAL
  ELAPSED=$((ELAPSED + POLL_INTERVAL))
done

if [ "$FRONTEND_HEALTHY" = false ]; then
  echo -e "${RED}  ✗ Frontend not healthy after ${MAX_HEALTH_WAIT}s${NC}"
  FAILED=1
fi

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Run API smoke test
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}[Step 4/6] Running API smoke test...${NC}"

if [ -f "$SCRIPT_DIR/smoke-test.sh" ]; then
  if bash "$SCRIPT_DIR/smoke-test.sh" "$BACKEND_URL"; then
    echo -e "${GREEN}  ✓ Smoke test passed${NC}"
  else
    echo -e "${RED}  ✗ Smoke test failed${NC}"
    FAILED=1
  fi
else
  echo -e "${RED}  ✗ smoke-test.sh not found${NC}"
  FAILED=1
fi

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Check schema drift
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}[Step 5/6] Checking schema health...${NC}"

HEALTH_BODY=$(curl -s "$BACKEND_URL/health" --max-time 10 2>/dev/null || echo '{}')
SCHEMA_STATUS=$(echo "$HEALTH_BODY" | jq -r '.status // "unknown"')

if [ "$SCHEMA_STATUS" = "healthy" ]; then
  echo -e "${GREEN}  ✓ Schema is current${NC}"
elif [ "$SCHEMA_STATUS" = "degraded" ]; then
  echo -e "${RED}  ✗ Schema drift detected!${NC}"
  echo "$HEALTH_BODY" | jq '.schema // empty'
  FAILED=1
else
  echo -e "${YELLOW}  ⚠ Could not determine schema status (${SCHEMA_STATUS})${NC}"
fi

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Step 6: Logfire 500 error check — delegated to Claude via MCP
# ─────────────────────────────────────────────────────────────────────────────
if [ -n "$BRANCH" ]; then
  echo -e "${CYAN}[Step 6/6] Logfire 500 error check via MCP...${NC}"
  echo ""
  echo -e "${YELLOW}  This step is performed by Claude using the Logfire MCP integration.${NC}"
  echo -e "${YELLOW}  Claude: use mcp__logfire__find_exceptions_in_file to check for 500 errors in the last 30 minutes.${NC}"
  echo -e "${YELLOW}  If no MCP available, use mcp__logfire__arbitrary_query with:${NC}"
  echo -e "${YELLOW}    SELECT http_status_code, http_route, message FROM records WHERE http_response_status_code >= 500 ORDER BY start_timestamp DESC LIMIT 10${NC}"
  echo ""
  echo -e "${YELLOW}  If no 500 errors found, mark verification complete:${NC}"

  # Compute marker path for Claude to write after MCP check passes
  PROJECT_HASH=$(printf '%s' "$PROJECT_ROOT" | cksum | cut -d' ' -f1)
  MARKER_DIR="/tmp/claude-deepsci/$PROJECT_HASH"
  mkdir -p "$MARKER_DIR"
  MARKER_PATH="$MARKER_DIR/deploy-verified"
  echo -e "${YELLOW}    touch $MARKER_PATH${NC}"
  echo ""
  echo -e "${CYAN}  Steps 1-5 passed. Waiting for Logfire MCP check to complete verification.${NC}"
else
  echo -e "${YELLOW}[Step 6/6] Skipped Logfire check (local environment)${NC}"
fi

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${CYAN}======================================${NC}"
if [ $FAILED -gt 0 ]; then
  echo -e "${RED}  ✗ VERIFICATION FAILED${NC}"
  echo -e "${RED}  You CANNOT end this session.${NC}"
  echo -e "${RED}  Fix ALL issues and run this script again.${NC}"
  echo -e "${CYAN}======================================${NC}"
  exit 1
else
  if [ -n "$BRANCH" ]; then
    echo -e "${GREEN}  ✓ Steps 1-5 PASSED${NC}"
    echo -e "${YELLOW}  ⏳ Step 6 pending: query Logfire via MCP, then touch the marker above.${NC}"
  else
    # Local environment — no Logfire check needed, write marker directly
    echo -e "${GREEN}  ✓ ALL CHECKS PASSED${NC}"
    echo -e "${GREEN}  Deployment verified for $ENVIRONMENT.${NC}"
    PROJECT_HASH=$(printf '%s' "$PROJECT_ROOT" | cksum | cut -d' ' -f1)
    MARKER_DIR="/tmp/claude-deepsci/$PROJECT_HASH"
    mkdir -p "$MARKER_DIR"
    touch "$MARKER_DIR/deploy-verified"
  fi
  echo -e "${CYAN}======================================${NC}"

  exit 0
fi
