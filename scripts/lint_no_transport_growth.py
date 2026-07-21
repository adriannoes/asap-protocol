#!/usr/bin/env python3
"""Forbid growing public surface on transport server/client modules.

Compares the set of public function/method names in the transport server module
(``server.py``) and the transport client package (``client/``) against the frozen
baseline in ``scripts/_transport_baseline_v2.5.1.json``. New public symbols fail
CI; removed symbols are allowed.

The client was a single ``client.py`` module through v2.5.0 and later
decomposed into the ``client/`` package (``_core`` / ``_send`` /
``_discovery`` / ``_helpers``). To keep frozen-surface enforcement effective
on a package, the linter aggregates public symbols across **every**
``*.py`` module in the package directory (methods are named by their defining
class, e.g. ``ASAPClient.batch`` or ``_SendMixin.send``). ``server.py`` is still
a single file and is measured directly.

Design rationale:
    AST inspection avoids importing ASAP dependencies when emitting/checking.

Exit codes:
    0 — current exports ⊆ baseline (no growth).
    1 — baseline violated or invalid invocation."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Final

_REPO_ROOT: Final = Path(__file__).resolve().parent.parent
_BASELINE_REL_PATH: Final = Path("scripts/_transport_baseline_v2.5.1.json")
# Each entry is either a single-file module (``server.py``) or a package
# directory (``client/``) whose public surface is aggregated across its modules.
_TRANSPORT_REL_PATHS: Final[tuple[str, ...]] = (
    "src/asap/transport/server.py",
    "src/asap/transport/client",
)


def _is_public_symbol(name: str) -> bool:
    """Return True if this AST-defined callable should count toward the frozen surface."""
    return not name.startswith("_")


def _symbols_from_class_body(class_node: ast.ClassDef, prefix: str) -> set[str]:
    """Collect ``Prefix.method`` symbols from class body (recursive for nested classes)."""
    found: set[str] = set()
    for item in class_node.body:
        if isinstance(item, ast.ClassDef):
            nested_prefix = f"{prefix}.{item.name}"
            found |= _symbols_from_class_body(item, nested_prefix)
        elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _is_public_symbol(item.name):
                found.add(f"{prefix}.{item.name}")
    return found


def extract_public_symbols(py_path: Path) -> list[str]:
    """Parse *py_path* and list public module-level functions plus class methods."""
    source = py_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    symbols: set[str] = set()

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _is_public_symbol(node.name):
                symbols.add(node.name)
        elif isinstance(node, ast.ClassDef):
            symbols |= _symbols_from_class_body(node, node.name)

    return sorted(symbols)


def extract_package_symbols(pkg_dir: Path) -> list[str]:
    """Aggregate public symbols across every ``*.py`` module in package *pkg_dir*.

    Methods are named by their defining class (``ClassName.method``), so a method
    moved into a mixin during decomposition (e.g. ``_SendMixin.send``) is tracked
    at its definition site. The union across modules is the package's public
    surface that D4 freezes.
    """
    symbols: set[str] = set()
    for py_path in sorted(pkg_dir.rglob("*.py")):
        symbols.update(extract_public_symbols(py_path))
    return sorted(symbols)


def extract_surface_symbols(rel_path: Path) -> list[str]:
    """Extract frozen surface symbols for a file module or a package directory."""
    if rel_path.is_dir():
        return extract_package_symbols(rel_path)
    return extract_public_symbols(rel_path)


def emit_baseline(repo_root: Path) -> dict[str, object]:
    """Build baseline payload with sorted symbol lists."""
    files_payload: dict[str, list[str]] = {}
    for rel in _TRANSPORT_REL_PATHS:
        abs_path = repo_root / rel
        if not abs_path.exists():
            msg = f"Expected transport module/package missing: {rel}"
            raise FileNotFoundError(msg)
        files_payload[rel] = extract_surface_symbols(abs_path)

    return {
        "_meta": {
            "description": (
                "Frozen public callable surface for transport surface lint "
                "(see docs/maintainers/transport-evolution.md)."
            ),
            "frozen_at_release": "v2.5.1",
        },
        "files": files_payload,
    }


def load_baseline(path: Path) -> dict[str, list[str]]:
    """Load and validate baseline JSON; return the ``files`` mapping."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Baseline root must be a JSON object")
    files_obj = raw.get("files")
    if not isinstance(files_obj, dict):
        raise ValueError("Baseline must contain a 'files' object")

    files_payload: dict[str, list[str]] = {}
    for key, value in files_obj.items():
        if key not in _TRANSPORT_REL_PATHS:
            raise ValueError(f"Unexpected baseline key {key!r}")
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            raise ValueError(f"Baseline entry for {key!r} must be a list of strings")
        files_payload[str(key)] = list(value)

    expected = set(_TRANSPORT_REL_PATHS)
    if set(files_payload.keys()) != expected:
        missing = expected - set(files_payload.keys())
        raise ValueError(f"Baseline 'files' missing entries: {sorted(missing)}")

    return files_payload


def check_no_growth(repo_root: Path, baseline_path: Path) -> list[str]:
    """Return human-readable errors (empty list means success)."""
    errors: list[str] = []
    try:
        baseline_files = load_baseline(baseline_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"Cannot load baseline {baseline_path}: {exc}"]

    for rel in _TRANSPORT_REL_PATHS:
        abs_path = repo_root / rel
        if not abs_path.exists():
            errors.append(f"Missing transport module/package {rel}")
            continue

        current = set(extract_surface_symbols(abs_path))
        allowed = set(baseline_files[rel])
        added = sorted(current - allowed)
        if added:
            joined = ", ".join(added)
            errors.append(
                f"D4 violation: new public symbols in {rel} "
                f"(move routes/helpers to a dedicated module): {joined}"
            )

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--emit-baseline",
        action="store_true",
        help=f"Print baseline JSON to stdout (redirect to {_BASELINE_REL_PATH.as_posix()}).",
    )
    parser.add_argument(
        "--baseline-path",
        type=Path,
        default=None,
        help=f"Override baseline JSON path (default: repo / {_BASELINE_REL_PATH.as_posix()}).",
    )
    args = parser.parse_args(argv)

    baseline_default = _REPO_ROOT / _BASELINE_REL_PATH
    baseline_path = args.baseline_path if args.baseline_path is not None else baseline_default

    if args.emit_baseline:
        try:
            payload = emit_baseline(_REPO_ROOT)
        except FileNotFoundError as exc:
            print(exc, file=sys.stderr)
            return 1
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    errors = check_no_growth(_REPO_ROOT, baseline_path.resolve())
    if errors:
        for line in errors:
            print(line, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
