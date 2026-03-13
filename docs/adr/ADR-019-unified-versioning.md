# ADR-019: Unified Versioning and Content Negotiation

## Context and Problem Statement

ASAP has two versioning decisions that partially conflict: ADR-016 (`docs/adr/`) specifies SemVer for the library + `asap_version` in the envelope + contract tests. Q6 (`decision-records/05-product-strategy.md`) proposes a Major.CalVer hybrid (e.g., `1.2025.01`). Additionally, there is no content negotiation mechanism — clients and servers cannot negotiate which protocol version to use, making backward compatibility fragile. As v2.2 introduces new features (streaming, batch, error taxonomy evolution), a formal versioning and negotiation strategy is critical.

## Decision Drivers

* Resolve the SemVer (ADR-016) vs Major.CalVer (Q6) conflict
* Enable backward compatibility via content negotiation
* Support agents running different protocol versions in the same ecosystem
* Contract tests (ADR-016) must continue to validate compatibility
* Minimize disruption to existing clients (no header = current version)

## Considered Options

* SemVer for everything (library = protocol version)
* Separate library version (SemVer) and protocol version (simple MAJOR.MINOR)
* Major.CalVer for protocol (Q6 proposal)
* No versioning header (rely on envelope `asap_version` field only)

## Decision Outcome

Chosen option: "Separate library version (SemVer) and protocol version (simple MAJOR.MINOR)", because the library version (PyPI package) follows standard SemVer for dependency management, while the protocol version uses a simple MAJOR.MINOR scheme (e.g., "2.1", "2.2") for wire-level negotiation. CalVer (Q6) is **not adopted** — it adds complexity without proportional benefit for a protocol standard. The `asap_version` field in the envelope continues to carry the protocol version.

### Version Mapping

| Library Version (SemVer) | Protocol Version | Notes |
|--------------------------|-----------------|-------|
| 1.0.0 - 1.4.x | 1.0 | Original protocol |
| 2.0.0 - 2.1.x | 2.1 | Marketplace era |
| 2.2.x | 2.2 | Protocol Hardening (streaming, batch, versioning) |

### Content Negotiation

1. Client sends `ASAP-Version: 2.2` header (or comma-separated list: `ASAP-Version: 2.2, 2.1`)
2. Server checks supported versions and selects the best match
3. Server responds with `ASAP-Version: 2.2` header confirming the negotiated version
4. If no header is sent, server assumes current version (backward compatible)
5. If no compatible version exists, server returns JSON-RPC error `-32000` (protocol version mismatch)

### Consequences

* Good, because clean separation: PyPI version for packages, protocol version for wire format
* Good, because `ASAP-Version` header enables graceful version negotiation
* Good, because backward compatible — no header = current version
* Good, because resolves Q6 (CalVer rejected in favor of simpler MAJOR.MINOR)
* Good, because contract tests (ADR-016) naturally extend to cover negotiation
* Bad, because two version numbers to track (library vs protocol)
* Bad, because header adds overhead to every request (minimal: ~20 bytes)

### Confirmation

`ASAP-Version` header in all HTTP requests/responses. Contract tests in `tests/contract/test_version_negotiation.py`. Manifest `supported_versions` field.

## Pros and Cons of the Options

### SemVer for everything

* Good, because single version number
* Bad, because library patches (e.g., bug fix 2.2.1 → 2.2.2) don't change protocol
* Bad, because version negotiation with 3 components is verbose

### Separate library + protocol versions

* Good, because each version serves its purpose
* Good, because protocol version is stable across patch releases
* Bad, because two numbers to track

### Major.CalVer (Q6)

* Good, because calendar context
* Bad, because unusual for protocols (HTTP uses 1.0, 1.1, 2, 3 — not CalVer)
* Bad, because version negotiation with dates is awkward
* Bad, because changes every release even if protocol is unchanged

### No versioning header

* Good, because simple
* Bad, because no negotiation — breaking changes break silently
* Bad, because `asap_version` in envelope body requires parsing before version check

## More Information

* ADR-016 (`docs/adr/`): SemVer + asap_version + contract tests (SUPERSEDED by this ADR for protocol versioning)
* Q6 (`decision-records/05-product-strategy.md`): Major.CalVer proposal (REJECTED by this ADR)
* `Envelope.asap_version` field: continues to carry protocol version in message body
* PRD v2.2: `prd-v2.2-protocol-hardening.md` §4.3
