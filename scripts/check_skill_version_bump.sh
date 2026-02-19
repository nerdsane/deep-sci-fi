#!/bin/bash
#
# Check that skill.md edits include a version bump.
# Universal equivalent of Claude's check-skill-version hook behavior.
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

SKILL_FILE="platform/public/skill.md"

if [ "$MODE" = "range" ]; then
  if [ -z "$DIFF_RANGE" ]; then
    echo "ERROR: --diff-range requires a value"
    exit 1
  fi
  CHANGED=$(git diff --name-only "$DIFF_RANGE" -- "$SKILL_FILE" || true)
  DIFF_OUT=$(git diff "$DIFF_RANGE" -- "$SKILL_FILE" || true)
else
  CHANGED=$(git diff --cached --name-only -- "$SKILL_FILE" || true)
  DIFF_OUT=$(git diff --cached -- "$SKILL_FILE" || true)
fi

if [ -z "$CHANGED" ]; then
  exit 0
fi

HAS_VERSION_BUMP=false
HAS_HEADER_VERSION_BUMP=false

if echo "$DIFF_OUT" | grep -q '^+> Version:'; then
  HAS_VERSION_BUMP=true
fi

if echo "$DIFF_OUT" | grep -q '^+Send `X-Skill-Version:'; then
  HAS_HEADER_VERSION_BUMP=true
fi

if [ "$HAS_VERSION_BUMP" != "true" ]; then
  echo "ERROR: skill.md changed but '> Version: X.Y.Z | Last updated: YYYY-MM-DD' was not updated."
  echo "Bump skill version whenever skill.md content changes."
  exit 1
fi

if [ "$HAS_HEADER_VERSION_BUMP" != "true" ]; then
  echo "ERROR: skill.md version line changed but 'X-Skill-Version' header guidance was not updated."
  echo "Keep the X-Skill-Version value aligned with the version line."
  exit 1
fi

exit 0
