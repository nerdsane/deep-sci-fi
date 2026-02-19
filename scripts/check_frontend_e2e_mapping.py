#!/usr/bin/env python3
"""Check that changed frontend files include matching E2E test changes.

Universal equivalent of Claude's check-e2e-coverage hook mapping.
This enforces file-level coupling between frontend surface areas and
expected Playwright specs.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys


E2E_FILE_RE = re.compile(r"^platform/e2e/.+\.spec\.ts$")
FRONTEND_FILE_RE = re.compile(r"^platform/(app|components)/.+\.(ts|tsx)$")

# Ordered list: first match wins (mirrors Claude hook behavior)
MAPPINGS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^platform/app/page\.tsx$"), "smoke.spec.ts"),
    (re.compile(r"^platform/app/how-it-works/"), "smoke.spec.ts"),
    (re.compile(r"^platform/app/feed/"), "feed.spec.ts"),
    (re.compile(r"^platform/app/worlds/"), "worlds.spec.ts"),
    (re.compile(r"^platform/app/world/"), "worlds.spec.ts"),
    (re.compile(r"^platform/app/proposals/"), "proposals.spec.ts"),
    (re.compile(r"^platform/app/proposal/"), "proposals.spec.ts"),
    (re.compile(r"^platform/app/agents/"), "agents.spec.ts"),
    (re.compile(r"^platform/app/agent/"), "agents.spec.ts"),
    (re.compile(r"^platform/app/stories/"), "stories.spec.ts"),
    (re.compile(r"^platform/app/dweller/"), "dweller.spec.ts"),
    (re.compile(r"^platform/app/aspect/"), "aspect.spec.ts"),
    (re.compile(r"^platform/components/world/"), "worlds.spec.ts"),
    (re.compile(r"^platform/components/feed/"), "feed.spec.ts"),
    (re.compile(r"^platform/components/social/"), "multiple"),
]


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
    return [line.strip() for line in out.splitlines() if line.strip()]


def mapped_test(path: str) -> str | None:
    for pattern, test_file in MAPPINGS:
        if pattern.search(path):
            return test_file
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Check frontend→E2E mapping on changed files")
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

    frontend_changed = [f for f in files if FRONTEND_FILE_RE.match(f)]
    e2e_changed = [f for f in files if E2E_FILE_RE.match(f)]

    if not frontend_changed:
        return 0

    required: dict[str, list[str]] = {}
    for f in frontend_changed:
        test_file = mapped_test(f)
        if not test_file:
            continue
        required.setdefault(test_file, []).append(f)

    if not required:
        return 0

    changed_e2e_names = {f.split("/")[-1] for f in e2e_changed}
    missing: list[tuple[str, list[str]]] = []

    for needed, sources in required.items():
        if needed == "multiple":
            if e2e_changed:
                continue
            missing.append(("any platform/e2e/*.spec.ts", sources))
            continue

        if needed not in changed_e2e_names:
            missing.append((needed, sources))

    if not missing:
        return 0

    print("ERROR: Frontend files changed without matching E2E spec updates.")
    for needed, sources in missing:
        print(f"\nRequired E2E change: {needed}")
        print("Triggered by:")
        for src in sources:
            print(f"  - {src}")
    print("\nUpdate the mapped Playwright spec(s) before committing.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
