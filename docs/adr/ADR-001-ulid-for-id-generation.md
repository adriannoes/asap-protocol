# ADR-001: ULID for ID Generation

## Context and Problem Statement

ASAP agents need unique identifiers for envelopes, tasks, conversations, and snapshots. These IDs must be globally unique, sortable for indexing/logging, and URL-safe for transport.

## Decision Drivers

* Need globally unique IDs across distributed agents
* Sortability by creation time simplifies indexing and debugging
* URL-safe encoding for JSON-RPC and HTTP
* Minimal dependencies and simple API

## Considered Options

* UUID v4
* UUID v7 (time-ordered)
* ULID
* Snowflake-style IDs (Twitter, Discord)

## Decision Outcome

Chosen option: "ULID", because it provides lexicographic sortability, 128-bit uniqueness, Crockford's Base32 encoding (URL-safe), and wide library support (e.g., python-ulid).

### Consequences

* Good, because IDs are sortable by creation time for logging and indexing
* Good, because 26-character string is compact and human-readable
* Good, because monotonic within same millisecond for ordering
* Bad, because ULID is less known than UUID; requires documentation

### Confirmation

All IDs in `asap.models.ids.generate_id()` return ULID strings. Tests verify format and sortability.

## Pros and Cons of the Options

### UUID v4

* Good, because universally recognized
* Bad, because random; no sortability by time
* Bad, because hyphenated format less compact

### UUID v7

* Good, because time-ordered
* Bad, because newer; fewer implementations at decision time

### ULID

* Good, because lexicographically sortable
* Good, because Crockford Base32 (no ambiguous chars)
* Good, because python-ulid is mature
* Neutral, because 26 chars vs UUID's 36

## More Information

* [ULID specification](https://github.com/ulid/spec)
* Implementation: `src/asap/models/ids.py`
* `extract_timestamp(ulid)` for debugging/analytics
