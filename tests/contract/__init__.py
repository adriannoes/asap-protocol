"""Contract tests for ASAP protocol cross-version compatibility.

Contract tests verify that different protocol versions can communicate correctly:
- v0.1.0 client → v1.0.0 server
- v1.0.0 client → v0.1.0 server
- Schema evolution (forward and backward compatibility)

These tests ensure backward compatibility is maintained across versions.
"""
