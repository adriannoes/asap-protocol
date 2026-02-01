"""Internal link checker for docs/.

Verifies that relative links in docs/*.md point to existing files.
Safe to run in CI; no network. Skips external URLs.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Pattern: [text](path) or [text](path#anchor)
LINK_PATTERN = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")

DOCS_ROOT = Path(__file__).resolve().parent.parent / "docs"


def _collect_md_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.md"))


def _extract_links(content: str) -> list[str]:
    return [m.group(2).strip() for m in LINK_PATTERN.finditer(content)]


def _is_external(href: str) -> bool:
    return (
        href.startswith("http://")
        or href.startswith("https://")
        or href.startswith("mailto:")
        or href.startswith("#")
    )


def _resolve_target(from_file: Path, href: str) -> Path | None:
    """Resolve href relative to from_file. Returns path under DOCS_ROOT or None."""
    href_path = href.split("#")[0].strip()
    if not href_path:
        return from_file
    if href_path.startswith("/"):
        return None
    parent = from_file.parent
    resolved = (parent / href_path).resolve()
    try:
        resolved.relative_to(DOCS_ROOT.resolve())
    except ValueError:
        return None
    return resolved


@pytest.fixture(scope="module")
def docs_md_files() -> list[Path]:
    """All .md files under docs/."""
    if not DOCS_ROOT.exists():
        return []
    return _collect_md_files(DOCS_ROOT)


@pytest.fixture(scope="module")
def internal_links_by_file(
    docs_md_files: list[Path],
) -> list[tuple[Path, str, Path | None]]:
    """List of (from_file, href, resolved_path) for internal links."""
    out: list[tuple[Path, str, Path | None]] = []
    for md_file in docs_md_files:
        content = md_file.read_text(encoding="utf-8", errors="replace")
        for href in _extract_links(content):
            if _is_external(href):
                continue
            resolved = _resolve_target(md_file, href)
            out.append((md_file, href, resolved))
    return out


def test_docs_internal_links_targets_exist(
    internal_links_by_file: list[tuple[Path, str, Path | None]],
) -> None:
    """Every relative link in docs/ points to an existing file."""
    missing: list[tuple[Path, str, Path | None]] = []
    for from_file, href, resolved in internal_links_by_file:
        if resolved is None:
            continue
        if not resolved.exists():
            missing.append((from_file, href, resolved))
    assert not missing, (
        "Internal doc links pointing to missing files:\n"
        + "\n".join(
            f"  {f.relative_to(DOCS_ROOT)} -> {href} (resolved: {r})"
            for f, href, r in missing
        )
    )
