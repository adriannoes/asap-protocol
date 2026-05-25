"""Tests for scripts/validate_registry.py."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_registry import validate_registry


REGISTRY_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "registry"


def test_shellclaw_agents_array_fixture_validates() -> None:
    """ShellClaw registry array fixture passes the CI registry validator."""
    path = REGISTRY_FIXTURES_DIR / "shellclaw-v1.0-agents-array.json"
    assert validate_registry(path) == []


def test_lite_registry_with_hardware_fields_validates(tmp_path: Path) -> None:
    """LiteRegistry object form accepts v2.4 hardware and inference mirror fields."""
    entry_path = REGISTRY_FIXTURES_DIR / "shellclaw-v1.0-entry.json"
    entry = json.loads(entry_path.read_text(encoding="utf-8"))
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "updated_at": "2026-05-24T00:00:00Z",
                "agents": [entry],
            }
        ),
        encoding="utf-8",
    )

    assert validate_registry(registry_path) == []


def test_agents_array_rejects_string_hardware_io(tmp_path: Path) -> None:
    """Array-form registry rejects hardware_io when it is not a list."""
    entry_path = REGISTRY_FIXTURES_DIR / "shellclaw-v1.0-entry.json"
    entry = json.loads(entry_path.read_text(encoding="utf-8"))
    entry["hardware_io"] = "gpio"
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps([entry]), encoding="utf-8")

    errors = validate_registry(registry_path)

    assert any("agents[0].hardware_io" in error for error in errors)
