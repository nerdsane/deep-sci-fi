#!/usr/bin/env python3
"""DST Endpoint Coverage Checker.

Compares FastAPI endpoints from OpenAPI spec against URL patterns found
in DST test files. Reports coverage and optionally fails if uncovered
state-mutating endpoints exist.

Usage:
    python scripts/check_dst_coverage.py           # Report only
    python scripts/check_dst_coverage.py --check    # Fail if uncovered POST/PATCH/DELETE
"""

import argparse
import json
import os
import re
import sys

# Must set env vars before importing app
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ.setdefault("DST_SIMULATION", "true")

# Add backend to path
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "platform", "backend")
sys.path.insert(0, os.path.abspath(BACKEND_DIR))


def get_openapi_endpoints() -> list[dict]:
    """Extract all endpoints from FastAPI's OpenAPI spec."""
    from main import app

    schema = app.openapi()
    endpoints = []
    for path, methods in schema.get("paths", {}).items():
        for method in methods:
            if method.upper() in ("GET", "POST", "PUT", "PATCH", "DELETE"):
                endpoints.append({
                    "method": method.upper(),
                    "path": path,
                    "is_mutating": method.upper() in ("POST", "PUT", "PATCH", "DELETE"),
                })
    return endpoints


def normalize_path(path: str) -> str:
    """Normalize path for comparison: /api/dwellers/{dweller_id}/claim -> /api/dwellers/*/claim"""
    return re.sub(r"\{[^}]+\}", "*", path)


def get_dst_url_patterns() -> set[tuple[str, str]]:
    """Parse DST test files for URL patterns used in self.client calls."""
    test_dir = os.path.join(BACKEND_DIR, "tests", "simulation")
    patterns = set()

    # Regex to match self.client.(post|get|patch|delete|put)(
    #   f"/api/..." or "/api/..."
    method_re = re.compile(
        r'self\.client\.(post|get|patch|delete|put)\(\s*'
        r'(?:f)?["\']([^"\']+)["\']',
        re.MULTILINE,
    )

    # Scan rules/ directory and test_game_rules*.py
    scan_dirs = [
        os.path.join(test_dir, "rules"),
        test_dir,
    ]

    for scan_dir in scan_dirs:
        if not os.path.isdir(scan_dir):
            continue
        for fname in os.listdir(scan_dir):
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(scan_dir, fname)
            with open(fpath) as f:
                content = f.read()
            for match in method_re.finditer(content):
                method = match.group(1).upper()
                url = match.group(2)
                # Normalize f-string variables: {did} -> *
                url = re.sub(r"\{[^}]*\}", "*", url)
                # Strip query params
                url = url.split("?")[0]
                patterns.add((method, url))

    return patterns


def match_endpoint(ep_method: str, ep_path: str, dst_patterns: set[tuple[str, str]]) -> bool:
    """Check if an endpoint matches any DST pattern."""
    norm_ep = normalize_path(ep_path)
    for dst_method, dst_path in dst_patterns:
        if dst_method == ep_method and norm_ep == dst_path:
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Check DST endpoint coverage")
    parser.add_argument("--check", action="store_true",
                        help="Exit 1 if uncovered state-mutating endpoints exist")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON instead of text")
    args = parser.parse_args()

    endpoints = get_openapi_endpoints()
    dst_patterns = get_dst_url_patterns()

    covered = []
    uncovered = []
    for ep in endpoints:
        if match_endpoint(ep["method"], ep["path"], dst_patterns):
            covered.append(ep)
        else:
            uncovered.append(ep)

    total = len(endpoints)
    covered_count = len(covered)
    uncovered_mutating = [e for e in uncovered if e["is_mutating"]]
    uncovered_readonly = [e for e in uncovered if not e["is_mutating"]]

    if args.json:
        print(json.dumps({
            "total": total,
            "covered": covered_count,
            "uncovered_mutating": [f"{e['method']} {e['path']}" for e in uncovered_mutating],
            "uncovered_readonly": [f"{e['method']} {e['path']}" for e in uncovered_readonly],
            "coverage_pct": round(covered_count / total * 100, 1) if total > 0 else 0,
        }, indent=2))
    else:
        print(f"\nDST Coverage: {covered_count}/{total} endpoints ({round(covered_count / total * 100, 1) if total else 0}%)")
        print(f"  State-mutating: {sum(1 for e in covered if e['is_mutating'])}/{sum(1 for e in endpoints if e['is_mutating'])} covered")
        print(f"  Read-only:      {sum(1 for e in covered if not e['is_mutating'])}/{sum(1 for e in endpoints if not e['is_mutating'])} covered")

        if uncovered_mutating:
            print(f"\n  UNCOVERED state-mutating endpoints ({len(uncovered_mutating)}):")
            for e in sorted(uncovered_mutating, key=lambda x: x["path"]):
                print(f"    {e['method']} {e['path']}")

        if uncovered_readonly:
            print(f"\n  Uncovered read-only endpoints ({len(uncovered_readonly)}):")
            for e in sorted(uncovered_readonly, key=lambda x: x["path"]):
                print(f"    {e['method']} {e['path']}")

        print()

    if args.check and uncovered_mutating:
        print(f"ERROR: {len(uncovered_mutating)} uncovered state-mutating endpoints!", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
