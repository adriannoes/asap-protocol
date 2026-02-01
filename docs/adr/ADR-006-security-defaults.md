# ADR-006: Security Defaults

## Context and Problem Statement

ASAP agents may handle sensitive data. Defaults should favor security over convenience to avoid accidental exposure in production.

## Decision Drivers

* Secure by default
* Minimize misconfiguration risk
* Support development workflows (localhost exceptions)

## Considered Options

* Permissive defaults (opt-in security)
* Secure defaults (opt-out for development)
* No defaults (explicit configuration required)

## Decision Outcome

Chosen option: "Secure defaults", because rate limiting, request size limits, timestamp validation, and HTTPS enforcement are enabled by default. Development uses localhost exceptions (e.g., HTTP allowed for localhost).

### Consequences

* Good, because production deployments are secure without extra config
* Good, because explicit opt-out for development (e.g., `require_https=False`)
* Bad, because developers must know how to relax for local testing
* Neutral, because authentication is opt-in (manifest.auth)

### Confirmation

Server defaults: rate_limit, max_request_size, timestamp validation. Client: require_https=True, rejects HTTP for non-localhost. See [Security Guide](../security.md).

## Pros and Cons of the Options

### Permissive defaults

* Good, because easier to get started
* Bad, because production misconfiguration risk

### Secure defaults

* Good, because production-safe
* Good, because clear exceptions for localhost
* Bad, because developers must read docs for local setup

## More Information

* [Security Guide](../security.md)
* `asap.models.constants` (MAX_ENVELOPE_AGE_SECONDS, etc.)
* `ASAPClient(require_https=True)` default
