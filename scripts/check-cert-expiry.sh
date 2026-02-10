#!/bin/bash
#
# Check SSL certificate expiry
# Warns if any bundled certificates expire within the specified threshold
#
# Usage:
#   ./scripts/check-cert-expiry.sh [days]
#
# Exit codes:
#   0 = all certificates valid
#   1 = certificate expiring soon or already expired

set -euo pipefail

DAYS_THRESHOLD="${1:-90}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CERTS_DIR="$PROJECT_ROOT/platform/backend/certs"

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

FAILED=0

echo "Checking certificate expiry (threshold: ${DAYS_THRESHOLD} days)"
echo ""

for cert_file in "$CERTS_DIR"/*.crt; do
    [ -e "$cert_file" ] || continue

    filename=$(basename "$cert_file")

    # Get expiry date
    expiry_date=$(openssl x509 -in "$cert_file" -noout -enddate 2>/dev/null | cut -d= -f2)
    if [ -z "$expiry_date" ]; then
        echo -e "${RED}[ERROR]${NC} $filename: Could not read certificate"
        FAILED=1
        continue
    fi

    # Convert to epoch for comparison (works on both macOS and Linux)
    if date -j -f "%b %d %H:%M:%S %Y %Z" "$expiry_date" +%s >/dev/null 2>&1; then
        # macOS
        expiry_epoch=$(date -j -f "%b %d %H:%M:%S %Y %Z" "$expiry_date" +%s)
    else
        # Linux (GNU date)
        expiry_epoch=$(date -d "$expiry_date" +%s)
    fi
    now_epoch=$(date +%s)
    threshold_epoch=$((now_epoch + DAYS_THRESHOLD * 86400))

    # Calculate days until expiry
    days_until_expiry=$(( (expiry_epoch - now_epoch) / 86400 ))

    # Get subject for display
    subject=$(openssl x509 -in "$cert_file" -noout -subject 2>/dev/null | sed 's/subject=//')

    if [ "$expiry_epoch" -lt "$now_epoch" ]; then
        echo -e "${RED}[EXPIRED]${NC} $filename"
        echo "  Subject: $subject"
        echo "  Expired: $expiry_date"
        FAILED=1
    elif [ "$expiry_epoch" -lt "$threshold_epoch" ]; then
        echo -e "${YELLOW}[WARNING]${NC} $filename"
        echo "  Subject: $subject"
        echo "  Expires: $expiry_date ($days_until_expiry days remaining)"
        echo "  Action: Download new certificate from Supabase Dashboard"
        FAILED=1
    else
        echo -e "${GREEN}[OK]${NC} $filename"
        echo "  Subject: $subject"
        echo "  Expires: $expiry_date ($days_until_expiry days remaining)"
    fi
    echo ""
done

if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Certificate check failed!${NC}"
    echo "To update Supabase CA certificate:"
    echo "  1. Download from Supabase Dashboard > Database Settings > SSL Configuration"
    echo "  2. Or run: ruby scripts/extract-supabase-cert.rb"
    exit 1
else
    echo -e "${GREEN}All certificates valid.${NC}"
    exit 0
fi
