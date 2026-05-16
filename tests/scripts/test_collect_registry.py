"""Tests for scripts/telemetry/collect_registry.py."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from scripts.telemetry.collect_registry import (
    collect_registry_snapshot,
    count_registry_agents,
    detect_registry_format,
    fetch_registry_json,
    load_previous_count,
    main,
    resolve_previous_agent_count,
)


class TestCountRegistryAgents:
    def test_counts_lite_registry(self) -> None:
        raw = {"version": "1", "agents": [{"id": "a"}, {"id": "b"}]}
        assert count_registry_agents(raw) == 2

    def test_counts_array_root(self) -> None:
        assert count_registry_agents([{"id": "x"}]) == 1

    def test_rejects_bad_root(self) -> None:
        with pytest.raises(ValueError, match="array"):
            count_registry_agents({"no_agents": []})


class TestDetectRegistryFormat:
    def test_lite_registry(self) -> None:
        assert detect_registry_format({"agents": []}) == "lite_registry"

    def test_array(self) -> None:
        assert detect_registry_format([]) == "array"


class TestResolvePreviousAgentCount:
    def test_from_telemetry_json(self) -> None:
        assert resolve_previous_agent_count({"agent_count": 42}) == 42

    def test_from_registry_wrapper(self) -> None:
        raw = {"agents": [{"id": "1"}, {"id": "2"}]}
        assert resolve_previous_agent_count(raw) == 2


class TestLoadPreviousCount:
    def test_reads_file(self, tmp_path: Path) -> None:
        p = tmp_path / "prev.json"
        p.write_text(json.dumps({"agent_count": 5}), encoding="utf-8")
        assert load_previous_count(p) == 5


class TestFetchRegistryJson:
    def test_https_only(self) -> None:
        with pytest.raises(ValueError, match="scheme"):
            fetch_registry_json("file:///etc/passwd")

    def test_gets_json(self) -> None:
        payload: dict[str, object] = {"agents": []}

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.host == "example.com"
            return httpx.Response(200, json=payload)

        transport = httpx.MockTransport(handler)
        with httpx.Client(transport=transport) as client:
            out = fetch_registry_json("https://example.com/registry.json", client=client)
        assert out == payload


class TestCollectRegistrySnapshot:
    def test_growth_when_previous_set(self) -> None:
        raw: dict[str, object] = {"agents": [{}] * 4}
        report = collect_registry_snapshot(
            raw,
            registry_ref="https://example/r.json",
            previous_count=2,
        )
        assert report["agent_count"] == 4
        assert report["growth"] == 2
        assert report["previous_agent_count"] == 2

    def test_growth_none_without_previous(self) -> None:
        raw: dict[str, object] = {"agents": [{}]}
        report = collect_registry_snapshot(
            raw,
            registry_ref="local",
            previous_count=None,
        )
        assert report["growth"] is None
        assert report["previous_agent_count"] is None


class TestMainCli:
    def test_local_registry_and_previous(self, tmp_path: Path) -> None:
        reg = tmp_path / "registry.json"
        reg.write_text(
            json.dumps({"agents": [{"id": "a"}, {"id": "b"}]}),
            encoding="utf-8",
        )
        prev = tmp_path / "prev.json"
        prev.write_text(json.dumps({"agent_count": 1}), encoding="utf-8")
        out = tmp_path / "out.json"
        rc = main(
            [
                "--registry-path",
                str(reg),
                "--previous",
                str(prev),
                "-o",
                str(out),
            ]
        )
        assert rc == 0
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["agent_count"] == 2
        assert data["growth"] == 1

    def test_missing_previous_errors(self, tmp_path: Path) -> None:
        reg = tmp_path / "registry.json"
        reg.write_text(json.dumps({"agents": []}), encoding="utf-8")
        rc = main(
            [
                "--registry-path",
                str(reg),
                "--previous",
                str(tmp_path / "nope.json"),
            ]
        )
        assert rc == 1
