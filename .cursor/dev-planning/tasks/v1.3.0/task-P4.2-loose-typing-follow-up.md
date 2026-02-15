# Follow-up Task: Tighten dict[str, Any] Typing in Models (P4.2)

> **Source**: Security Remediation Pre-v1.3.0 ([plan-security-remediation-pre-v1.3.md](../v1.2.1/plan-security-remediation-pre-v1.3.md))
> **Phase**: P4.2 Loose Typing (Optional / Deferred)
> **Backlog**: v1.3.0 or later

## Context

The security review suggests tightening validation for `dict[str, Any]` in Pydantic models. Using `TypedDict` or `pydantic.Json` could improve validation and reduce injection risk.

## Audit Results (src/asap/models/)

| File | Fields / Usages |
|------|-----------------|
| **payloads.py** | `input`, `config`, `result`, `final_state`, `metrics`, `progress`, `input_request`, `arguments`, `mcp_context`, `content` |
| **entities.py** | `input_schema`, `output_schema`, `oauth2`, `metadata`, `progress`, `data` |
| **envelope.py** | `payload`, `extensions` |
| **parts.py** | `data`, `variables` |

## Recommendation

- **Priority**: Low (refactor; no immediate security impact).
- **Approach**: Replace `dict[str, Any]` with `TypedDict` or `pydantic.Json` where schema is known.
- **Consider**: `payload` in Envelope is polymorphic (payload_type determines shape); may need `Union[TaskRequest, TaskResponse, ...]` or discriminated union.
- **Defer**: Until v1.3 or v2.0 when model stability allows.

## Acceptance Criteria (when implemented)

- [ ] Audit each `dict[str, Any]` for replaceability
- [ ] Introduce TypedDict or pydantic.Json for schemas with known structure
- [ ] All tests pass; no breaking changes to API
- [ ] Document any remaining `dict[str, Any]` with rationale
