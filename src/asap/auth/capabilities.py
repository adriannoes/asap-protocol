"""Capability definitions, grants, constraint validation, and registry."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from asap.models.base import ASAPBaseModel

GrantStatus = Literal["active", "pending", "denied"]


class CapabilityDefinition(ASAPBaseModel):
    """Registered capability (name, schemas, optional location URI)."""

    name: str
    description: str
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    location: str | None = None


class CapabilityGrant(ASAPBaseModel):
    """Grant of one capability to an agent (status, optional constraints and expiry)."""

    capability: str
    status: GrantStatus = "pending"
    constraints: dict[str, Any] | None = None
    granted_by: str | None = None
    reason: str | None = None
    expires_at: datetime | None = None


# ---------------------------------------------------------------------------
# Constraint operators & validation
# ---------------------------------------------------------------------------

OPERATOR_KEYS = frozenset({"max", "min", "in", "not_in"})


@dataclass(frozen=True)
class ConstraintViolation:
    """Describes a single constraint check failure."""

    field: str
    operator: str
    expected: Any
    actual: Any
    message: str


def _check_operator(
    field: str, operator: str, expected: Any, actual: Any
) -> ConstraintViolation | None:
    """Return a violation if *actual* fails the *operator* check, else None."""
    if operator == "max":
        if not isinstance(actual, (int, float)):
            return ConstraintViolation(
                field,
                operator,
                expected,
                actual,
                f"{field}: expected a number, got {type(actual).__name__}",
            )
        if actual > expected:
            return ConstraintViolation(
                field,
                operator,
                expected,
                actual,
                f"{field}: {actual} exceeds maximum {expected}",
            )
    elif operator == "min":
        if not isinstance(actual, (int, float)):
            return ConstraintViolation(
                field,
                operator,
                expected,
                actual,
                f"{field}: expected a number, got {type(actual).__name__}",
            )
        if actual < expected:
            return ConstraintViolation(
                field,
                operator,
                expected,
                actual,
                f"{field}: {actual} is below minimum {expected}",
            )
    elif operator == "in":
        if actual not in expected:
            return ConstraintViolation(
                field,
                operator,
                expected,
                actual,
                f"{field}: {actual!r} not in allowed values {expected!r}",
            )
    elif operator == "not_in":
        if actual in expected:
            return ConstraintViolation(
                field,
                operator,
                expected,
                actual,
                f"{field}: {actual!r} is in forbidden values {expected!r}",
            )
    return None


def validate_constraints(
    constraints: dict[str, Any], arguments: dict[str, Any]
) -> list[ConstraintViolation]:
    """Validate *arguments* against *constraints*, returning all violations.

    Constraint values may be:
    - A plain value → exact-match check.
    - A ``dict`` whose keys are operator names (``max``, ``min``, ``in``,
      ``not_in``) → each operator is evaluated independently, allowing
      multiple operators per field.
    """
    violations: list[ConstraintViolation] = []
    for field, spec in constraints.items():
        actual = arguments.get(field)
        if actual is None:
            violations.append(
                ConstraintViolation(
                    field,
                    "required",
                    spec,
                    None,
                    f"{field}: missing required argument",
                )
            )
            continue

        if isinstance(spec, dict) and OPERATOR_KEYS & spec.keys():
            for op, expected in spec.items():
                if op not in OPERATOR_KEYS:
                    continue
                v = _check_operator(field, op, expected, actual)
                if v is not None:
                    violations.append(v)
        else:
            if actual != spec:
                violations.append(
                    ConstraintViolation(
                        field,
                        "eq",
                        spec,
                        actual,
                        f"{field}: expected {spec!r}, got {actual!r}",
                    )
                )
    return violations


# ---------------------------------------------------------------------------
# Capability registry — server-side capability management
# ---------------------------------------------------------------------------


@dataclass
class GrantCheckResult:
    """Result of :meth:`CapabilityRegistry.check_grant`."""

    allowed: bool
    violations: list[ConstraintViolation]
    grant: CapabilityGrant | None = None


class CapabilityRegistry:
    """In-memory definitions and per-agent grants (single-process; not shared across workers)."""

    def __init__(self) -> None:
        self._definitions: dict[str, CapabilityDefinition] = {}
        self._grants: dict[str, dict[str, CapabilityGrant]] = {}

    # -- Definitions --------------------------------------------------------

    def register(self, definition: CapabilityDefinition) -> None:
        """Register (or replace) a capability definition."""
        self._definitions[definition.name] = definition

    def list_capabilities(self) -> list[CapabilityDefinition]:
        """Return all registered capability definitions."""
        return list(self._definitions.values())

    def describe(self, name: str) -> CapabilityDefinition | None:
        """Return the full definition for *name*, or ``None``."""
        return self._definitions.get(name)

    # -- Grants -------------------------------------------------------------

    def grant(
        self,
        agent_id: str,
        capability: str,
        *,
        constraints: dict[str, Any] | None = None,
        granted_by: str | None = None,
        status: GrantStatus = "active",
        reason: str | None = None,
        expires_at: datetime | None = None,
    ) -> CapabilityGrant:
        """Issue or update a grant for *agent_id*."""
        g = CapabilityGrant(
            capability=capability,
            status=status,
            constraints=constraints,
            granted_by=granted_by,
            reason=reason,
            expires_at=expires_at,
        )
        self._grants.setdefault(agent_id, {})[capability] = g
        return g

    def get_grants(self, agent_id: str) -> list[CapabilityGrant]:
        """Return all grants for *agent_id*."""
        return list(self._grants.get(agent_id, {}).values())

    def check_grant(
        self,
        agent_id: str,
        capability: str,
        arguments: dict[str, Any] | None = None,
    ) -> GrantCheckResult:
        """Return whether *agent_id* may invoke *capability* with *arguments*."""
        agent_grants = self._grants.get(agent_id, {})
        g = agent_grants.get(capability)

        if g is None:
            return GrantCheckResult(allowed=False, violations=[], grant=None)

        if g.status != "active":
            return GrantCheckResult(allowed=False, violations=[], grant=g)

        if g.expires_at is not None and datetime.now(timezone.utc) > g.expires_at:
            return GrantCheckResult(allowed=False, violations=[], grant=g)

        if g.constraints and arguments is not None:
            violations = validate_constraints(g.constraints, arguments)
            if violations:
                return GrantCheckResult(allowed=False, violations=violations, grant=g)

        return GrantCheckResult(allowed=True, violations=[], grant=g)


# ---------------------------------------------------------------------------
# OAuth2 scope → capability mapping (backward compatibility)
# ---------------------------------------------------------------------------

# Scope constants (mirrored from asap.auth.scopes to avoid circular import)
_SCOPE_READ = "asap:read"
_SCOPE_EXECUTE = "asap:execute"
_SCOPE_ADMIN = "asap:admin"


def map_scopes_to_capabilities(
    scopes: list[str],
    registry: CapabilityRegistry,
) -> list[CapabilityGrant]:
    """Map OAuth2 scopes to synthetic active grants (admin = all caps; read/execute by name heuristics)."""
    all_caps = registry.list_capabilities()
    granted_names: set[str] = set()

    if _SCOPE_ADMIN in scopes:
        granted_names = {c.name for c in all_caps}
    else:
        if _SCOPE_READ in scopes:
            for c in all_caps:
                lower = c.name.lower()
                if any(kw in lower for kw in ("read", "list", "describe")):
                    granted_names.add(c.name)
        if _SCOPE_EXECUTE in scopes:
            for c in all_caps:
                lower = c.name.lower()
                if any(kw in lower for kw in ("execute", "write", "invoke")):
                    granted_names.add(c.name)

    return [CapabilityGrant(capability=name, status="active") for name in sorted(granted_names)]
