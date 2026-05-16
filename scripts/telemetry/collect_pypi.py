#!/usr/bin/env python3
"""Fetch PyPI download aggregates for a package via `pypistats` (PyPI Stats public API).

Mirrors ``pypistats recent <package>`` — **last_day**, **last_week**, **last_month** —
and emits JSON for weekly aggregation.

Requires the project optional extra ``telemetry`` (install: ``uv sync --extra telemetry``
or ``uv sync --all-extras``).

API: https://pypistats.org/api
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pypistats

DEFAULT_PYPI_PACKAGE = "asap-protocol"
_RECENT_KEYS = ("last_day", "last_week", "last_month")


def normalize_recent_counts(data: object) -> dict[str, int]:
    """Validate ``pypistats`` /recent ``data`` object and return integer counts.

    Raises:
        ValueError: If the payload is missing required keys or has invalid types.
    """
    if not isinstance(data, dict):
        msg = "pypistats recent 'data' must be a JSON object"
        raise ValueError(msg)
    out: dict[str, int] = {}
    for key in _RECENT_KEYS:
        if key not in data:
            msg = f"pypistats recent data missing key {key!r}"
            raise ValueError(msg)
        val = data[key]
        if isinstance(val, bool) or not isinstance(val, int | float | str):
            msg = f"pypistats recent {key!r} must be numeric"
            raise ValueError(msg)
        if isinstance(val, str):
            stripped = val.replace(",", "").strip()
            if not stripped.isdigit():
                msg = f"pypistats recent {key!r} is not an integer string"
                raise ValueError(msg)
            out[key] = int(stripped)
        else:
            out[key] = int(val)
    return out


def fetch_pypi_recent(package: str) -> dict[str, Any]:
    """Call ``pypistats.recent`` and return a minimal report dict for one package."""
    raw = pypistats.recent(package, format="json")
    if isinstance(raw, str) and not raw.strip().startswith("{"):
        msg = f"pypistats API: {raw}"
        raise ValueError(msg)
    payload: object = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(payload, dict):
        msg = "pypistats JSON response must be an object"
        raise ValueError(msg)
    name = payload.get("package")
    if name != package:
        msg = f"pypistats package mismatch: expected {package!r}, got {name!r}"
        raise ValueError(msg)
    counts = normalize_recent_counts(payload.get("data"))
    return {
        "package": package,
        "downloads": counts,
    }


def collect_pypi_recent(
    packages: tuple[str, ...],
) -> dict[str, Any]:
    """Collect recent download windows for each PyPI ``packages`` name."""
    collected_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    results: dict[str, dict[str, Any]] = {}
    for pkg in packages:
        results[pkg] = fetch_pypi_recent(pkg)
    return {
        "source": "pypistats_recent",
        "collected_at": collected_at,
        "packages": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Collect PyPI download aggregates (pypistats recent) for telemetry."
    )
    parser.add_argument(
        "--package",
        action="append",
        dest="packages",
        metavar="NAME",
        help=("PyPI project name (repeatable). Defaults to asap-protocol when omitted."),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write JSON to this path instead of stdout",
    )
    args = parser.parse_args(argv)
    pkgs: tuple[str, ...] = tuple(args.packages) if args.packages else (DEFAULT_PYPI_PACKAGE,)

    report = collect_pypi_recent(pkgs)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
