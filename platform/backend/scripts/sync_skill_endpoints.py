#!/usr/bin/env python3
"""Sync endpoint tables in skill.md from the FastAPI OpenAPI schema.

Reads the OpenAPI spec from the FastAPI app, groups endpoints by tag,
and replaces content between AUTO markers in skill.md.

Usage:
    cd platform/backend
    python scripts/sync_skill_endpoints.py           # Update skill.md in place
    python scripts/sync_skill_endpoints.py --check   # Exit non-zero if stale (CI mode)
"""
import re
import sys
from pathlib import Path

# Ensure backend directory is on the path so `main` can be imported
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from main import app  # noqa: E402


def get_endpoints_by_tag() -> dict[str, list[dict]]:
    """Extract endpoints grouped by OpenAPI tag."""
    schema = app.openapi()
    paths = schema.get("paths", {})

    tag_map: dict[str, list[dict]] = {}
    for path, methods in paths.items():
        for method, details in methods.items():
            if method in ("get", "post", "put", "patch", "delete"):
                tags = details.get("tags", ["untagged"])
                summary = details.get("summary", "")
                for tag in tags:
                    tag_map.setdefault(tag, []).append({
                        "method": method.upper(),
                        "path": path,
                        "summary": summary,
                    })
    return tag_map


def build_table(endpoints: list[dict]) -> str:
    """Build a markdown table from a list of endpoints."""
    lines = [
        "| Endpoint | Description |",
        "|----------|-------------|",
    ]
    for ep in endpoints:
        # Paths from OpenAPI don't include /api prefix since routers use prefix="/api"
        # They look like /api/proposals/{id}/submit already
        path = ep["path"]
        lines.append(f"| `{ep['method']} {path}` | {ep['summary']} |")
    return "\n".join(lines)


def sync_skill_md(skill_path: Path, tag_map: dict[str, list[dict]], *, check_only: bool = False) -> bool:
    """Replace AUTO-marked sections in skill.md with generated tables.

    Args:
        check_only: If True, don't write — just report whether changes are needed.

    Returns True if changes were made (or would be made in check mode).
    """
    content = skill_path.read_text(encoding="utf-8")
    original = content

    # Find all AUTO markers: <!-- AUTO:endpoints:TAG --> ... <!-- /AUTO:endpoints:TAG -->
    pattern = re.compile(
        r"(<!-- AUTO:endpoints:(\S+?) -->)\n.*?\n(<!-- /AUTO:endpoints:\2 -->)",
        re.DOTALL,
    )

    def replacer(match: re.Match) -> str:
        open_marker = match.group(1)
        tag = match.group(2)
        close_marker = match.group(3)

        endpoints = tag_map.get(tag)
        if endpoints is None:
            print(f"  WARNING: No OpenAPI tag '{tag}' found — leaving section unchanged")
            return match.group(0)

        table = build_table(endpoints)
        print(f"  {tag}: {len(endpoints)} endpoints")
        return f"{open_marker}\n{table}\n{close_marker}"

    content = pattern.sub(replacer, content)

    if content != original:
        if not check_only:
            skill_path.write_text(content, encoding="utf-8")
        return True
    return False


def main() -> None:
    check_only = "--check" in sys.argv

    skill_path = backend_dir.parent / "public" / "skill.md"
    if not skill_path.exists():
        print(f"ERROR: skill.md not found at {skill_path}")
        sys.exit(1)

    print("Reading OpenAPI schema from FastAPI app...")
    tag_map = get_endpoints_by_tag()
    print(f"Found {len(tag_map)} tags, {sum(len(v) for v in tag_map.values())} total endpoints\n")

    mode = "Checking" if check_only else "Syncing"
    print(f"{mode} skill.md endpoint tables:")
    changed = sync_skill_md(skill_path, tag_map, check_only=check_only)

    if check_only:
        if changed:
            print("\nERROR: skill.md endpoint tables are out of date!")
            print("Run: cd platform/backend && python scripts/sync_skill_endpoints.py")
            sys.exit(1)
        else:
            print("\nskill.md endpoint tables are up to date.")
    else:
        if changed:
            print("\nskill.md updated successfully.")
        else:
            print("\nskill.md is already up to date.")


if __name__ == "__main__":
    main()
