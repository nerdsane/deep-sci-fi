#!/bin/bash
#
# Universal review marker gate (agent-agnostic).
# Mirrors Claude's pre-commit review marker policy:
# - code-reviewed marker is always required for changed files
# - dst-reviewed marker is required when DST-sensitive files changed
#

set -euo pipefail

MODE="staged"
DIFF_RANGE=""

while [ $# -gt 0 ]; do
  case "$1" in
    --staged)
      MODE="staged"
      shift
      ;;
    --diff-range)
      MODE="range"
      DIFF_RANGE="${2:-}"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

WORKSPACE_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PROJECT_HASH="$(echo "$WORKSPACE_ROOT" | shasum -a 256 | cut -c1-12)"
MARKER_DIR="/tmp/dsf-harness/${PROJECT_HASH}"

if [ "$MODE" = "range" ]; then
  if [ -z "$DIFF_RANGE" ]; then
    echo "ERROR: --diff-range requires a value"
    exit 1
  fi
  CHANGED="$(git diff --name-only "$DIFF_RANGE" || true)"
else
  CHANGED="$(git diff --cached --name-only || true)"
fi

if [ -z "$CHANGED" ]; then
  exit 0
fi

CODE_MARKER="$MARKER_DIR/code-reviewed"
DST_MARKER="$MARKER_DIR/dst-reviewed"

if [ ! -f "$CODE_MARKER" ]; then
  echo "ERROR: Missing code review marker: $CODE_MARKER"
  echo "Run: ./scripts/run_required_reviews.sh --staged (or --diff-range <range>)"
  echo "Run: ./scripts/mark_code_reviewed.sh"
  exit 1
fi

# Require DST marker when changes touch DST-sensitive areas.
if echo "$CHANGED" | grep -qE '(^platform/backend/api/.+\.py$|^platform/backend/db/models\.py$|^platform/backend/tests/simulation/|validation|reviews\.py|^platform/public/skill\.md$)'; then
  if [ ! -f "$DST_MARKER" ]; then
    echo "ERROR: Missing DST review marker for DST-sensitive changes: $DST_MARKER"
    echo "Run: ./scripts/run_required_reviews.sh --staged (or --diff-range <range>)"
    echo "Run: ./scripts/mark_dst_reviewed.sh"
    exit 1
  fi
fi

exit 0
