#!/usr/bin/env python3
"""E2E Route Coverage Checker.

Compares Next.js page routes (platform/app/**/page.tsx) against
URL patterns found in Playwright E2E test files (platform/e2e/**/*.spec.ts).
Reports covered vs uncovered routes and optionally fails if any are uncovered.

Usage:
    python scripts/check_e2e_coverage.py           # Report only
    python scripts/check_e2e_coverage.py --check    # Fail if uncovered routes
"""

import argparse
import os
import re
import sys


def discover_routes(platform_dir: str) -> list[str]:
    """Discover all Next.js routes from page.tsx files."""
    app_dir = os.path.join(platform_dir, "app")
    routes = []

    for root, dirs, files in os.walk(app_dir):
        if "page.tsx" in files:
            # Convert filesystem path to route
            rel = os.path.relpath(root, app_dir)
            if rel == ".":
                route = "/"
            else:
                # Convert [id] segments to Next.js convention
                route = "/" + rel.replace(os.sep, "/")
            routes.append(route)

    return sorted(routes)


def extract_goto_urls(e2e_dir: str) -> set[str]:
    """Extract page.goto(...) URL patterns from Playwright test files."""
    urls = set()
    goto_re = re.compile(
        r'page\.goto\(\s*[`"\']([^`"\']+)[`"\']\s*\)',
    )
    # Also match template literals with variables: page.goto(`/world/${setup.worldId}`)
    template_re = re.compile(
        r"page\.goto\(\s*`([^`]+)`\s*\)",
    )

    for root, dirs, files in os.walk(e2e_dir):
        for fname in files:
            if not fname.endswith(".spec.ts"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath) as f:
                content = f.read()

            # Extract simple string URLs
            for match in goto_re.finditer(content):
                urls.add(match.group(1))

            # Extract template literal URLs
            for match in template_re.finditer(content):
                urls.add(match.group(1))

    return urls


def normalize_url(url: str) -> str:
    """Normalize a URL to a route pattern.

    /world/${setup.worldId} -> /world/[id]
    /stories/abc-123        -> /stories/[id]
    /                       -> /
    """
    # Replace template literal expressions: ${...}
    url = re.sub(r"\$\{[^}]+\}", "[id]", url)
    # Replace UUID-like segments
    url = re.sub(r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "/[id]", url)
    # Strip query params
    url = url.split("?")[0]
    return url


def main():
    parser = argparse.ArgumentParser(description="Check E2E route coverage")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if any routes are uncovered by E2E tests",
    )
    args = parser.parse_args()

    # Resolve paths relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    platform_dir = os.path.join(project_root, "platform")
    e2e_dir = os.path.join(platform_dir, "e2e")

    if not os.path.isdir(e2e_dir):
        print("ERROR: E2E test directory not found at", e2e_dir, file=sys.stderr)
        sys.exit(1)

    routes = discover_routes(platform_dir)
    goto_urls = extract_goto_urls(e2e_dir)

    # Normalize all goto URLs to route patterns
    tested_routes = set()
    for url in goto_urls:
        normalized = normalize_url(url)
        tested_routes.add(normalized)

    covered = []
    uncovered = []
    for route in routes:
        if route in tested_routes:
            covered.append(route)
        else:
            uncovered.append(route)

    total = len(routes)
    covered_count = len(covered)
    pct = round(covered_count / total * 100, 1) if total else 0

    print(f"\nE2E Route Coverage: {covered_count}/{total} routes ({pct}%)")

    if covered:
        print(f"\n  Covered routes ({len(covered)}):")
        for r in covered:
            print(f"    {r}")

    if uncovered:
        print(f"\n  UNCOVERED routes ({len(uncovered)}):")
        for r in uncovered:
            print(f"    {r}")

    print()

    if args.check and uncovered:
        print(
            f"ERROR: {len(uncovered)} routes have no E2E test coverage!",
            file=sys.stderr,
        )
        for r in uncovered:
            print(f"    {r}", file=sys.stderr)
        print(
            "\nAdd page.goto() calls for these routes in platform/e2e/*.spec.ts files.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
