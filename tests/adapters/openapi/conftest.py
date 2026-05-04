"""Shared fixtures and helpers for OpenAPI adapter tests."""

from __future__ import annotations

import json
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


@contextmanager
def tmp_openapi_spec(
    tmp_path: Path, data: dict[str, Any], name: str
) -> Generator[Path, None, None]:
    """Write *data* as JSON under *tmp_path* and yield the file path (pytest cleans *tmp_path*)."""
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    yield path
