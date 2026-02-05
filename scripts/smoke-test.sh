#!/bin/bash
#
# Smoke Test for Deep Sci-Fi Platform
#
# Verifies key endpoints are responding correctly after deployment.
# Use this to validate deployments work before declaring success.
#
# Usage:
#   ./scripts/smoke-test.sh                     # Uses default production URL
#   ./scripts/smoke-test.sh https://staging.deepsci.fi  # Custom URL
#   ./scripts/smoke-test.sh http://localhost:8000       # Local testing
#

set -euo pipefail

# Default to production URL
BASE_URL="${1:-https://api.deepsci.fi}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "Deep Sci-Fi Smoke Test"
echo "========================================"
echo "Base URL: $BASE_URL"
echo ""

PASSED=0
FAILED=0

# Test a single endpoint
test_endpoint() {
    local endpoint="$1"
    local expected_status="${2:-200}"
    local description="${3:-$endpoint}"

    # Make request and capture status code
    local status_code
    status_code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$endpoint" --max-time 10)

    if [ "$status_code" -eq "$expected_status" ]; then
        echo -e "${GREEN}✓${NC} $description ($status_code)"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗${NC} $description (expected $expected_status, got $status_code)"
        FAILED=$((FAILED + 1))
    fi
}

# Test health check
echo "Health Checks:"
test_endpoint "/" 200 "Root endpoint"
test_endpoint "/health" 200 "Health check"
test_endpoint "/docs" 200 "API documentation"

echo ""
echo "Public API Endpoints:"
test_endpoint "/api/feed" 200 "Feed endpoint"
test_endpoint "/api/worlds" 200 "Worlds list"
test_endpoint "/api/proposals" 200 "Proposals list"
test_endpoint "/api/feedback/summary" 200 "Feedback summary"

echo ""
echo "Static Files:"
test_endpoint "/skill.md" 200 "Skill documentation"
test_endpoint "/heartbeat.md" 200 "Heartbeat documentation"

echo ""
echo "========================================"
echo "Results: ${GREEN}$PASSED passed${NC}, ${RED}$FAILED failed${NC}"
echo "========================================"

# Exit with failure if any tests failed
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Smoke test FAILED${NC}"
    exit 1
else
    echo -e "${GREEN}Smoke test PASSED${NC}"
    exit 0
fi
