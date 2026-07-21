"""Integration tests for transport layer with HTTP/FastAPI.

Tests in this directory use FastAPI TestClient and test feature integration
(e.g., rate limiting, size validation, thread pool bounds).

Fixtures in this package use isolated_limiter_factory or replace_global_limiter
to prevent rate limiting interference.
"""
