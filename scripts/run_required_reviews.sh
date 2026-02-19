#!/bin/bash
#
# Auto-run required review agents using the same prompts Claude uses.
# This provides universal "auto-subagent-like" behavior for any local workflow.
#

set -euo pipefail

MODE="staged"
DIFF_RANGE=""
FORCE=false

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
    --force)
      FORCE=true
      shift
      ;;
    *)
      shift
      ;;
  esac
done

WORKSPACE_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PROJECT_HASH="$(echo "$WORKSPACE_ROOT" | shasum -a 256 | cut -c1-12)"
MARKER_DIR="/tmp/dsf-harness/${PROJECT_HASH}"
CODE_MARKER="$MARKER_DIR/code-reviewed"
DST_MARKER="$MARKER_DIR/dst-reviewed"
CODE_PROMPT_FILE="$WORKSPACE_ROOT/.claude/agents/code-reviewer.md"
DST_PROMPT_FILE="$WORKSPACE_ROOT/.claude/agents/dst-reviewer.md"
REVIEW_ENGINE=""

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

mkdir -p "$MARKER_DIR"

BASE_REF=""
if [ "$MODE" = "range" ] && [[ "$DIFF_RANGE" == *"..."* ]]; then
  BASE_REF="${DIFF_RANGE%%...*}"
fi

run_one_review() {
  local reviewer_name="$1"
  local prompt_file="$2"
  local marker_script="$3"
  local output_file prompt_tmp prompt_text

  if [ ! -f "$prompt_file" ]; then
    echo "ERROR: Missing reviewer prompt file: $prompt_file"
    return 1
  fi

  output_file="$(mktemp)"
  prompt_tmp="$(mktemp)"

  cat "$prompt_file" > "$prompt_tmp"
  {
    echo
    echo "## Runtime Instructions For Universal Auto-Review"
    if [ -n "$BASE_REF" ]; then
      echo "- Review branch diff relative to base: $BASE_REF"
    else
      echo "- Review currently staged/uncommitted changes."
    fi
    echo "- Keep the required output format from this prompt."
    echo "- End with exactly one verdict line: '### Verdict: PASS' or '### Verdict: FAIL'."
    echo "- Use FAIL when any blocking finding exists."
  } >> "$prompt_tmp"

  echo "[AUTO-REVIEW] Running $reviewer_name via $REVIEW_ENGINE..."
  prompt_text="$(cat "$prompt_tmp")"
  if [ "$REVIEW_ENGINE" = "codex" ]; then
    if [ -n "$BASE_REF" ]; then
      if ! codex exec review --base "$BASE_REF" "$prompt_text" > "$output_file" 2>&1; then
        echo "ERROR: $reviewer_name execution failed."
        tail -n 80 "$output_file" || true
        rm -f "$output_file" "$prompt_tmp"
        return 1
      fi
    else
      if ! codex exec review --uncommitted "$prompt_text" > "$output_file" 2>&1; then
        echo "ERROR: $reviewer_name execution failed."
        tail -n 80 "$output_file" || true
        rm -f "$output_file" "$prompt_tmp"
        return 1
      fi
    fi
  elif [ "$REVIEW_ENGINE" = "claude" ]; then
    if ! claude -p --agent "$reviewer_name" "$prompt_text" > "$output_file" 2>&1; then
      echo "ERROR: $reviewer_name execution failed."
      tail -n 80 "$output_file" || true
      rm -f "$output_file" "$prompt_tmp"
      return 1
    fi
  else
    echo "ERROR: No review engine available."
    rm -f "$output_file" "$prompt_tmp"
    return 1
  fi

  if ! grep -Eiq '^[[:space:]]*#{0,3}[[:space:]]*Verdict:[[:space:]]*PASS([[:space:]]|$)' "$output_file"; then
    echo "ERROR: $reviewer_name returned non-PASS verdict."
    tail -n 120 "$output_file" || true
    rm -f "$output_file" "$prompt_tmp"
    return 1
  fi

  "$marker_script" >/dev/null
  echo "[AUTO-REVIEW] $reviewer_name PASS."

  rm -f "$output_file" "$prompt_tmp"
  return 0
}

DST_REQUIRED=false
if echo "$CHANGED" | grep -qE '(^platform/backend/api/.+\.py$|^platform/backend/db/models\.py$|^platform/backend/tests/simulation/|validation|reviews\.py|^platform/public/skill\.md$)'; then
  DST_REQUIRED=true
fi

NEED_CODE_REVIEW=false
NEED_DST_REVIEW=false

if [ "$FORCE" = true ] || [ ! -f "$CODE_MARKER" ]; then
  NEED_CODE_REVIEW=true
fi

if [ "$DST_REQUIRED" = true ]; then
  if [ "$FORCE" = true ] || [ ! -f "$DST_MARKER" ]; then
    NEED_DST_REVIEW=true
  fi
fi

if [ "$NEED_CODE_REVIEW" = false ] && [ "$NEED_DST_REVIEW" = false ]; then
  exit 0
fi

if [ "${DSF_DISABLE_AUTO_REVIEW:-0}" = "1" ]; then
  echo "[AUTO-REVIEW] Disabled via DSF_DISABLE_AUTO_REVIEW=1."
  exit 0
fi

if command -v codex >/dev/null 2>&1; then
  REVIEW_ENGINE="codex"
elif command -v claude >/dev/null 2>&1; then
  REVIEW_ENGINE="claude"
else
  echo "ERROR: neither codex nor claude CLI is installed; cannot auto-run required reviewers."
  echo "Install codex/claude CLI or create markers manually."
  exit 1
fi

if [ "$NEED_CODE_REVIEW" = true ]; then
  run_one_review "code-reviewer" "$CODE_PROMPT_FILE" "$WORKSPACE_ROOT/scripts/mark_code_reviewed.sh"
fi

if [ "$NEED_DST_REVIEW" = true ]; then
  run_one_review "dst-reviewer" "$DST_PROMPT_FILE" "$WORKSPACE_ROOT/scripts/mark_dst_reviewed.sh"
fi

exit 0
