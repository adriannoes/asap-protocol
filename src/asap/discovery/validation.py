"""Manifest validation for discovered ASAP agents.

Validates schema, version compatibility, and capability/skill matching
to prevent runtime errors from malformed or incompatible manifests.
"""

from __future__ import annotations

from packaging.version import InvalidVersion, Version
from pydantic import ValidationError

from asap.models.constants import ASAP_PROTOCOL_VERSION
from asap.models.entities import Manifest


class ManifestValidationError(Exception):
    """Raised when a discovered manifest fails validation.

    Attributes:
        message: Human-readable description of the validation failure.
        field: Optional field or constraint that failed (e.g. "capabilities.asap_version").
    """

    def __init__(self, message: str, field: str | None = None) -> None:
        """Initialize validation error.

        Args:
            message: Error description.
            field: Optional field or constraint that failed.
        """
        super().__init__(message)
        self.message = message
        self.field = field


def validate_manifest_schema(data: dict[str, object]) -> Manifest:
    """Validate raw manifest data and return a Manifest instance.

    Ensures required fields are present and types are correct.
    Pydantic performs schema validation; this wraps ValidationError
    into ManifestValidationError with a clear message.

    Args:
        data: Raw dict (e.g. from JSON response).

    Returns:
        Validated Manifest instance.

    Raises:
        ManifestValidationError: If schema is invalid (missing required
            fields, wrong types, or invalid values).
    """
    try:
        return Manifest.model_validate(data)
    except ValidationError as e:
        raise ManifestValidationError(
            f"Invalid manifest schema: {e!s}",
            field="schema",
        ) from e


def check_version_compatibility(
    manifest: Manifest,
    min_asap_version: str | None = None,
) -> None:
    """Check that the manifest's ASAP protocol version is compatible.

    Args:
        manifest: Validated manifest.
        min_asap_version: Minimum required ASAP version (e.g. "0.1").
            Defaults to ASAP_PROTOCOL_VERSION.

    Raises:
        ManifestValidationError: If asap_version is missing or lower than
            the minimum required version.
    """
    required = min_asap_version if min_asap_version is not None else ASAP_PROTOCOL_VERSION
    raw = manifest.capabilities.asap_version
    try:
        agent_ver = Version(raw)
        min_ver = Version(required)
        if agent_ver < min_ver:
            raise ManifestValidationError(
                f"Agent ASAP version '{raw}' is older than required '{required}'.",
                field="capabilities.asap_version",
            )
    except InvalidVersion as e:
        raise ManifestValidationError(
            f"Invalid ASAP version in manifest: '{raw}'. {e}",
            field="capabilities.asap_version",
        ) from e


def manifest_supports_skill(manifest: Manifest, skill_id: str) -> bool:
    """Return whether the agent declares support for the given skill.

    Args:
        manifest: Validated manifest.
        skill_id: Skill identifier (e.g. "web_research").

    Returns:
        True if the manifest's capabilities list a skill with the given id.
    """
    return any(s.id == skill_id for s in manifest.capabilities.skills)


def require_skill(manifest: Manifest, skill_id: str) -> None:
    """Require that the manifest declares the given skill; otherwise raise.

    Args:
        manifest: Validated manifest.
        skill_id: Required skill identifier.

    Raises:
        ManifestValidationError: If the agent does not list the skill.
    """
    if not manifest_supports_skill(manifest, skill_id):
        available = [s.id for s in manifest.capabilities.skills]
        raise ManifestValidationError(
            f"Agent does not support required skill '{skill_id}'. "
            f"Available skills: {available or 'none'}.",
            field="capabilities.skills",
        )
