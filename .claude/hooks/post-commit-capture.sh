#!/bin/bash
# PostToolUse hook: after any git commit, remind CC to capture the moment.
#
# Hook type: PostToolUse (Bash matcher)
# Fires when a bash command contains "git commit"
# Reminds CC to write diary + X draft + update MEMORY.md
#
# This makes "write when it happens" structural, not behavioral.

set -euo pipefail

INPUT=$(cat)

COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null || echo "")

# Only trigger on git commit commands
if ! echo "$COMMAND" | grep -q 'git commit'; then
  echo '{}'
  exit 0
fi

# Check if this was a meaningful commit (not just a merge or empty trigger)
COMMIT_MSG=$(git log --format='%s' -1 2>/dev/null || echo "")

# Skip merge commits and chore commits
if echo "$COMMIT_MSG" | grep -qiE '^merge|^chore: trigger'; then
  echo '{}'
  exit 0
fi

cat <<ENDJSON
{
  "additionalContext": "📝 POST-COMMIT CAPTURE: You just committed: '$COMMIT_MSG'\n\nBefore moving on, consider:\n1. Is this a bug fix, feature, discovery, or insight? If yes → write a 1-3 sentence X-style take about it\n2. Did you learn something that should survive compaction? If yes → note it for MEMORY.md\n3. Did this close a harness gap? If yes → document the loop: bug → what test catches it → fix\n\nWrite drafts to shared-context/signals/for-calcifer/ and diary entries to memory/. Don't batch — the moment is freshest now."
}
ENDJSON
