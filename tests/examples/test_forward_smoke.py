"""Unit tests for starter smoke forwarder (DIST-003)."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FORWARD_SMOKE_PATH = _REPO_ROOT / "examples" / "starters" / "_forward_smoke.py"


def _load_forward_smoke() -> ModuleType:
    """Load examples/starters/_forward_smoke.py by path (not a package)."""
    spec = importlib.util.spec_from_file_location(
        "forward_smoke_under_test",
        _FORWARD_SMOKE_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_forward_parent_exits_when_parent_missing(
    tmp_path: Path,
    capsys: CaptureFixture[str],
) -> None:
    """Missing parent example exits 1 with expected path context."""
    forward_smoke = _load_forward_smoke()
    missing = tmp_path / "missing_parent.py"
    with pytest.raises(SystemExit) as exc_info:
        forward_smoke.forward_parent(
            missing,
            label="OpenAPI",
            expected_relpath="examples/openapi_petstore/main.py",
        )
    assert exc_info.value.code == 1
    err = capsys.readouterr().err
    assert str(missing) in err
    assert "examples/openapi_petstore/main.py" in err


def test_forward_parent_timeout_omits_argv_and_exits_124(
    tmp_path: Path,
    capsys: CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Timeout logs script basename only — argv may carry secrets."""
    forward_smoke = _load_forward_smoke()
    parent = tmp_path / "parent_smoke.py"
    parent.write_text("print('ok')\n", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["smoke.py", "--token", "super-secret-token"],
    )

    with (
        patch.object(
            forward_smoke.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(
                cmd=["python", str(parent)],
                timeout=1,
            ),
        ),
        pytest.raises(SystemExit) as exc_info,
    ):
        forward_smoke.forward_parent(
            parent,
            label="OpenAPI",
            expected_relpath="x",
            timeout_sec=1,
        )

    assert exc_info.value.code == 124
    err = capsys.readouterr().err
    assert "parent_smoke.py" in err
    assert "arguments omitted" in err
    assert "super-secret-token" not in err
    assert "--token" not in err


def test_forward_parent_forwards_returncode(tmp_path: Path) -> None:
    """Successful runs exit with the parent process return code."""
    forward_smoke = _load_forward_smoke()
    parent = tmp_path / "parent_smoke.py"
    parent.write_text("print('ok')\n", encoding="utf-8")

    with (
        patch.object(
            forward_smoke.subprocess,
            "run",
            return_value=Mock(returncode=42),
        ),
        pytest.raises(SystemExit) as exc_info,
    ):
        forward_smoke.forward_parent(parent, label="OpenAPI", expected_relpath="x")

    assert exc_info.value.code == 42
