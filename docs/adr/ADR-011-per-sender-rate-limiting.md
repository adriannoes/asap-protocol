# ADR-011: Per-Sender Rate Limiting

## Context and Problem Statement

ASAP agents must protect against denial-of-service and abusive clients. Rate limiting should be applied per sender (agent URN or fallback to client IP) to allow fair multi-tenant usage.

## Decision Drivers

* Protect server from overload
* Fair usage across multiple clients
* Per-sender isolation (one abusive client doesn't affect others)
* Configurable limits (env var or create_app param)

## Considered Options

* No rate limiting
* Global rate limit (all requests)
* Per-IP rate limit
* Per-sender (envelope.sender) rate limit with IP fallback

## Decision Outcome

Chosen option: "Per-sender rate limit with IP fallback", because envelope.sender identifies the agent; when envelope is not yet parsed, fallback to client IP. Default: 10/second;100/minute per sender. Configurable via ASAP_RATE_LIMIT or create_app(rate_limit=...).

### Consequences

* Good, because per-sender fairness; one client cannot starve others
* Good, because slowapi integration; supports Redis for multi-instance
* Bad, because IP fallback can be spoofed (use behind trusted proxy)
* Neutral, because memory storage is per-process; Redis needed for shared limits

### Confirmation

Rate limiting in `asap.transport.middleware`. Key: sender from envelope or client IP. See [Security Guide](../security.md#rate-limiting).

## Pros and Cons of the Options

### Global rate limit

* Good, because simple
* Bad, because one client can starve others

### Per-sender with IP fallback

* Good, because fairness; identifies agent when available
* Good, because fallback for unauthenticated requests
* Bad, because IP can be spoofed without proxy

## More Information

* [Security Guide](../security.md#rate-limiting)
* slowapi integration in middleware
* ASAP_RATE_LIMIT env var; format: "10/second;100/minute"
