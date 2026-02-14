#!/bin/bash
# Post-edit hook: auto-bump skill.md version when content changes
#
# Hook type: PostToolUse (Edit|Write matcher)
# Detects edits to skill.md or heartbeat.md and bumps the version + date
# if the content changed but the version line didn't.

set -euo pipefail

INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // ""' 2>/dev/null || echo "")

# Only trigger on skill.md or heartbeat.md edits
case "$FILE" in
  *skill.md|*heartbeat.md) ;;
  *) echo '{}'; exit 0 ;;
esac

PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")
SKILL_FILE="$PROJECT_ROOT/platform/public/skill.md"

if [ ! -f "$SKILL_FILE" ]; then
  echo '{}'
  exit 0
fi

# Check if skill.md has uncommitted changes
if ! git diff --name-only 2>/dev/null | grep -q "skill.md"; then
  echo '{}'
  exit 0
fi

# Check if the version line was already modified in this diff
if git diff "$SKILL_FILE" 2>/dev/null | grep -q "^+> Version:"; then
  # Version was already bumped in this edit — good
  echo '{}'
  exit 0
fi

# Content changed but version wasn't bumped — remind CC
CURRENT_VERSION=$(grep -oP 'Version: \K[\d.]+' "$SKILL_FILE" 2>/dev/null || echo "0.0.0")

cat <<ENDJSON
{
  "additionalContext": "WARNING: You modified skill.md content but didn't bump the version (currently $CURRENT_VERSION). Agents cache skill.md and only re-fetch when the version changes. Bump the version in the '> Version: X.Y.Z | Last updated: YYYY-MM-DD' line, and update the X-Skill-Version reference below it. Use semver: patch for fixes, minor for new features, major for breaking changes."
}
ENDJSON
