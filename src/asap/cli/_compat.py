"""Legacy public-symbol re-exports kept for backward compatibility.

These names historically lived on ``asap.cli`` (inline in ``__init__.py``
before the v2.5.1 S3 cli split). The root ``asap.cli`` package no longer
re-exports them (issue #242); use this module or the canonical paths below.

**Deprecation window:** scheduled for removal in **v2.6.0** (same timeline as
other v2.5.1 transport/MCP shims — see ``docs/migration.md``).

Canonical import paths for new code:

- ``DEFAULT_SCHEMAS_DIR`` → ``asap.cli.schemas``
- ``export_all_schemas`` → ``asap.schemas``
- ``_repl_namespace`` → ``asap.cli.repl``
"""

from __future__ import annotations

from asap.cli.repl import _repl_namespace
from asap.cli.schemas import DEFAULT_SCHEMAS_DIR
from asap.schemas import export_all_schemas

__all__ = ["DEFAULT_SCHEMAS_DIR", "export_all_schemas", "_repl_namespace"]
