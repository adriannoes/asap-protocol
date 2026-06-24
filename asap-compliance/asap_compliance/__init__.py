"""ASAP Compliance Harness - Protocol compliance testing suite.

Validates that ASAP implementations follow the protocol specification.
Third parties can use this package to certify their agents are ASAP-compliant.
"""

from asap_compliance.harness import (
    ComplianceConfig,
    HandshakeResult,
    McpAuthComplianceConfig,
    McpAuthResult,
    SchemaResult,
    SlaResult,
    StateResult,
    validate_handshake,
    validate_handshake_async,
    validate_mcp_auth,
    validate_mcp_auth_async,
    validate_schema,
    validate_sla,
    validate_sla_async,
    validate_state_machine,
    validate_state_machine_async,
)

__version__ = "1.2.0"

__all__ = [
    "ComplianceConfig",
    "HandshakeResult",
    "McpAuthComplianceConfig",
    "McpAuthResult",
    "SchemaResult",
    "SlaResult",
    "StateResult",
    "validate_handshake",
    "validate_handshake_async",
    "validate_mcp_auth",
    "validate_mcp_auth_async",
    "validate_schema",
    "validate_sla",
    "validate_sla_async",
    "validate_state_machine",
    "validate_state_machine_async",
    "__version__",
]
