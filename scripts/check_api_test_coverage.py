#!/usr/bin/env python3
"""Check API test coverage for changed backend API files.

Universal (tool-agnostic) equivalent of Claude's check-api-test-coverage hook.
For each changed API module, if routes are present but no backend/e2e tests
reference that module's router prefix, fail with actionable output.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


API_FILE_RE = re.compile(r"^platform/backend/api/.+\.py$")
ROUTE_RE = re.compile(r"@router\.(get|post|put|patch|delete)\(\s*['\"]([^'\"]+)['\"]")
PREFIX_RE = re.compile(r"APIRouter\([^)]*prefix\s*=\s*['\"]([^'\"]+)['\"][^)]*\)", re.DOTALL)


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


def parse_routes(text: str) -> list[str]:
    routes = []
    for method, route in ROUTE_RE.findall(text):
        routes.append(f"{method.upper()} {route}")
    return routes


def parse_prefix(text: str) -> str:
    match = PREFIX_RE.search(text)
    if match:
        return match.group(1)
    return ""


def iter_test_files(repo_root: Path) -> list[Path]:
    paths: list[Path] = []
    backend_tests = repo_root / "platform/backend/tests"
    e2e_tests = repo_root / "platform/e2e"

    if backend_tests.exists():
        paths.extend(backend_tests.rglob("*.py"))
    if e2e_tests.exists():
        paths.extend(e2e_tests.rglob("*.ts"))
    return paths


def has_prefix_reference(prefix: str, test_files: list[Path]) -> bool:
    if not prefix:
        return False
    for path in test_files:
        try:
            if prefix in path.read_text(encoding="utf-8"):
                return True
        except UnicodeDecodeError:
            continue
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Check API test coverage for changed API files")
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
    test_files = iter_test_files(repo_root)

    failures: list[str] = []
    for rel in files:
        full = repo_root / rel
        if not full.exists():
            continue

        text = full.read_text(encoding="utf-8")
        routes = parse_routes(text)
        if not routes:
            continue

        prefix = parse_prefix(text)
        if has_prefix_reference(prefix, test_files):
            continue

        failures.append(f"\n{rel}")
        failures.append(f"  - router prefix: {prefix or '(none found)'}")
        failures.append("  - routes:")
        for route in routes:
            failures.append(f"    * {route}")
        failures.append(
            "  - action: add/update integration or e2e tests that hit this prefix"
        )

    if not failures:
        return 0

    print("ERROR: Changed API modules appear untested by route prefix.")
    print("Add tests that make HTTP requests to the changed endpoints.")
    print("\n".join(failures))
    return 1


if __name__ == "__main__":
    sys.exit(main())
