"""Tests for scripts/telemetry/aggregate.py."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pytest

from scripts.telemetry import aggregate as aggregate_mod


def test_validate_snapshot_accepts_minimal_shape() -> None:
    sample: dict[str, Any] = {
        "snapshot_version": 1,
        "collected_at": "2026-05-16T12:00:00+00:00",
        "npm": {"@asap-protocol/client": 10},
        "pypi": {"source": "x"},
        "github": {"source": "github_rest_api"},
        "registry": {"agent_count": 1},
        "site": {"ctr_per_cta": {}},
        "adapter_requests": {},
    }
    aggregate_mod.validate_snapshot(sample)


def test_flatten_adapter_request_counts() -> None:
    gh: dict[str, Any] = {
        "adapter_requests": {
            "by_framework": {"mastra": 2, "langgraph": 1},
            "unparsed_open_count": 1,
        },
    }
    out = aggregate_mod.flatten_adapter_request_counts(gh)
    assert out["mastra"] == 2
    assert out["_unparsed"] == 1


def test_render_dashboard_adapter_section_sorted() -> None:
    snap: dict[str, Any] = {
        "adapter_requests": {"mastra": 2, "x": 5, "_unparsed": 1},
    }
    hist = [(date(2026, 5, 16), Path("snapshot-2026-05-16.json"))]
    md = aggregate_mod.render_dashboard(snap, hist, weeks=12)
    assert "## Adapter requests" in md
    # x has higher count than mastra; _unparsed last
    x_pos = md.index("| `x` |")
    m_pos = md.index("| `mastra` |")
    u_pos = md.index("| `_unparsed` |")
    assert x_pos < m_pos < u_pos


def test_main_writes_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        aggregate_mod,
        "collect_npm_weekly",
        lambda *_a, **_k: {
            "packages": {"@asap-protocol/client": {"downloads": 42}},
        },
    )
    monkeypatch.setattr(
        aggregate_mod,
        "collect_pypi_recent",
        lambda *_a, **_k: {"packages": {}, "source": "stub"},
    )
    monkeypatch.setattr(
        aggregate_mod,
        "collect_github_or_placeholder",
        lambda *_a, **_k: {
            "source": "github_rest_api",
            "adapter_requests": {"by_framework": {"acme": 1}, "open_count": 1},
            "repo": {"stargazers_count": 3},
        },
    )

    def _fake_fetch(_url: str) -> dict[str, Any]:
        return {"agents": [{"id": "a"}]}

    monkeypatch.setattr(aggregate_mod, "fetch_registry_json", _fake_fetch)
    monkeypatch.setattr(aggregate_mod, "update_latest_symlink", lambda *_a, **_k: None)

    code = aggregate_mod.main(
        ["--output-dir", str(tmp_path), "--date", "2026-05-16"],
    )
    assert code == 0
    written = (tmp_path / "snapshot-2026-05-16.json").read_text(encoding="utf-8")
    assert "adapter_requests" in written
    assert (tmp_path / "dashboard.md").is_file()
