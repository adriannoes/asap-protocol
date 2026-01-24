"""ASAP Protocol performance benchmarks.

This package contains performance benchmarks for measuring latency
and throughput of ASAP protocol operations.

Benchmark categories:
- Model serialization/deserialization
- Envelope creation and validation
- JSON-RPC request/response handling
- HTTP transport round-trip times

Run benchmarks with:
    uv run pytest benchmarks/ --benchmark-only
"""
