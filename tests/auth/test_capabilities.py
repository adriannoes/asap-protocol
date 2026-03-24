"""Tests for capability models, constraint operators, and the registry."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, get_args

import pytest
from pydantic import ValidationError

from asap.auth.capabilities import (
    CapabilityDefinition,
    CapabilityGrant,
    CapabilityRegistry,
    ConstraintViolation,
    GrantStatus,
    map_scopes_to_capabilities,
    validate_constraints,
)


# ---------------------------------------------------------------------------
# CapabilityDefinition
# ---------------------------------------------------------------------------


class TestCapabilityDefinition:
    def test_full_fields(self) -> None:
        cap = CapabilityDefinition(
            name="file:read",
            description="Read a file",
            input_schema={"type": "object"},
            output_schema={"type": "string"},
            location="/files",
        )
        assert cap.name == "file:read"
        assert cap.input_schema == {"type": "object"}
        assert cap.location == "/files"

    def test_minimal_fields(self) -> None:
        cap = CapabilityDefinition(name="ping", description="Health check")
        assert cap.input_schema is None
        assert cap.output_schema is None
        assert cap.location is None

    def test_frozen(self) -> None:
        cap = CapabilityDefinition(name="x", description="y")
        with pytest.raises(ValidationError):
            cap.name = "changed"

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            CapabilityDefinition(name="x", description="y", unknown="z")


# ---------------------------------------------------------------------------
# CapabilityGrant
# ---------------------------------------------------------------------------


class TestCapabilityGrant:
    def test_active_grant(self) -> None:
        g = CapabilityGrant(
            capability="file:read",
            status="active",
            constraints={"path": {"in": ["/tmp"]}},
            granted_by="host:abc",
        )
        assert g.status == "active"
        assert g.constraints is not None

    def test_default_pending(self) -> None:
        g = CapabilityGrant(capability="file:write")
        assert g.status == "pending"

    def test_denied_with_reason(self) -> None:
        g = CapabilityGrant(capability="admin:delete", status="denied", reason="Not allowed")
        assert g.reason == "Not allowed"

    def test_expires_at(self) -> None:
        exp = datetime(2030, 6, 1, tzinfo=timezone.utc)
        g = CapabilityGrant(capability="x", expires_at=exp)
        assert g.expires_at == exp

    def test_all_grant_statuses_covered(self) -> None:
        for status in get_args(GrantStatus):
            g = CapabilityGrant(capability="test", status=status)
            assert g.status == status

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CapabilityGrant(capability="x", status="bogus")

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            CapabilityGrant(capability="x", unknown="y")


# ---------------------------------------------------------------------------
# Constraint operators
# ---------------------------------------------------------------------------


class TestConstraintOperators:
    """Each operator tested independently, then combined."""

    # -- max ----------------------------------------------------------------

    def test_max_pass(self) -> None:
        assert validate_constraints({"n": {"max": 10}}, {"n": 10}) == []

    def test_max_fail(self) -> None:
        vs = validate_constraints({"n": {"max": 10}}, {"n": 11})
        assert len(vs) == 1
        assert vs[0].operator == "max"

    def test_max_type_error(self) -> None:
        vs = validate_constraints({"n": {"max": 10}}, {"n": "text"})
        assert len(vs) == 1
        assert "number" in vs[0].message

    # -- min ----------------------------------------------------------------

    def test_min_pass(self) -> None:
        assert validate_constraints({"n": {"min": 5}}, {"n": 5}) == []

    def test_min_fail(self) -> None:
        vs = validate_constraints({"n": {"min": 5}}, {"n": 4})
        assert len(vs) == 1
        assert vs[0].operator == "min"

    def test_min_type_error(self) -> None:
        vs = validate_constraints({"n": {"min": 5}}, {"n": "text"})
        assert len(vs) == 1
        assert "number" in vs[0].message

    # -- in -----------------------------------------------------------------

    def test_in_pass(self) -> None:
        assert validate_constraints({"r": {"in": ["a", "b"]}}, {"r": "a"}) == []

    def test_in_fail(self) -> None:
        vs = validate_constraints({"r": {"in": ["a", "b"]}}, {"r": "c"})
        assert len(vs) == 1
        assert vs[0].operator == "in"

    # -- not_in -------------------------------------------------------------

    def test_not_in_pass(self) -> None:
        assert validate_constraints({"e": {"not_in": ["prod"]}}, {"e": "dev"}) == []

    def test_not_in_fail(self) -> None:
        vs = validate_constraints({"e": {"not_in": ["prod"]}}, {"e": "prod"})
        assert len(vs) == 1
        assert vs[0].operator == "not_in"

    # -- exact match --------------------------------------------------------

    def test_exact_pass(self) -> None:
        assert validate_constraints({"mode": "read"}, {"mode": "read"}) == []

    def test_exact_fail(self) -> None:
        vs = validate_constraints({"mode": "read"}, {"mode": "write"})
        assert len(vs) == 1
        assert vs[0].operator == "eq"

    # -- missing field ------------------------------------------------------

    def test_missing_field(self) -> None:
        vs = validate_constraints({"x": {"max": 5}}, {})
        assert len(vs) == 1
        assert vs[0].operator == "required"

    # -- combined operators -------------------------------------------------

    def test_combined_both_pass(self) -> None:
        assert validate_constraints({"n": {"min": 1, "max": 10}}, {"n": 5}) == []

    def test_combined_max_fail(self) -> None:
        vs = validate_constraints({"n": {"min": 1, "max": 10}}, {"n": 15})
        assert len(vs) == 1
        assert vs[0].operator == "max"

    def test_combined_min_fail(self) -> None:
        vs = validate_constraints({"n": {"min": 1, "max": 10}}, {"n": 0})
        assert len(vs) == 1
        assert vs[0].operator == "min"

    def test_combined_both_fail(self) -> None:
        """Value is a non-number, so both min and max produce type errors."""
        vs = validate_constraints({"n": {"min": 1, "max": 10}}, {"n": "bad"})
        assert len(vs) == 2

    def test_multiple_fields(self) -> None:
        constraints: dict[str, Any] = {
            "count": {"min": 1, "max": 100},
            "env": {"in": ["dev", "staging"]},
        }
        vs = validate_constraints(constraints, {"count": 200, "env": "prod"})
        assert len(vs) == 2


# ---------------------------------------------------------------------------
# ConstraintViolation structure
# ---------------------------------------------------------------------------


class TestConstraintViolation:
    def test_fields(self) -> None:
        v = ConstraintViolation("f", "max", 10, 20, "f: 20 exceeds maximum 10")
        assert v.field == "f"
        assert v.operator == "max"
        assert v.expected == 10
        assert v.actual == 20
        assert "exceeds" in v.message

    def test_frozen(self) -> None:
        v = ConstraintViolation("f", "eq", 1, 2, "msg")
        with pytest.raises(AttributeError):
            v.field = "changed"


# ---------------------------------------------------------------------------
# CapabilityRegistry
# ---------------------------------------------------------------------------


class TestCapabilityRegistry:
    @pytest.fixture()
    def registry(self) -> CapabilityRegistry:
        reg = CapabilityRegistry()
        reg.register(CapabilityDefinition(name="file:read", description="Read"))
        reg.register(CapabilityDefinition(name="file:write", description="Write"))
        return reg

    # -- definitions --------------------------------------------------------

    def test_list(self, registry: CapabilityRegistry) -> None:
        caps = registry.list_capabilities()
        assert len(caps) == 2

    def test_list_with_agent_id(self, registry: CapabilityRegistry) -> None:
        """agent_id param doesn't filter definitions (filtering is endpoint-level)."""
        caps = registry.list_capabilities(agent_id="agent-1")
        assert len(caps) == 2

    def test_describe_found(self, registry: CapabilityRegistry) -> None:
        d = registry.describe("file:read")
        assert d is not None
        assert d.name == "file:read"

    def test_describe_not_found(self, registry: CapabilityRegistry) -> None:
        assert registry.describe("nonexistent") is None

    # -- grants -------------------------------------------------------------

    def test_grant_and_get(self, registry: CapabilityRegistry) -> None:
        registry.grant("a1", "file:read")
        grants = registry.get_grants("a1")
        assert len(grants) == 1
        assert grants[0].capability == "file:read"
        assert grants[0].status == "active"

    def test_grant_replaces(self, registry: CapabilityRegistry) -> None:
        registry.grant("a1", "file:read", status="pending")
        registry.grant("a1", "file:read", status="active")
        grants = registry.get_grants("a1")
        assert len(grants) == 1
        assert grants[0].status == "active"

    def test_get_grants_unknown_agent(self, registry: CapabilityRegistry) -> None:
        assert registry.get_grants("unknown") == []

    # -- check_grant --------------------------------------------------------

    def test_check_grant_allowed(self, registry: CapabilityRegistry) -> None:
        registry.grant("a1", "file:read")
        r = registry.check_grant("a1", "file:read")
        assert r.allowed

    def test_check_grant_no_grant(self, registry: CapabilityRegistry) -> None:
        r = registry.check_grant("a1", "file:read")
        assert not r.allowed
        assert r.grant is None

    def test_check_grant_denied(self, registry: CapabilityRegistry) -> None:
        registry.grant("a1", "file:read", status="denied")
        r = registry.check_grant("a1", "file:read")
        assert not r.allowed
        assert r.grant is not None
        assert r.grant.status == "denied"

    def test_check_grant_pending(self, registry: CapabilityRegistry) -> None:
        registry.grant("a1", "file:read", status="pending")
        r = registry.check_grant("a1", "file:read")
        assert not r.allowed

    def test_check_grant_with_constraints_pass(self, registry: CapabilityRegistry) -> None:
        registry.grant("a1", "file:read", constraints={"path": {"in": ["/tmp", "/data"]}})
        r = registry.check_grant("a1", "file:read", {"path": "/tmp"})
        assert r.allowed
        assert r.violations == []

    def test_check_grant_with_constraints_violated(self, registry: CapabilityRegistry) -> None:
        registry.grant("a1", "file:read", constraints={"path": {"in": ["/tmp"]}})
        r = registry.check_grant("a1", "file:read", {"path": "/etc"})
        assert not r.allowed
        assert len(r.violations) == 1
        assert r.violations[0].operator == "in"

    def test_check_grant_expired(self, registry: CapabilityRegistry) -> None:
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        registry.grant("a1", "file:read", expires_at=past)
        r = registry.check_grant("a1", "file:read")
        assert not r.allowed

    def test_check_grant_not_expired(self, registry: CapabilityRegistry) -> None:
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        registry.grant("a1", "file:read", expires_at=future)
        r = registry.check_grant("a1", "file:read")
        assert r.allowed

    def test_check_grant_unknown_agent(self, registry: CapabilityRegistry) -> None:
        r = registry.check_grant("unknown", "file:read")
        assert not r.allowed
        assert r.grant is None


