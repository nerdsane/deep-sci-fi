#!/bin/bash
#
# Verify Deployment for Deep Sci-Fi Platform
#
# BLOCKING verification — session cannot end until ALL checks pass.
# Polls GitHub Actions, verifies both frontend and backend, checks Logfire.
#
# Usage:
#   ./scripts/verify-deployment.sh              # Verify staging (default)
#   ./scripts/verify-deployment.sh production   # Verify production
#   ./scripts/verify-deployment.sh local        # Verify local (skip CI/Logfire)
#
# Exit codes:
#   0 = all checks passed
#   1 = one or more checks failed (BLOCKS session end)

set -euo pipefail

ENVIRONMENT="${1:-staging}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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
    BACKEND_URL="https://api.deep-sci-fi.world"
    FRONTEND_URL="https://deep-sci-fi.world"  # Same as prod (Vercel preview would need specific URL)
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
  echo -e "${CYAN}[Step 1/6] Waiting for GitHub Actions CI...${NC}"

  if ! command -v gh &> /dev/null; then
    echo -e "${RED}  ERROR: gh CLI not installed${NC}"
    echo "  Install: https://cli.github.com/"
    FAILED=1
  else
    ELAPSED=0
    CI_PASSED=false

    while [ $ELAPSED -lt $MAX_CI_WAIT ]; do
      STATUS=$(gh run list --branch "$BRANCH" --workflow "Deploy" --limit 1 --json status,conclusion --jq '.[0]' 2>/dev/null || echo '{}')
      RUN_STATUS=$(echo "$STATUS" | jq -r '.status // "unknown"')
      RUN_CONCLUSION=$(echo "$STATUS" | jq -r '.conclusion // "unknown"')

      if [ "$RUN_STATUS" = "completed" ]; then
        if [ "$RUN_CONCLUSION" = "success" ]; then
          echo -e "${GREEN}  ✓ CI passed${NC}"
          CI_PASSED=true
          break
        else
          echo -e "${RED}  ✗ CI failed (${RUN_CONCLUSION})${NC}"
          echo -e "${RED}    Fix CI before proceeding. Check: gh run view${NC}"
          FAILED=1
          break
        fi
      elif [ "$RUN_STATUS" = "in_progress" ] || [ "$RUN_STATUS" = "queued" ]; then
        echo -e "  Workflow ${RUN_STATUS}... (${ELAPSED}s / ${MAX_CI_WAIT}s max)"
        sleep $POLL_INTERVAL
        ELAPSED=$((ELAPSED + POLL_INTERVAL))
      else
        echo -e "${YELLOW}  No workflow found for branch $BRANCH${NC}"
        echo -e "${YELLOW}  Continuing with other checks...${NC}"
        break
      fi
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
# Step 6: BLOCKING Logfire check — no 500 errors in last 30 minutes
# ─────────────────────────────────────────────────────────────────────────────
if [ -n "$BRANCH" ]; then
  echo -e "${CYAN}[Step 6/6] Checking Logfire for 500 errors (BLOCKING)...${NC}"

  # Check if logfire token exists
  LOGFIRE_TOKEN_FILE="$PROJECT_ROOT/.claude/logfire-token"
  if [ -f "$LOGFIRE_TOKEN_FILE" ]; then
    LOGFIRE_TOKEN=$(cat "$LOGFIRE_TOKEN_FILE" | head -1 | tr -d '[:space:]')

    if [ -n "$LOGFIRE_TOKEN" ] && [ "$LOGFIRE_TOKEN" != "YOUR_LOGFIRE_READ_TOKEN_HERE" ]; then
      # Query Logfire for 500 errors in last 30 minutes
      # Using the Logfire API directly since we can't call MCP from bash
      LOGFIRE_RESULT=$(curl -s --max-time 30 \
        -H "Authorization: Bearer $LOGFIRE_TOKEN" \
        -H "Content-Type: application/json" \
        -X POST "https://logfire-api.pydantic.dev/v1/query" \
        -d '{
          "sql": "SELECT COUNT(*) as error_count FROM records WHERE http_response_status_code >= 500",
          "min_timestamp": "'$(date -u -v-30M +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%SZ)'"
        }' 2>/dev/null || echo '{"error": "request failed"}')

      if echo "$LOGFIRE_RESULT" | grep -q '"error"'; then
        echo -e "${YELLOW}  ⚠ Could not query Logfire API${NC}"
        echo -e "${YELLOW}    You MUST manually check: Use mcp__logfire__arbitrary_query${NC}"
        echo -e "${YELLOW}    Query: SELECT * FROM records WHERE http_response_status_code >= 500 LIMIT 10${NC}"
        echo -e "${RED}  ✗ Logfire check inconclusive — MANUAL CHECK REQUIRED${NC}"
        FAILED=1
      else
        ERROR_COUNT=$(echo "$LOGFIRE_RESULT" | jq -r '.data[0].error_count // 0' 2>/dev/null || echo "0")

        if [ "$ERROR_COUNT" = "0" ]; then
          echo -e "${GREEN}  ✓ No 500 errors in last 30 minutes${NC}"
        else
          echo -e "${RED}  ✗ Found $ERROR_COUNT server errors (500+) in last 30 minutes${NC}"
          echo -e "${RED}    Investigate with: mcp__logfire__arbitrary_query${NC}"
          echo -e "${RED}    Query: SELECT exception_type, exception_message, http_route FROM records WHERE http_response_status_code >= 500 ORDER BY start_timestamp DESC LIMIT 10${NC}"
          FAILED=1
        fi
      fi
    else
      echo -e "${YELLOW}  ⚠ Logfire token not configured${NC}"
      echo -e "${RED}  ✗ Logfire check REQUIRED but token missing${NC}"
      echo -e "${RED}    Add token to: $LOGFIRE_TOKEN_FILE${NC}"
      FAILED=1
    fi
  else
    echo -e "${YELLOW}  ⚠ Logfire token file not found${NC}"
    echo -e "${RED}  ✗ Logfire check REQUIRED but not configured${NC}"
    echo -e "${RED}    Create: $LOGFIRE_TOKEN_FILE${NC}"
    FAILED=1
  fi
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
  echo -e "${GREEN}  ✓ ALL CHECKS PASSED${NC}"
  echo -e "${GREEN}  Deployment verified for $ENVIRONMENT.${NC}"
  echo -e "${CYAN}======================================${NC}"

  # Signal to Stop hook that verification passed
  MARKER_DIR="/tmp/claude-deepsci"
  mkdir -p "$MARKER_DIR"
  touch "$MARKER_DIR/deploy-verified"

  exit 0
fi
