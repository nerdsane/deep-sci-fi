#!/usr/bin/env python3
"""Sync endpoint tables and auto-bump version in skill.md.

Reads the OpenAPI spec from the FastAPI app, groups endpoints by tag,
replaces content between AUTO markers in skill.md, and auto-bumps the
patch version whenever content changes (endpoints or prose).

Usage:
    cd platform/backend
    python scripts/sync_skill_endpoints.py           # Sync endpoints + auto-bump version
    python scripts/sync_skill_endpoints.py --check   # Exit non-zero if stale (CI mode)
"""
import datetime
import hashlib
import re
import subprocess
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


def _strip_version_lines(content: str) -> str:
    """Remove version/date lines so we can compare raw content changes."""
    lines = content.splitlines()
    filtered = []
    for line in lines:
        # Skip the 4 version-bearing lines
        if re.match(r"^version:\s*[\d.]+", line):
            continue
        if re.match(r"^>\s*Version:\s*[\d.]+", line):
            continue
        if re.match(r"\*\*Skill version:\*\*\s*[\d.]+", line):
            continue
        if re.search(r'"version":\s*"[\d.]+"', line):
            continue
        filtered.append(line)
    return "\n".join(filtered)


def _content_fingerprint(content: str) -> str:
    """MD5 of content with version/date lines stripped."""
    return hashlib.md5(_strip_version_lines(content).encode()).hexdigest()


def _get_head_content(skill_path: Path) -> str | None:
    """Read skill.md from git HEAD (returns None if unavailable)."""
    try:
        repo_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True, stderr=subprocess.DEVNULL,
        ).strip()
        rel_path = skill_path.relative_to(repo_root)
        return subprocess.check_output(
            ["git", "show", f"HEAD:{rel_path}"], text=True, stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, ValueError):
        return None


def _extract_version(content: str) -> str:
    """Extract version string from YAML frontmatter."""
    m = re.search(r"^version:\s*([\d.]+)", content, re.MULTILINE)
    return m.group(1) if m else "0.0.0"


def needs_version_bump(skill_path: Path) -> bool:
    """True when content changed from HEAD but version was not bumped."""
    current = skill_path.read_text(encoding="utf-8")
    head = _get_head_content(skill_path)
    if head is None:
        return False  # New file or not in git — nothing to compare

    # Content (excluding version lines) unchanged → no bump needed
    if _content_fingerprint(current) == _content_fingerprint(head):
        return False

    # Content changed — check whether version was already bumped
    if _extract_version(current) != _extract_version(head):
        return False  # Already bumped

    return True


def bump_version(skill_path: Path) -> str:
    """Increment patch version and update date in all 4 locations. Returns new version."""
    content = skill_path.read_text(encoding="utf-8")

    current_version = _extract_version(content)
    major, minor, patch = current_version.split(".")
    new_version = f"{major}.{minor}.{int(patch) + 1}"
    today = datetime.date.today().isoformat()

    # 1. YAML frontmatter: version: X.Y.Z
    content = re.sub(
        r"^(version:\s*)[\d.]+", rf"\g<1>{new_version}", content, count=1, flags=re.MULTILINE,
    )
    # 2. Markdown header: > Version: X.Y.Z | Last updated: YYYY-MM-DD
    content = re.sub(
        r"^(>\s*Version:\s*)[\d.]+ \| Last updated: \S+",
        rf"\g<1>{new_version} | Last updated: {today}",
        content, count=1, flags=re.MULTILINE,
    )
    # 3. Example JSON: {"version": "X.Y.Z", ...}
    content = re.sub(
        r'("version":\s*")[\d.]+"', rf'\g<1>{new_version}"', content, count=1,
    )
    # 4. Bold label: **Skill version:** X.Y.Z
    content = re.sub(
        r"(\*\*Skill version:\*\*\s*)[\d.]+", rf"\g<1>{new_version}", content, count=1,
    )

    skill_path.write_text(content, encoding="utf-8")
    print(f"  Version bumped: {current_version} → {new_version} (date: {today})")
    return new_version


def main() -> None:
    check_only = "--check" in sys.argv

    skill_path = backend_dir.parent / "public" / "skill.md"
    if not skill_path.exists():
        print(f"ERROR: skill.md not found at {skill_path}")
        sys.exit(1)

    print("Reading OpenAPI schema from FastAPI app...")
    tag_map = get_endpoints_by_tag()
    print(f"Found {len(tag_map)} tags, {sum(len(v) for v in tag_map.values())} total endpoints\n")

    # --- Phase 1: endpoint table sync ---
    mode = "Checking" if check_only else "Syncing"
    print(f"{mode} skill.md endpoint tables:")
    tables_changed = sync_skill_md(skill_path, tag_map, check_only=check_only)

    # --- Phase 2: version freshness ---
    version_stale = needs_version_bump(skill_path)

    if check_only:
        errors = []
        if tables_changed:
            errors.append("Endpoint tables are out of date.")
        if version_stale:
            errors.append("Content changed but version was not bumped.")
        if errors:
            print(f"\nERROR: {' '.join(errors)}")
            print("Run: cd platform/backend && python scripts/sync_skill_endpoints.py")
            sys.exit(1)
        print("\nskill.md endpoint tables and version are up to date.")
    else:
        if tables_changed or version_stale:
            bump_version(skill_path)
            print("\nskill.md updated successfully.")
        else:
            print("\nskill.md is already up to date.")


if __name__ == "__main__":
    main()
