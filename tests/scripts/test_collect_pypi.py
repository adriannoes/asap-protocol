"""Tests for scripts/telemetry/collect_pypi.py."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from scripts.telemetry.collect_pypi import (
    DEFAULT_PYPI_PACKAGES,
    collect_pypi_recent,
    fetch_pypi_recent,
    normalize_recent_counts,
)

REQUIRED_DEFAULT_PYPI_PACKAGES: frozenset[str] = frozenset(
    {
        "asap-protocol",
        "asap-compliance",
    }
)


class TestDefaultPypiPackages:
    def test_defaults_cover_protocol_and_compliance(self) -> None:
        assert len(DEFAULT_PYPI_PACKAGES) >= 2
        assert REQUIRED_DEFAULT_PYPI_PACKAGES.issubset(DEFAULT_PYPI_PACKAGES)


class TestNormalizeRecentCounts:
    def test_parses_ints(self) -> None:
        data = {"last_day": 1, "last_week": 10, "last_month": 100}
        assert normalize_recent_counts(data) == data

    def test_parses_numeric_strings(self) -> None:
        data = {"last_day": "5", "last_week": "50", "last_month": "500"}
        assert normalize_recent_counts(data) == {
            "last_day": 5,
            "last_week": 50,
            "last_month": 500,
        }

    def test_rejects_missing_key(self) -> None:
        with pytest.raises(ValueError, match="last_week"):
            normalize_recent_counts({"last_day": 1, "last_month": 2})

    def test_rejects_non_object(self) -> None:
        with pytest.raises(ValueError, match="JSON object"):
            normalize_recent_counts([])


class TestFetchPypiRecent:
    @patch("scripts.telemetry.collect_pypi.pypistats.recent")
    def test_parses_json_envelope(
        self,
        mock_recent: object,
    ) -> None:
        mock_recent.return_value = json.dumps(
            {
                "package": "asap-protocol",
                "data": {"last_day": 2, "last_week": 20, "last_month": 200},
            }
        )
        out = fetch_pypi_recent("asap-protocol")
        assert out["package"] == "asap-protocol"
        assert out["downloads"] == {
            "last_day": 2,
            "last_week": 20,
            "last_month": 200,
        }

    @patch("scripts.telemetry.collect_pypi.pypistats.recent")
    def test_raises_on_no_data_message(self, mock_recent: object) -> None:
        mock_recent.return_value = "No data found for https://pypi.org/project/x/"
        with pytest.raises(ValueError, match="pypistats API"):
            fetch_pypi_recent("x")

    @patch("scripts.telemetry.collect_pypi.pypistats.recent")
    def test_raises_on_package_mismatch(self, mock_recent: object) -> None:
        mock_recent.return_value = json.dumps(
            {"package": "other", "data": {"last_day": 1, "last_week": 2, "last_month": 3}}
        )
        with pytest.raises(ValueError, match="mismatch"):
            fetch_pypi_recent("asap-protocol")


class TestCollectPypiRecent:
    @patch("scripts.telemetry.collect_pypi.pypistats.recent")
    def test_collects_multiple_packages(self, mock_recent: object) -> None:
        def _side_effect(pkg: str, **_kwargs: object) -> str:
            if pkg == "asap-protocol":
                counts = {"last_day": 1, "last_week": 10, "last_month": 100}
            else:
                counts = {"last_day": 0, "last_week": 3, "last_month": 30}
            return json.dumps({"package": pkg, "data": counts})

        mock_recent.side_effect = _side_effect

        report = collect_pypi_recent(("asap-protocol", "asap-cli"))
        assert report["source"] == "pypistats_recent"
        assert "collected_at" in report
        pkgs = report["packages"]
        assert pkgs["asap-protocol"]["downloads"]["last_week"] == 10
        assert pkgs["asap-cli"]["downloads"]["last_week"] == 3
        assert mock_recent.call_count == 2
