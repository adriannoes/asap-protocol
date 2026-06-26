"""Tests for scripts.lint_no_transport_growth (D4 transport surface guard).

Covers the v2.5.1 package-aware extension: the linter must aggregate public
symbols across every ``*.py`` module in a package directory (e.g. the decomposed
``client/`` package), naming methods by their defining class, so D4 stays
effective after the S2 decomposition that split ``client.py`` into a package.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.lint_no_transport_growth import (
    check_no_growth,
    extract_package_symbols,
    extract_surface_symbols,
)


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


_CLIENT_CORE = '''\
"""Synthetic package module: defines the public class and one method."""
from __future__ import annotations


class ASAPClient:
    def batch(self) -> None:
        return None
'''


_CLIENT_MIXIN = '''\
"""Synthetic package module: a mixin contributing public methods."""
from __future__ import annotations


class _SendMixin:
    async def send(self) -> None:
        return None

    def _private_helper(self) -> None:
        return None
'''


def test_extract_package_symbols_aggregates_across_modules(tmp_path: Path) -> None:
    """Symbols from every module in the package are collected; private names drop."""
    pkg = tmp_path / "client"
    _write(pkg / "_core.py", _CLIENT_CORE)
    _write(pkg / "_send.py", _CLIENT_MIXIN)

    symbols = extract_package_symbols(pkg)

    assert "ASAPClient.batch" in symbols
    assert "_SendMixin.send" in symbols
    assert "_SendMixin._private_helper" not in symbols


def test_extract_surface_symbols_dispatches_file_vs_dir(tmp_path: Path) -> None:
    """A file path is parsed directly; a directory path is aggregated as a package."""
    single = tmp_path / "server.py"
    _write(single, "def create_app() -> None:\n    return None\n")
    assert extract_surface_symbols(single) == ["create_app"]

    pkg = tmp_path / "client"
    _write(pkg / "_core.py", _CLIENT_CORE)
    assert extract_surface_symbols(pkg) == ["ASAPClient.batch"]


def _write_baseline(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def test_check_no_growth_passes_when_surface_within_baseline(tmp_path: Path) -> None:
    """No error when the package's public surface equals the frozen baseline."""
    pkg = tmp_path / "src" / "asap" / "transport" / "client"
    _write(pkg / "_core.py", _CLIENT_CORE)
    _write(pkg / "_send.py", _CLIENT_MIXIN)
    server = tmp_path / "src" / "asap" / "transport" / "server.py"
    _write(server, "def create_app() -> None:\n    return None\n")

    baseline = tmp_path / "baseline.json"
    _write_baseline(
        baseline,
        {
            "files": {
                "src/asap/transport/server.py": ["create_app"],
                "src/asap/transport/client": ["ASAPClient.batch", "_SendMixin.send"],
            }
        },
    )

    assert check_no_growth(tmp_path, baseline) == []


def test_check_no_growth_fails_on_new_public_method_in_package(tmp_path: Path) -> None:
    """A new public method added to any package module is a D4 violation."""
    server = tmp_path / "src" / "asap" / "transport" / "server.py"
    _write(server, "def create_app() -> None:\n    return None\n")
    pkg = tmp_path / "src" / "asap" / "transport" / "client"
    _write(pkg / "_core.py", _CLIENT_CORE)
    _write(
        pkg / "_send.py",
        _CLIENT_MIXIN + "\n\n    async def stream(self) -> None:\n        return None\n",
    )

    baseline = tmp_path / "baseline.json"
    _write_baseline(
        baseline,
        {
            "files": {
                "src/asap/transport/server.py": ["create_app"],
                "src/asap/transport/client": ["ASAPClient.batch", "_SendMixin.send"],
            }
        },
    )

    errors = check_no_growth(tmp_path, baseline)
    assert len(errors) == 1
    assert "_SendMixin.stream" in errors[0]
