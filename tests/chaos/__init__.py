"""Chaos engineering tests for ASAP protocol.

This package contains tests that simulate infrastructure failures to verify
the resilience and graceful degradation of the ASAP protocol implementation.

Chaos tests include:
- Network partition simulation
- Random server crashes
- Message loss and duplication
- Clock skew testing

These tests help ensure that:
1. The client properly retries failed requests
2. Circuit breakers open under sustained failures
3. The system degrades gracefully under adverse conditions
4. Error messages are clear and actionable
"""
