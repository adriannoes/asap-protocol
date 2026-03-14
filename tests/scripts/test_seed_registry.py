"""Tests for scripts/seed_registry.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.seed_registry import build_seed_agents, write_registry


class TestBuildSeedAgents:
    def test_returns_at_least_requested_count(self) -> None:
        agents = build_seed_agents(100)
        assert len(agents) == 100

    def test_returns_120_for_default_count(self) -> None:
        agents = build_seed_agents(120)
        assert len(agents) == 120

    def test_all_entries_have_online_check_false(self) -> None:
        agents = build_seed_agents(10)
        for e in agents:
            assert e.online_check is False

    def test_ids_are_unique_urn_format(self) -> None:
        agents = build_seed_agents(50)
        ids = [e.id for e in agents]
        assert len(ids) == len(set(ids))
        for aid in ids:
            assert aid.startswith("urn:asap:agent:seed:agent-")
            assert aid[-1].isdigit() or (len(aid) > 20 and aid.rsplit("-", 1)[-1].isdigit())

    def test_entries_have_required_fields(self) -> None:
        agents = build_seed_agents(5)
        for e in agents:
            assert e.name
            assert e.description
            assert "http" in e.endpoints
            assert len(e.skills) >= 1
            assert e.asap_version


class TestWriteRegistry:
    def test_written_file_validates_as_lite_registry(self, tmp_path: Path) -> None:
        agents = build_seed_agents(15)
        out = tmp_path / "registry.json"
        write_registry(out, agents)
        raw = json.loads(out.read_text())
        assert raw.get("version") == "1.0"
        assert "updated_at" in raw
        assert len(raw["agents"]) == 15
        for a in raw["agents"]:
            assert a.get("online_check") is False

    def test_written_file_has_valid_agent_schema(self, tmp_path: Path) -> None:
        agents = build_seed_agents(3)
        write_registry(tmp_path / "reg.json", agents)
        from scripts.validate_registry import validate_registry

        errors = validate_registry(tmp_path / "reg.json")
        assert not errors, errors


class TestSeedRegistryMain:
    def test_main_writes_at_least_100_agents(self, tmp_path: Path) -> None:
        import subprocess
        import sys

        reg_path = tmp_path / "registry.json"
        repo_root = Path(__file__).resolve().parent.parent.parent
        result = subprocess.run(
            [
                sys.executable,
                str(repo_root / "scripts" / "seed_registry.py"),
                "--count",
                "105",
                "--registry",
                str(reg_path),
            ],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.fail(f"seed_registry failed: {result.stderr}")
        data = json.loads(reg_path.read_text())
        assert len(data["agents"]) >= 100
