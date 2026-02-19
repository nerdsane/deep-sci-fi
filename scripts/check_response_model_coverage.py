#!/usr/bin/env python3
"""Check response model coverage for changed FastAPI API files.

This is a universal (tool-agnostic) equivalent of the Claude-only
check-response-model hook. It enforces that every changed endpoint decorator
declares either:
  - response_model=
  - responses=
  - include_in_schema=False (explicitly internal)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


API_FILE_RE = re.compile(r"^platform/backend/api/.+\.py$")
ROUTE_BLOCK_RE = re.compile(
    r"@router\.(get|post|put|patch|delete)\((.*?)\)\s*\n(?:async\s+def|def\s+)",
    re.DOTALL,
)


def run_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return result.stdout.strip()


def changed_files(staged: bool, diff_range: str | None) -> list[str]:
    if diff_range:
        out = run_git(["diff", "--name-only", diff_range])
    elif staged:
        out = run_git(["diff", "--cached", "--name-only"])
    else:
        out = run_git(["diff", "--name-only"])

    files = []
    for line in out.splitlines():
        path = line.strip()
        if not path or not API_FILE_RE.match(path):
            continue
        if path.endswith("__init__.py"):
            continue
        files.append(path)
    return sorted(set(files))


def find_missing(path: Path) -> list[tuple[int, str, str]]:
    text = path.read_text(encoding="utf-8")
    missing: list[tuple[int, str, str]] = []

    for match in ROUTE_BLOCK_RE.finditer(text):
        method = match.group(1).upper()
        decorator_args = match.group(2)
        line = text.count("\n", 0, match.start()) + 1

        if "include_in_schema=False" in decorator_args:
            continue
        if "response_model=" in decorator_args or "responses=" in decorator_args:
            continue

        # Short preview for readable output
        preview = " ".join(decorator_args.strip().split())
        preview = preview[:200] + ("..." if len(preview) > 200 else "")
        missing.append((line, method, preview))

    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Check response_model coverage for changed API files")
    parser.add_argument("--staged", action="store_true", help="Check staged files")
    parser.add_argument(
        "--diff-range",
        type=str,
        default=None,
        help="Git diff range (example: origin/main...HEAD)",
    )
    args = parser.parse_args()

    files = changed_files(staged=args.staged, diff_range=args.diff_range)
    if not files:
        return 0

    repo_root = Path(run_git(["rev-parse", "--show-toplevel"]) or ".").resolve()
    failures: list[str] = []

    for rel in files:
        full = repo_root / rel
        if not full.exists():
            continue

        missing = find_missing(full)
        if not missing:
            continue

        failures.append(f"\n{rel}")
        for line, method, preview in missing:
            failures.append(f"  - line {line} [{method}] missing response_model/responses: {preview}")

    if not failures:
        return 0

    print("ERROR: Missing response_model/responses on changed API endpoints.")
    print("Every endpoint must declare response_model= or responses= (or include_in_schema=False).")
    print("\n".join(failures))
    return 1


if __name__ == "__main__":
    sys.exit(main())
