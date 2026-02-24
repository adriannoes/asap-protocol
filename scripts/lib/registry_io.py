"""Shared I/O utilities for registry scripts.

Provides input sanitization, validation-result writing, and atomic
registry file load/save used by both registration and removal workflows.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, cast


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Strip code blocks, HTML, and control chars; clamp length."""
    if not text:
        return ""
    clean = re.sub(r"```[\s\S]*?```", "", text)
    clean = re.sub(r"`[^`]*`", "", clean)
    clean = re.sub(r"<[^>]+>", "", clean)
    clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", clean)
    return clean.strip()[:max_length]


def write_validation_result(
    output_path: str,
    *,
    valid: bool = False,
    errors: str = "",
    debug_id: str | None = None,
) -> None:
    out: dict[str, bool | str] = {"valid": valid, "errors": errors}
    if debug_id:
        out["debug_id"] = debug_id
    Path(output_path).write_text(json.dumps(out))


def load_registry(path: str) -> list[dict[str, Any]]:
    """Load registry JSON (array or LiteRegistry wrapper). Returns [] if missing."""
    p = Path(path)
    if not p.exists():
        return []
    raw: object = json.loads(p.read_text())
    if isinstance(raw, list):
        return cast(list[dict[str, Any]], raw)
    if isinstance(raw, dict) and "agents" in raw:
        return cast(list[dict[str, Any]], raw["agents"])
    return []


def save_registry(path: str, agents: list[dict[str, Any]]) -> None:
    """Write agents to path via temp file + rename (atomic)."""
    target = Path(path)
    content = json.dumps(agents, indent=2) + "\n"
    temp_dir = target.parent if target.parent != Path() else Path.cwd()
    fd, tmp = tempfile.mkstemp(dir=temp_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        Path(tmp).replace(target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
