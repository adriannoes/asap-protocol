"""`asap repl` — interactive REPL with ASAP models for testing payloads."""

from __future__ import annotations

import code
from typing import Any

import typer

from asap.models import Envelope, TaskRequest, generate_id
from asap.models.entities import Capability, Endpoint, Manifest, Skill

REPL_BANNER = (
    "ASAP Protocol REPL - test payloads interactively.\n"
    "  Envelope, TaskRequest, Manifest, generate_id, sample_envelope() available.\n"
    "  Type exit() or Ctrl-D to quit."
)


def _sample_envelope() -> Envelope:
    """Return a sample task.request envelope for quick REPL testing."""
    return Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:repl-sender",
        recipient="urn:asap:agent:repl-recipient",
        payload_type="task.request",
        payload=TaskRequest(
            conversation_id=f"conv-{generate_id()}",
            skill_id="echo",
            input={"message": "hello from REPL"},
        ).model_dump(),
    )


def _repl_namespace() -> dict[str, Any]:
    """Build namespace for the ASAP REPL with models and a sample envelope helper."""
    return {
        "Envelope": Envelope,
        "TaskRequest": TaskRequest,
        "Manifest": Manifest,
        "Capability": Capability,
        "Endpoint": Endpoint,
        "Skill": Skill,
        "generate_id": generate_id,
        "sample_envelope": _sample_envelope,
    }


def register_repl_command(root: typer.Typer) -> None:
    """Register the ``repl`` command on *root*."""

    @root.command("repl")
    def repl() -> None:
        """Start an interactive REPL with ASAP models for testing payloads.

        Provides Envelope, TaskRequest, Manifest, generate_id, and sample_envelope()
        in the namespace. Use Python's code module for the interactive loop.
        """
        code.interact(banner=REPL_BANNER, local=_repl_namespace())