# ---------------------------------------------------------------------------
# map_scopes_to_capabilities
# ---------------------------------------------------------------------------


class TestMapScopesToCapabilities:
    @pytest.fixture()
    def registry(self) -> CapabilityRegistry:
        reg = CapabilityRegistry()
        reg.register(CapabilityDefinition(name="file:read", description="Read file"))
        reg.register(CapabilityDefinition(name="file:write", description="Write file"))
        reg.register(CapabilityDefinition(name="capability:list", description="List caps"))
        reg.register(CapabilityDefinition(name="task:execute", description="Exec task"))
        reg.register(CapabilityDefinition(name="capability:describe", description="Describe cap"))
        reg.register(CapabilityDefinition(name="task:invoke", description="Invoke"))
        reg.register(CapabilityDefinition(name="admin:config", description="Admin"))
        return reg

    def test_read_scope(self, registry: CapabilityRegistry) -> None:
        grants = map_scopes_to_capabilities(["asap:read"], registry)
        names = {g.capability for g in grants}
        assert "file:read" in names
        assert "capability:list" in names
        assert "capability:describe" in names
        assert "file:write" not in names
        assert all(g.status == "active" for g in grants)

    def test_execute_scope(self, registry: CapabilityRegistry) -> None:
        grants = map_scopes_to_capabilities(["asap:execute"], registry)
        names = {g.capability for g in grants}
        assert "file:write" in names
        assert "task:execute" in names
        assert "task:invoke" in names
        assert "file:read" not in names

    def test_admin_scope(self, registry: CapabilityRegistry) -> None:
        grants = map_scopes_to_capabilities(["asap:admin"], registry)
        assert len(grants) == 7

    def test_combined_scopes(self, registry: CapabilityRegistry) -> None:
        grants = map_scopes_to_capabilities(["asap:read", "asap:execute"], registry)
        names = {g.capability for g in grants}
        assert "file:read" in names
        assert "file:write" in names

    def test_empty_scopes(self, registry: CapabilityRegistry) -> None:
        grants = map_scopes_to_capabilities([], registry)
        assert grants == []

    def test_unknown_scope(self, registry: CapabilityRegistry) -> None:
        grants = map_scopes_to_capabilities(["custom:scope"], registry)
        assert grants == []

    def test_sorted_output(self, registry: CapabilityRegistry) -> None:
        grants = map_scopes_to_capabilities(["asap:admin"], registry)
        names = [g.capability for g in grants]
        assert names == sorted(names)
