#!/bin/bash
#
# Local Agent Tester
#
# A simple script that exercises the DSF API and reports issues via feedback.
# Run this alongside Claude Code to create a local feedback loop.
#
# Usage:
#   1. Start backend: cd platform/backend && uvicorn main:app --reload
#   2. Register a tester: ./scripts/local-tester.sh register
#   3. Run tests: ./scripts/local-tester.sh run
#
# The API key is stored in .local-tester-key
#

set -euo pipefail

BASE_URL="${DSF_URL:-http://localhost:8000}"
KEY_FILE=".local-tester-key"
INTERVAL="${TEST_INTERVAL:-15}"  # seconds between test runs

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${CYAN}[$(date +%H:%M:%S)]${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; }
warn() { echo -e "${YELLOW}!${NC} $1"; }

# Get API key
get_key() {
    if [[ -f "$KEY_FILE" ]]; then
        cat "$KEY_FILE"
    else
        echo ""
    fi
}

# Register a tester agent
register() {
    log "Registering local tester agent..."

    RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/agent" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "Local Tester Agent",
            "username": "local-tester",
            "description": "Automated local testing agent for development"
        }')

    API_KEY=$(echo "$RESPONSE" | jq -r '.api_key.key // empty')

    if [[ -n "$API_KEY" ]]; then
        echo "$API_KEY" > "$KEY_FILE"
        success "Registered! Key saved to $KEY_FILE"
        echo "  Username: $(echo "$RESPONSE" | jq -r '.agent.username')"
    else
        fail "Registration failed"
        echo "$RESPONSE" | jq .
        exit 1
    fi
}

# Submit feedback
report_feedback() {
    local category="$1"
    local priority="$2"
    local title="$3"
    local description="$4"
    local endpoint="${5:-}"
    local error_code="${6:-}"

    API_KEY=$(get_key)
    if [[ -z "$API_KEY" ]]; then
        fail "No API key. Run: $0 register"
        return 1
    fi

    PAYLOAD=$(jq -n \
        --arg cat "$category" \
        --arg pri "$priority" \
        --arg title "$title" \
        --arg desc "$description" \
        --arg ep "$endpoint" \
        --arg ec "$error_code" \
        '{
            category: $cat,
            priority: $pri,
            title: $title,
            description: $desc,
            endpoint: (if $ep != "" then $ep else null end),
            error_code: (if $ec != "" then ($ec | tonumber) else null end)
        }')

    RESPONSE=$(curl -s -X POST "$BASE_URL/api/feedback" \
        -H "X-API-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD")

    if echo "$RESPONSE" | jq -e '.success' > /dev/null 2>&1; then
        warn "Reported: $title"
    else
        fail "Failed to report feedback"
    fi
}

# Test: Check error responses have how_to_fix
test_error_messages() {
    log "Testing: Error message quality..."
    API_KEY=$(get_key)

    # Test 1: Missing auth
    RESPONSE=$(curl -s -X POST "$BASE_URL/api/proposals" \
        -H "Content-Type: application/json" \
        -d '{"premise": "test"}')

    if ! echo "$RESPONSE" | jq -e '.detail.how_to_fix' > /dev/null 2>&1; then
        report_feedback "error_message" "medium" \
            "401 response missing how_to_fix field" \
            "When calling POST /api/proposals without auth, the error response lacks actionable guidance (how_to_fix field)." \
            "/api/proposals" "401"
    else
        success "401 error has how_to_fix"
    fi

    # Test 2: Invalid UUID
    RESPONSE=$(curl -s "$BASE_URL/api/worlds/not-a-uuid")

    if ! echo "$RESPONSE" | jq -e '.detail.how_to_fix' > /dev/null 2>&1; then
        report_feedback "error_message" "low" \
            "Invalid UUID error missing how_to_fix" \
            "When calling GET /api/worlds/not-a-uuid, the error response lacks actionable guidance." \
            "/api/worlds/{id}" "400"
    else
        success "Invalid UUID error has how_to_fix"
    fi
}

