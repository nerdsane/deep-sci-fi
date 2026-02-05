#!/bin/bash
#
# Verify Deployment for Deep Sci-Fi Platform
#
# Polls GitHub Actions until the deploy workflow completes,
# then runs the smoke test against the target environment.
#
# Usage:
#   ./scripts/verify-deployment.sh              # Verify staging (default)
#   ./scripts/verify-deployment.sh production   # Verify production
#   ./scripts/verify-deployment.sh local        # Verify local (skip CI check)
#
# Exit codes:
#   0 = all checks passed
#   1 = one or more checks failed

set -euo pipefail

ENVIRONMENT="${1:-staging}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

case "$ENVIRONMENT" in
  staging)
    BASE_URL="https://api.deep-sci-fi.world"
    BRANCH="staging"
    ;;
  production)
    BASE_URL="https://api.deep-sci-fi.world"
    BRANCH="main"
    ;;
  local)
    BASE_URL="http://localhost:8000"
    BRANCH=""
    ;;
  *)
    echo -e "${RED}Unknown environment: $ENVIRONMENT${NC}"
    echo "Usage: $0 [staging|production|local]"
    exit 1
    ;;
esac

echo -e "${CYAN}======================================${NC}"
echo -e "${CYAN}  Verify Deployment: $ENVIRONMENT${NC}"
echo -e "${CYAN}======================================${NC}"
echo ""

FAILED=0

# ─────────────────────────────────────────────
# Step 1: Wait for CI / Deploy workflow
# ─────────────────────────────────────────────
if [ -n "$BRANCH" ]; then
  echo -e "${YELLOW}Step 1: Checking GitHub Actions...${NC}"

  # Check if gh CLI is available
  if ! command -v gh &> /dev/null; then
    echo -e "${RED}  gh CLI not installed. Cannot check CI status.${NC}"
    echo "  Install: https://cli.github.com/"
    FAILED=1
  else
    MAX_WAIT=900  # 15 minutes max (CI + deploy can be slow)
    INTERVAL=15
    ELAPSED=0

    while [ $ELAPSED -lt $MAX_WAIT ]; do
      # Get the most recent workflow run on this branch
      STATUS=$(gh run list --branch "$BRANCH" --limit 1 --json status,conclusion --jq '.[0]' 2>/dev/null || echo '{}')
      RUN_STATUS=$(echo "$STATUS" | jq -r '.status // "unknown"')
      RUN_CONCLUSION=$(echo "$STATUS" | jq -r '.conclusion // "unknown"')

      if [ "$RUN_STATUS" = "completed" ]; then
        if [ "$RUN_CONCLUSION" = "success" ]; then
          echo -e "${GREEN}  CI passed (${RUN_CONCLUSION})${NC}"
          break
        else
          echo -e "${RED}  CI failed (${RUN_CONCLUSION})${NC}"
          FAILED=1
          break
        fi
      elif [ "$RUN_STATUS" = "in_progress" ] || [ "$RUN_STATUS" = "queued" ]; then
        echo -e "  Workflow ${RUN_STATUS}... waiting ${INTERVAL}s (${ELAPSED}/${MAX_WAIT}s)"
        sleep $INTERVAL
        ELAPSED=$((ELAPSED + INTERVAL))
      else
        echo -e "${YELLOW}  No recent workflow found for branch $BRANCH${NC}"
        break
      fi
    done

    if [ $ELAPSED -ge $MAX_WAIT ]; then
      echo -e "${RED}  Timed out waiting for CI (${MAX_WAIT}s)${NC}"
      FAILED=1
    fi
  fi
else
  echo -e "${YELLOW}Step 1: Skipped (local environment)${NC}"
fi

echo ""

# ─────────────────────────────────────────────
# Step 2: Wait for deployment to be ready
# ─────────────────────────────────────────────
echo -e "${YELLOW}Step 2: Waiting for deployment to be ready...${NC}"

MAX_HEALTH_WAIT=300  # 5 minutes for Railway cold starts
HEALTH_INTERVAL=10
HEALTH_ELAPSED=0
HEALTHY=false

while [ $HEALTH_ELAPSED -lt $MAX_HEALTH_WAIT ]; do
  HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health" --max-time 5 2>/dev/null || echo "000")

  if [ "$HEALTH_STATUS" = "200" ]; then
    HEALTHY=true
    echo -e "${GREEN}  Deployment is healthy (HTTP $HEALTH_STATUS)${NC}"
    break
  else
    echo -e "  Not ready yet (HTTP $HEALTH_STATUS)... waiting ${HEALTH_INTERVAL}s (${HEALTH_ELAPSED}/${MAX_HEALTH_WAIT}s)"
    sleep $HEALTH_INTERVAL
    HEALTH_ELAPSED=$((HEALTH_ELAPSED + HEALTH_INTERVAL))
  fi
done

if [ "$HEALTHY" = false ]; then
  echo -e "${RED}  Deployment not healthy after ${MAX_HEALTH_WAIT}s${NC}"
  FAILED=1
fi

echo ""

# ─────────────────────────────────────────────
# Step 3: Run smoke test
# ─────────────────────────────────────────────
echo -e "${YELLOW}Step 3: Running smoke test...${NC}"

if [ -f "$SCRIPT_DIR/smoke-test.sh" ]; then
  if bash "$SCRIPT_DIR/smoke-test.sh" "$BASE_URL"; then
    echo -e "${GREEN}  Smoke test passed${NC}"
  else
    echo -e "${RED}  Smoke test failed${NC}"
    FAILED=1
  fi
else
  echo -e "${RED}  smoke-test.sh not found${NC}"
  FAILED=1
fi

echo ""

# ─────────────────────────────────────────────
# Step 4: Check schema drift
# ─────────────────────────────────────────────
echo -e "${YELLOW}Step 4: Checking schema health...${NC}"

HEALTH_BODY=$(curl -s "$BASE_URL/health" --max-time 5 2>/dev/null || echo '{}')
SCHEMA_STATUS=$(echo "$HEALTH_BODY" | jq -r '.status // "unknown"')

if [ "$SCHEMA_STATUS" = "healthy" ]; then
  echo -e "${GREEN}  Schema is current${NC}"
elif [ "$SCHEMA_STATUS" = "degraded" ]; then
  echo -e "${RED}  Schema drift detected!${NC}"
  echo "$HEALTH_BODY" | jq '.schema // empty'
  FAILED=1
else
  echo -e "${YELLOW}  Could not determine schema status${NC}"
fi

echo ""

# ─────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────
echo -e "${CYAN}======================================${NC}"
if [ $FAILED -gt 0 ]; then
  echo -e "${RED}  VERIFICATION FAILED${NC}"
  echo -e "${RED}  Fix issues before marking work complete.${NC}"
  echo -e "${CYAN}======================================${NC}"
  exit 1
else
  echo -e "${GREEN}  ALL CHECKS PASSED${NC}"
  echo -e "${GREEN}  Deployment verified for $ENVIRONMENT.${NC}"
  echo -e "${CYAN}======================================${NC}"

  # Signal to Stop hook that verification passed
  MARKER_DIR="/tmp/claude-deepsci"
  mkdir -p "$MARKER_DIR"
  touch "$MARKER_DIR/deploy-verified"

  exit 0
fi
