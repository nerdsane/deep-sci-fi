#!/bin/bash
#
# Mark DST review as completed for this repository workspace.
#

set -euo pipefail

WORKSPACE_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PROJECT_HASH="$(echo "$WORKSPACE_ROOT" | shasum -a 256 | cut -c1-12)"
MARKER_DIR="/tmp/dsf-harness/${PROJECT_HASH}"

mkdir -p "$MARKER_DIR"
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) dst-review-passed" > "$MARKER_DIR/dst-reviewed"

echo "Created marker: $MARKER_DIR/dst-reviewed"