# Test: Proposal creation flow
test_proposal_flow() {
    log "Testing: Proposal creation flow..."
    API_KEY=$(get_key)

    # Test: Missing required fields
    RESPONSE=$(curl -s -X POST "$BASE_URL/api/proposals" \
        -H "X-API-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"premise": "Test world premise"}')

    STATUS=$(echo "$RESPONSE" | jq -r '.detail.error // .error // "unknown"')

    if [[ "$STATUS" == "Validation Error" ]]; then
        success "Validation error returned for incomplete proposal"
    else
        # Check if it actually lists what's missing
        if ! echo "$RESPONSE" | jq -e '.details[]' > /dev/null 2>&1; then
            report_feedback "api_usability" "medium" \
                "Proposal validation error doesn't list missing fields" \
                "When submitting an incomplete proposal, the error doesn't clearly list which fields are missing. Should enumerate: year_setting, causal_chain, scientific_basis." \
                "/api/proposals" "422"
        else
            success "Validation error lists missing fields"
        fi
    fi
}

# Test: Feedback system itself
test_feedback_system() {
    log "Testing: Feedback system..."
    API_KEY=$(get_key)

    # Test: Summary endpoint works
    RESPONSE=$(curl -s "$BASE_URL/api/feedback/summary")

    if echo "$RESPONSE" | jq -e '.stats' > /dev/null 2>&1; then
        success "Feedback summary endpoint works"
        OPEN=$(echo "$RESPONSE" | jq '.stats.open')
        log "  Open issues: $OPEN"
    else
        fail "Feedback summary endpoint broken"
        report_feedback "api_bug" "critical" \
            "Feedback summary endpoint returning invalid response" \
            "GET /api/feedback/summary is not returning expected JSON structure with stats field." \
            "/api/feedback/summary" "200"
    fi
}

# Test: Worlds endpoint
test_worlds() {
    log "Testing: Worlds endpoint..."

    RESPONSE=$(curl -s "$BASE_URL/api/worlds")

    if echo "$RESPONSE" | jq -e '.worlds' > /dev/null 2>&1; then
        COUNT=$(echo "$RESPONSE" | jq '.worlds | length')
        success "Worlds endpoint works ($COUNT worlds)"
    else
        report_feedback "api_bug" "high" \
            "Worlds endpoint not returning expected structure" \
            "GET /api/worlds should return {worlds: [...]} but got different structure." \
            "/api/worlds" "200"
    fi
}

# Run all tests once
run_tests() {
    echo ""
    echo "========================================"
    echo " Local Tester - $(date)"
    echo " Target: $BASE_URL"
    echo "========================================"
    echo ""

    test_feedback_system
    test_error_messages
    test_proposal_flow
    test_worlds

    echo ""
    log "Test run complete"
}

# Continuous test loop
run_loop() {
    log "Starting continuous test loop (interval: ${INTERVAL}s)"
    log "Press Ctrl+C to stop"
    echo ""

    while true; do
        run_tests
        echo ""
        log "Sleeping ${INTERVAL}s..."
        sleep "$INTERVAL"
    done
}

# Show current feedback
show_feedback() {
    log "Current feedback summary:"
    echo ""
    curl -s "$BASE_URL/api/feedback/summary" | jq '{
        critical: .critical_issues | length,
        high_upvotes: .high_upvotes | length,
        recent: .recent_issues | length,
        stats: .stats
    }'

    echo ""
    log "Recent issues:"
    curl -s "$BASE_URL/api/feedback/summary" | jq -r '.recent_issues[] | "  [\(.priority)] \(.title)"'
}

# Main
case "${1:-}" in
    register)
        register
        ;;
    run)
        API_KEY=$(get_key)
        if [[ -z "$API_KEY" ]]; then
            fail "No API key. Run: $0 register"
            exit 1
        fi
        run_tests
        ;;
    loop)
        API_KEY=$(get_key)
        if [[ -z "$API_KEY" ]]; then
            fail "No API key. Run: $0 register"
            exit 1
        fi
        run_loop
        ;;
    feedback)
        show_feedback
        ;;
    *)
        echo "Usage: $0 {register|run|loop|feedback}"
        echo ""
        echo "Commands:"
        echo "  register  - Register a tester agent (do this first)"
        echo "  run       - Run tests once"
        echo "  loop      - Run tests continuously"
        echo "  feedback  - Show current feedback summary"
        echo ""
        echo "Environment:"
        echo "  DSF_URL        - Base URL (default: http://localhost:8000)"
        echo "  TEST_INTERVAL  - Seconds between loop runs (default: 15)"
        ;;
esac
