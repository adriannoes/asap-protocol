"""Contract tests for asap.cli._compat shim and trimmed cli/__init__.py surface."""

from __future__ import annotations

from pathlib import Path

import pytest

import asap.cli
import asap.cli._compat as compat
from asap.cli import repl as repl_module
from asap.cli import schemas as schemas_module
from asap.schemas import export_all_schemas as canonical_export_all_schemas

_LEGACY_SYMBOLS = ("DEFAULT_SCHEMAS_DIR", "export_all_schemas", "_repl_namespace")


def test_compat_all_exports() -> None:
    """_compat.__all__ declares exactly the three legacy symbols."""
    assert set(compat.__all__) == set(_LEGACY_SYMBOLS)


@pytest.mark.parametrize("name", list(compat.__all__))
def test_compat_symbols_importable(name: str) -> None:
    """Each name in _compat.__all__ is importable via getattr."""
    obj = getattr(compat, name)
    assert obj is not None


def test_compat_symbols_are_canonical_objects() -> None:
    """Re-exports are the same object as canonical imports."""
    assert compat.DEFAULT_SCHEMAS_DIR is schemas_module.DEFAULT_SCHEMAS_DIR
    assert compat.export_all_schemas is canonical_export_all_schemas
    assert compat._repl_namespace is repl_module._repl_namespace


def test_cli_init_public_all() -> None:
    """cli.__init__.__all__ exposes only app and main."""
    assert set(asap.cli.__all__) == {"app", "main"}


@pytest.mark.parametrize("name", _LEGACY_SYMBOLS)
def test_cli_init_does_not_export_legacy_symbols(name: str) -> None:
    """Legacy symbols are not re-exported from asap.cli root."""
    with pytest.raises(AttributeError):
        getattr(asap.cli, name)


def test_cli_init_line_count_within_ceiling() -> None:
    """cli/__init__.py stays small enough for a thin package facade (issue #242)."""
    repo_root = Path(__file__).resolve().parents[2]
    init_path = repo_root / "src/asap/cli/__init__.py"
    line_count = len(init_path.read_text(encoding="utf-8").splitlines())
    assert line_count <= 80


def test_compat_repl_namespace_behavior_unchanged() -> None:
    """_repl_namespace via shim returns dict with expected REPL keys."""
    ns = compat._repl_namespace()
    assert "Envelope" in ns
    assert "TaskRequest" in ns
    assert "sample_envelope" in ns
