# Tasks: A2H Protocol Integration (v2.2.0)

> **PRD**: `prd-a2h-integration.md`
> **Goal**: Enable ASAP agents to communicate with humans via A2H Gateways using a decoupled, protocol-agnostic HITL interface
> **Prerequisite**: v2.2.0 tech debt cleared (`tasks-v2.2.0-tech-debt.md`)

---

## Relevant Files

### Core HITL Protocol (decoupled from A2H)
- `src/asap/handlers/__init__.py` (create new) — New package for handler-level abstractions (HITL, etc.)
- `src/asap/handlers/hitl.py` (create new) — `HumanApprovalProvider` Protocol + `ApprovalResult` model
- `tests/handlers/__init__.py` (create new) — Test package init
- `tests/handlers/test_hitl.py` (create new) — Protocol conformance + model tests

### A2H Integration (models + client + provider)
- `src/asap/integrations/a2h.py` (create new) — Pydantic models, `A2HClient`, `A2HApprovalProvider`
- `src/asap/integrations/__init__.py` (modify existing) — Add lazy exports for A2H symbols
- `tests/integrations/test_a2h.py` (create new) — Unit tests with mocked gateway responses

### Example
- `src/asap/examples/a2h_approval.py` (create new) — E2E example: ASAP agent requests human approval via A2H
- `src/asap/examples/README.md` (modify existing) — Add A2H approval example to the examples table
- `tests/examples/test_a2h_approval.py` (create new) — Smoke test for the example module

### Documentation
- `AGENTS.md` (modify existing) — Add A2H to Framework Integrations list

### Notes

- Unit tests should be placed in `tests/` mirroring the `src/` structure.
- Use `PYTHONPATH=src uv run pytest tests/[path] -v` to run tests.
- The `handlers/` package is documented in `AGENTS.md` but does not exist yet — must be created with `__init__.py`.
- A2H integration uses only existing dependencies (`httpx`, `pydantic`) — **no changes** to `pyproject.toml`.
- Follow existing integration pattern from `src/asap/integrations/langchain.py` for lazy imports and `src/asap/integrations/openclaw.py` for client-style integrations.
- Examples follow the `src/asap/examples/<module>.py` pattern (run via `uv run python -m asap.examples.<module>`).
- Testing standards: `pytest-asyncio` with `asyncio_mode = "auto"`. All tests must have type annotations.

---

## Tasks

### Task 1.0: Create HITL Protocol and ApprovalResult model

**Goal**: Define a protocol-agnostic, async-only interface for human approval that any provider (A2H, Slack, email, custom) can implement.

**Context**: This is the decoupled core — it lives in `asap.handlers`, not `asap.integrations`. No A2H-specific code here. The `HumanApprovalProvider` is a Python `Protocol` (structural typing via `typing.Protocol`) so any class with the right method signature satisfies it without inheritance. `ApprovalResult` is a Pydantic v2 model for the human's decision.

**Trigger**: PRD approved, v2.2.0 tech debt cleared.
**Enables**: Task 4.0 (`A2HApprovalProvider` implements this Protocol). Any custom HITL provider.
**Depends on**: Nothing.

#### Sub-tasks

- [x] 1.1 Create `handlers` package with `__init__.py`
  - **File**: `src/asap/handlers/__init__.py` (create new)
  - **What**: Create the package with a module docstring and exports for `HumanApprovalProvider`, `ApprovalResult`, and `ApprovalDecision`. Use direct imports (not lazy) since these are core types with no external dependencies.
  - **Why**: The `handlers` package is documented in `AGENTS.md` as a top-level module but doesn't exist yet. It's the correct location for handler-level abstractions that aren't transport-specific.
  - **Pattern**: Follow `src/asap/auth/__init__.py` structure (direct exports of core types).
  - **Verify**: `python -c "from asap.handlers import HumanApprovalProvider, ApprovalResult"` succeeds (after 1.2 is done).

- [x] 1.2 Create `HumanApprovalProvider` Protocol and `ApprovalResult` model
  - **File**: `src/asap/handlers/hitl.py` (create new)
  - **What**: Create:
    - `ApprovalDecision` — `StrEnum` with values `APPROVE` and `DECLINE`.
    - `ApprovalResult` — Pydantic `BaseModel` with fields: `decision: ApprovalDecision`, `data: dict[str, Any] | None = None`, `evidence: dict[str, Any] | None = None`, `decided_at: datetime | None = None`, `interaction_id: str | None = None`. Use `ConfigDict(extra="forbid")`.
    - `HumanApprovalProvider` — `typing.Protocol` (decorated with `@runtime_checkable`) with single async method: `async def request_approval(self, *, context: str, principal_id: str, assurance_level: str = "LOW", timeout_seconds: float = 300.0) -> ApprovalResult`.
  - **Why**: Decouples HITL from any specific implementation. `Protocol` + `@runtime_checkable` allows `isinstance()` checks without inheritance. Async-only matches ASAP's async-first architecture (FastAPI, aiosqlite, httpx).
  - **Pattern**: Follow `typing.Protocol` pattern from `src/asap/state/stores/snapshot.py` (`SnapshotStore`).
  - **Verify**: `uv run mypy src/asap/handlers/hitl.py` passes with no errors.

- [x] 1.3 Create test package and write HITL Protocol tests
  - **File**: `tests/handlers/__init__.py` (create new), `tests/handlers/test_hitl.py` (create new)
  - **What**: Create `__init__.py` (empty) and test file with:
    - `test_approval_result_approve` — Create `ApprovalResult(decision=ApprovalDecision.APPROVE)`, verify serialization via `model_dump()`.
    - `test_approval_result_decline` — Create with `DECLINE`, verify `decision` field.
    - `test_approval_result_forbids_extra_fields` — Verify `ValidationError` raised when extra fields passed.
    - `test_approval_result_with_all_fields` — Create with all optional fields populated, verify round-trip via `model_validate(result.model_dump())`.
    - `test_protocol_conformance_with_mock` — Create a mock class with `async def request_approval(...)` matching the Protocol signature. Verify `isinstance(mock, HumanApprovalProvider)` is `True`.
    - `test_non_conforming_class_fails` — Create a class missing the method. Verify `isinstance()` is `False`.
  - **Why**: Validates that the Protocol is runtime-checkable and models serialize correctly. These tests must pass before Task 4.0 builds on top.
  - **Pattern**: Follow `tests/integrations/test_openclaw.py` structure (imports, fixtures, test naming).
  - **Verify**: `PYTHONPATH=src uv run pytest tests/handlers/test_hitl.py -v` — all tests pass.

- [ ] 1.4 Commit
  - **Command**: `git add src/asap/handlers/ tests/handlers/ && git commit -m "feat(handlers): add HumanApprovalProvider protocol and ApprovalResult model"`
  - **Scope**: `src/asap/handlers/__init__.py`, `src/asap/handlers/hitl.py`, `tests/handlers/__init__.py`, `tests/handlers/test_hitl.py`

**Acceptance Criteria**:
- [ ] `from asap.handlers import HumanApprovalProvider, ApprovalResult, ApprovalDecision` works.
- [ ] `ApprovalResult` uses `ConfigDict(extra="forbid")`.
- [ ] `HumanApprovalProvider` is `@runtime_checkable` and has async `request_approval()`.
- [ ] Any class implementing the correct async method signature satisfies `isinstance(..., HumanApprovalProvider)`.
- [ ] All tests in `tests/handlers/test_hitl.py` pass.
- [ ] `uv run mypy src/asap/handlers/` passes.

---

### Task 2.0: Create A2H Pydantic models

**Goal**: Define typed Pydantic v2 models for the A2H protocol — message envelope, responses, discovery, and supporting types.

**Context**: These models map directly to the [A2H OpenAPI spec](https://github.com/twilio-labs/Agent2Human/blob/main/a2h-protocol.yaml). They are used by `A2HClient` (Task 3.0) to serialize requests and deserialize responses. All models use `ConfigDict(extra="forbid")` per ASAP security standards to reject unexpected fields.

**Trigger**: PRD approved.
**Enables**: Task 3.0 (`A2HClient` uses these models for request/response typing).
**Depends on**: Nothing (can run in parallel with Task 1.0).

#### Sub-tasks

- [x] 2.1 Create A2H enums and supporting models
  - **File**: `src/asap/integrations/a2h.py` (create new)
  - **What**: Create the following at the top of the file (after imports):
    - `IntentType` — `StrEnum`: `INFORM`, `COLLECT`, `AUTHORIZE`, `ESCALATE`, `RESULT`, `RESPONSE`, `ERROR`.
    - `InteractionState` — `StrEnum`: `PENDING`, `SENT`, `WAITING_INPUT`, `ANSWERED`, `EXPIRED`, `CANCELLED`, `FAILED`.
    - `AssuranceLevel` — `StrEnum`: `LOW`, `MEDIUM`, `HIGH`.
    - `ComponentType` — `StrEnum`: `TEXT`, `SELECT`, `MULTISELECT`, `CHECKBOX`, `RADIO`, `TEXTAREA`, `NUMBER`, `DATE`, `TIME`, `DATETIME`.
    - `ChannelBinding` — `BaseModel` with `type: str`, `address: str`, `fallback: list[ChannelFallback] | None = None`. `ConfigDict(extra="forbid")`.
    - `ChannelFallback` — `BaseModel` with `type: str`, `address: str`. `ConfigDict(extra="forbid")`.
    - `RenderContent` — `BaseModel` with `body: str`, `title: str | None = None`, `footer: str | None = None`. `ConfigDict(extra="forbid")`.
    - `AssuranceConfig` — `BaseModel` with `level: AssuranceLevel = AssuranceLevel.LOW`, `required_factors: list[str] | None = None`. `ConfigDict(extra="forbid")`.
    - `Component` — `BaseModel` with `type: ComponentType`, `name: str`, `label: str | None = None`, `required: bool = False`, `options: list[dict[str, str]] | None = None`. `ConfigDict(extra="forbid")`.
    - `CallbackConfig` — `BaseModel` with `url: str`, `secret: str`. `ConfigDict(extra="forbid")`.
  - **Why**: These are the building blocks used by `A2HMessage`, `GatewayCapabilities`, and `A2HResponse`. Defined first to avoid forward references.
  - **Pattern**: Follow Pydantic v2 style from `src/asap/models/entities.py` (ConfigDict, Field, StrEnum).
  - **Verify**: `python -c "from asap.integrations.a2h import IntentType, InteractionState, ChannelBinding"` succeeds.

- [x] 2.2 Create A2H message envelope model
  - **File**: `src/asap/integrations/a2h.py` (modify — append after 2.1)
  - **What**: Create `A2HMessage` — `BaseModel` with fields matching the [A2H Common Data Envelope](https://github.com/twilio-labs/Agent2Human/blob/main/a2h_framework.md#12-a2h-common-data-envelope):
    - `type: IntentType`
    - `message_id: str`
    - `agent_id: str`
    - `principal_id: str`
    - `a2h_version: str = "1.0"`
    - `interaction_id: str | None = None`
    - `responds_to: str | None = None`
    - `channel: ChannelBinding | None = None`
    - `render: RenderContent | None = None`
    - `links: dict[str, str] | None = None`
    - `params: dict[str, Any] | None = None`
    - `ttl_sec: int = 300`
    - `assurance: AssuranceConfig | None = None`
    - `explanation_bundle: dict[str, str] | None = None`
    - `callback: CallbackConfig | None = None`
    - `components: list[Component] | None = None`
    - `created_at: datetime | None = None`
    - Use `ConfigDict(extra="forbid")`.
  - **Why**: This is the core envelope sent to `POST /v1/intent`. All intent types share this structure.
  - **Verify**: Can instantiate `A2HMessage(type=IntentType.AUTHORIZE, message_id="m1", agent_id="a1", principal_id="p1")`.

- [x] 2.3 Create response and status models
  - **File**: `src/asap/integrations/a2h.py` (modify — append after 2.2)
  - **What**: Create:
    - `IntentResponse` — `BaseModel`: `interaction_id: str`, `state: InteractionState`, `created_at: datetime`, `ttl_sec: int`, `channel_id: str | None = None`, `duplicate: bool | None = None`. `ConfigDict(extra="forbid")`.
    - `A2HResponse` — `BaseModel`: `type: IntentType = IntentType.RESPONSE`, `responds_to: str | None = None`, `interaction_id: str | None = None`, `status: str | None = None`, `decision: str | None = None`, `decided_at: datetime | None = None`, `data: dict[str, Any] | None = None`, `evidence: dict[str, Any] | None = None`. `ConfigDict(extra="forbid")`.
    - `InteractionStatus` — `BaseModel`: `interaction_id: str`, `state: InteractionState`, `created_at: datetime`, `updated_at: datetime`, `response: A2HResponse | None = None`. `ConfigDict(extra="forbid")`.
  - **Why**: `IntentResponse` is returned by `POST /v1/intent`. `InteractionStatus` is returned by `GET /v1/status/{id}`. `A2HResponse` is the human's RESPONSE within the status.
  - **Verify**: `python -c "from asap.integrations.a2h import IntentResponse, A2HResponse, InteractionStatus"` succeeds.

- [x] 2.4 Create gateway capabilities model
  - **File**: `src/asap/integrations/a2h.py` (modify — append after 2.3)
  - **What**: Create `GatewayCapabilities` — `BaseModel`:
    - `a2h_supported: list[str]`
    - `channels: list[str]`
    - `factors: list[str] | None = None`
    - `max_ttl_sec: int | None = None`
    - `locales: list[str] | None = None`
    - `jwks_uri: str | None = None`
    - `quiet_hours: dict[str, str] | None = None`
    - `limits: dict[str, float] | None = None`
    - `auth: dict[str, Any] | None = None`
    - `replay_protection: dict[str, Any] | None = None`
    - `webhooks: dict[str, Any] | None = None`
    - Use `ConfigDict(extra="allow")` — gateway discovery may include fields not yet in the spec. This is the intentional exception to the "forbid" rule.
  - **Why**: Discovery response from `/.well-known/a2h`. Using `extra="allow"` here because gateways may extend the spec with custom fields. This follows the A2H spec's extensibility principle.
  - **Verify**: Can instantiate `GatewayCapabilities(a2h_supported=["1.0"], channels=["sms"])`.

- [ ] 2.5 Commit
  - **Command**: `git add src/asap/integrations/a2h.py && git commit -m "feat(integrations): add A2H protocol Pydantic models"`
  - **Scope**: `src/asap/integrations/a2h.py` (models only, client comes in Task 3.0)

**Acceptance Criteria**:
- [ ] All models importable from `asap.integrations.a2h`.
- [ ] All models (except `GatewayCapabilities`) use `ConfigDict(extra="forbid")`.
- [ ] `GatewayCapabilities` uses `ConfigDict(extra="allow")` (documented exception).
- [ ] Enums are `StrEnum` with uppercase values matching the A2H spec.
- [ ] `uv run mypy src/asap/integrations/a2h.py` passes.

---

### Task 3.0: Create A2HClient (async HTTP client)

**Goal**: Build an async HTTP client that wraps the A2H REST API, supporting discovery, all intent types, status polling, and cancellation.

**Context**: `A2HClient` uses `httpx.AsyncClient` (already an ASAP dependency) to call A2H Gateway endpoints. It supports API Key and OAuth2 Bearer authentication. Blocking methods (AUTHORIZE, COLLECT, ESCALATE) poll `GET /v1/status/{id}` with configurable interval/timeout. The client automatically populates `links.a2a_thread` when a `conversation_id` is provided, enabling cross-protocol traceability.

**Trigger**: Task 2.0 models are available.
**Enables**: Task 4.0 (`A2HApprovalProvider` wraps this client).
**Depends on**: Task 2.0 (Pydantic models).

#### Sub-tasks

- [x] 3.1 Create `A2HClient` class with constructor and auth
  - **File**: `src/asap/integrations/a2h.py` (modify — append after models)
  - **What**: Create `A2HClient` class with:
    - `__init__(self, gateway_url: str, *, api_key: str | None = None, oauth_token: str | None = None, agent_id: str = "asap-agent")` — stores gateway URL (strips trailing slash), auth credentials, and agent_id.
    - Private method `_headers(self) -> dict[str, str]` — returns auth headers: `{"X-A2H-API-Key": api_key}` if api_key, `{"Authorization": f"Bearer {oauth_token}"}` if oauth_token, else empty dict. Always includes `Content-Type: application/json`.
    - `async def _request(self, method: str, path: str, **kwargs) -> httpx.Response` — creates `httpx.AsyncClient`, makes request to `{gateway_url}{path}` with auth headers, raises `httpx.HTTPStatusError` on non-2xx.
  - **Why**: Centralizes auth and HTTP logic. Using `httpx.AsyncClient` per-request (not persistent) to match the pattern in `src/asap/transport/http_client.py`.
  - **Pattern**: Follow `src/asap/transport/http_client.py` for httpx usage patterns.
  - **Verify**: Class instantiates without errors: `A2HClient("http://localhost:3000", api_key="test")`.

- [x] 3.2 Add `discover()` method
  - **File**: `src/asap/integrations/a2h.py` (modify — add method to `A2HClient`)
  - **What**: `async def discover(self) -> GatewayCapabilities` — sends `GET /.well-known/a2h`, deserializes response as `GatewayCapabilities`.
  - **Why**: Enables agents to check gateway capabilities before sending intents (A2H-002).
  - **Verify**: Unit test with mocked `/.well-known/a2h` response returns typed `GatewayCapabilities`.

- [x] 3.3 Add `_send_intent()` private method and `inform()` / `send_result()` public methods
  - **File**: `src/asap/integrations/a2h.py` (modify — add methods to `A2HClient`)
  - **What**: Create:
    - `_send_intent(self, message: A2HMessage) -> IntentResponse` — sends `POST /v1/intent` with message payload, returns `IntentResponse`.
    - `_build_message(self, type: IntentType, principal_id: str, *, body: str | None = None, ..., conversation_id: str | None = None) -> A2HMessage` — factory that creates `A2HMessage` with auto-generated `message_id` (UUID4), `created_at` (UTC now), and populates `links.a2a_thread` with `f"asap:conversation/{conversation_id}"` when `conversation_id` is provided.
    - `async def inform(self, principal_id: str, body: str, *, channel: ChannelBinding | None = None, conversation_id: str | None = None) -> str` — sends INFORM intent, returns `interaction_id`.
    - `async def send_result(self, principal_id: str, body: str, *, responds_to: str | None = None, channel: ChannelBinding | None = None, conversation_id: str | None = None) -> str` — sends RESULT intent, returns `interaction_id`.
  - **Why**: Fire-and-forget methods (A2H-003, A2H-007). `_build_message` centralizes envelope construction and the `a2a_thread` link (A2H-011).
  - **Verify**: `inform()` returns a string `interaction_id`. `links.a2a_thread` is populated when `conversation_id` is passed.

- [x] 3.4 Add `get_status()` and `cancel()` methods
  - **File**: `src/asap/integrations/a2h.py` (modify — add methods to `A2HClient`)
  - **What**: Create:
    - `async def get_status(self, interaction_id: str) -> InteractionStatus` — sends `GET /v1/status/{interaction_id}`, returns `InteractionStatus`.
    - `async def cancel(self, interaction_id: str) -> bool` — sends `POST /v1/cancel/{interaction_id}`, returns `True` if 200, `False` if 404/409.
  - **Why**: Status polling (A2H-008) is the foundation for blocking methods. Cancel (A2H-009) allows agents to abort pending interactions.
  - **Verify**: Unit tests with mocked endpoints return correct types.

- [x] 3.5 Add `_poll_until_resolved()` private method
  - **File**: `src/asap/integrations/a2h.py` (modify — add method to `A2HClient`)
  - **What**: `async def _poll_until_resolved(self, interaction_id: str, *, poll_interval: float = 2.0, timeout: float = 300.0) -> A2HResponse` — polls `get_status()` in a loop with `asyncio.sleep(poll_interval)` between calls. Returns `A2HResponse` when `state` is `ANSWERED`. Raises `TimeoutError` if elapsed time exceeds `timeout`. Raises `ValueError` if state transitions to `EXPIRED`, `CANCELLED`, or `FAILED` (with error info).
  - **Why**: Core polling logic (A2H-010) reused by `authorize()`, `collect()`, and `escalate()`.
  - **Pattern**: Use `asyncio.sleep()` (never `time.sleep()`), per testing standards.
  - **Verify**: Test with mocked sequence: PENDING → WAITING_INPUT → ANSWERED. Verify polling stops and returns response.

- [x] 3.6 Add `authorize()`, `collect()`, and `escalate()` methods
  - **File**: `src/asap/integrations/a2h.py` (modify — add methods to `A2HClient`)
  - **What**: Create:
    - `async def authorize(self, principal_id: str, body: str, *, assurance: AssuranceConfig | None = None, channel: ChannelBinding | None = None, explanation: str | None = None, conversation_id: str | None = None, poll_interval: float = 2.0, timeout: float = 300.0) -> A2HResponse` — builds AUTHORIZE message (with optional `assurance` and `explanation_bundle`), sends intent, polls until resolved.
    - `async def collect(self, principal_id: str, components: list[Component], *, body: str | None = None, channel: ChannelBinding | None = None, conversation_id: str | None = None, poll_interval: float = 2.0, timeout: float = 300.0) -> A2HResponse` — builds COLLECT message with `components`, sends intent, polls.
    - `async def escalate(self, principal_id: str, targets: list[str], *, body: str | None = None, channel: ChannelBinding | None = None, conversation_id: str | None = None, poll_interval: float = 2.0, timeout: float = 300.0) -> A2HResponse` — builds ESCALATE message with `params.targets`, sends intent, polls.
  - **Why**: These are the blocking (polling) methods corresponding to A2H-004, A2H-005, A2H-006.
  - **Verify**: `authorize()` returns `A2HResponse` with `decision` field. Timeout raises `TimeoutError`.

- [ ] 3.7 Commit
  - **Command**: `git add src/asap/integrations/a2h.py && git commit -m "feat(integrations): add A2HClient async HTTP client with polling"`
  - **Scope**: `src/asap/integrations/a2h.py` (models + client)

**Acceptance Criteria**:
- [ ] `A2HClient` supports API Key, OAuth2 Bearer, and no-auth modes.
- [ ] `discover()` returns typed `GatewayCapabilities`.
- [ ] `inform()` and `send_result()` are fire-and-forget (return `interaction_id`).
- [ ] `authorize()`, `collect()`, `escalate()` poll until `ANSWERED` and return `A2HResponse`.
- [ ] Polling raises `TimeoutError` on timeout and `ValueError` on terminal states (EXPIRED, CANCELLED, FAILED).
- [ ] `links.a2a_thread` populated when `conversation_id` is provided.
- [ ] `uv run mypy src/asap/integrations/a2h.py` passes.

---

### Task 4.0: Create A2HApprovalProvider and write all tests

**Goal**: Bridge the HITL Protocol (Task 1.0) with the A2H Client (Task 3.0), and write comprehensive unit tests for both the client and the provider.

**Context**: `A2HApprovalProvider` implements `HumanApprovalProvider` by delegating to `A2HClient.authorize()`. It translates between the generic HITL interface and A2H-specific concepts. Tests use `respx` (or `unittest.mock.AsyncMock` + `patch`) to mock httpx responses — no real HTTP calls.

**Trigger**: Tasks 1.0 and 3.0 are complete.
**Enables**: Task 5.0 (exports, example, docs).
**Depends on**: Task 1.0 (`HumanApprovalProvider`, `ApprovalResult`), Task 3.0 (`A2HClient`).

#### Sub-tasks

- [x] 4.1 Create `A2HApprovalProvider` class
  - **File**: `src/asap/integrations/a2h.py` (modify — append after `A2HClient`)
  - **What**: Create `A2HApprovalProvider` class:
    - `__init__(self, client: A2HClient)` — stores reference to `A2HClient`.
    - `async def request_approval(self, *, context: str, principal_id: str, assurance_level: str = "LOW", timeout_seconds: float = 300.0) -> ApprovalResult` — calls `self._client.authorize(principal_id=principal_id, body=context, assurance=AssuranceConfig(level=AssuranceLevel(assurance_level)), timeout=timeout_seconds)`. Maps `A2HResponse` to `ApprovalResult`: `decision` maps `"APPROVE"` → `ApprovalDecision.APPROVE`, else `DECLINE`; `data`, `evidence`, `decided_at`, `interaction_id` mapped directly.
    - `async def notify(self, *, principal_id: str, body: str) -> str` — convenience method wrapping `self._client.inform()`. Returns `interaction_id`.
  - **Why**: This bridges the generic HITL Protocol with the A2H-specific client. Developers use `HumanApprovalProvider` in their handlers and can swap `A2HApprovalProvider` for any other provider. The `notify()` method is a bonus for INFORM use cases (PRD §12 Q5: AUTHORIZE + INFORM).
  - **Pattern**: Follow `src/asap/integrations/openclaw.py` for client-wrapping patterns.
  - **Integration**: This class is consumed by agent handlers (e.g., `src/asap/examples/a2h_approval.py` in Task 5.0). Handlers receive a `HumanApprovalProvider` and call `request_approval()`.
  - **Verify**: `isinstance(A2HApprovalProvider(client), HumanApprovalProvider)` returns `True`.

- [x] 4.2 Write A2H client unit tests
  - **File**: `tests/integrations/test_a2h.py` (create new)
  - **What**: Create test file with fixtures and tests:
    - **Fixtures**: `_mock_gateway_url() -> str` (returns `"https://gateway.test"`), helper functions for creating mock httpx responses.
    - **Tests**:
      - `test_discover_capabilities` — Mock `GET /.well-known/a2h` with JSON `{"a2h_supported": ["1.0"], "channels": ["sms", "email"]}`. Verify `GatewayCapabilities` fields.
      - `test_inform_sends_correct_payload` — Mock `POST /v1/intent`, capture request body. Verify `type` is `"INFORM"`, `principal_id` and `render.body` match inputs. Verify returns `interaction_id`.
      - `test_send_result_payload` — Mock `POST /v1/intent`. Verify `type` is `"RESULT"` and `responds_to` is set.
      - `test_authorize_polls_until_answered` — Mock `POST /v1/intent` returning `{"interaction_id": "int-1", "state": "SENT", ...}`. Mock `GET /v1/status/int-1` returning `WAITING_INPUT` on first call, then `ANSWERED` with response on second call. Verify `authorize()` returns `A2HResponse` with `decision`.
      - `test_authorize_timeout_raises` — Mock status always returning `WAITING_INPUT`. Call `authorize(..., timeout=0.1, poll_interval=0.05)`. Verify `TimeoutError` raised.
      - `test_authorize_expired_raises_value_error` — Mock status returning `EXPIRED`. Verify `ValueError` raised.
      - `test_collect_returns_structured_data` — Mock collect flow. Verify `data` dict in response.
      - `test_cancel_interaction_success` — Mock `POST /v1/cancel/int-1` returning 200. Verify `cancel()` returns `True`.
      - `test_cancel_interaction_not_found` — Mock 404 response. Verify `cancel()` returns `False`.
      - `test_api_key_auth_header` — Create client with `api_key="test-key"`. Mock request, capture headers. Verify `X-A2H-API-Key: test-key`.
      - `test_oauth_bearer_header` — Create client with `oauth_token="tok"`. Verify `Authorization: Bearer tok`.
      - `test_no_auth_headers` — Create client without credentials. Verify no auth headers sent.
      - `test_a2a_thread_link_populated` — Call `inform(..., conversation_id="conv-123")`. Capture request body. Verify `links.a2a_thread == "asap:conversation/conv-123"`.
      - `test_a2a_thread_link_absent_without_conversation_id` — Call `inform(...)` without `conversation_id`. Verify `links` is `None` or doesn't contain `a2a_thread`.
      - `test_models_forbid_extra_fields` — For each model (except `GatewayCapabilities`), pass an unknown field. Verify `ValidationError` raised.
      - `test_gateway_capabilities_allows_extra` — Pass unknown field to `GatewayCapabilities`. Verify no error.
    - Use `unittest.mock.AsyncMock` and `patch("httpx.AsyncClient.request")` or `patch("httpx.AsyncClient.send")` to mock HTTP calls. Alternative: use `respx` if available in dev deps.
  - **Why**: Comprehensive test coverage for the A2H client. All network calls mocked — no external dependencies.
  - **Pattern**: Follow `tests/integrations/test_openclaw.py` for mock patterns and test structure.
  - **Verify**: `PYTHONPATH=src uv run pytest tests/integrations/test_a2h.py -v` — all tests pass.

- [x] 4.3 Write A2HApprovalProvider tests
  - **File**: `tests/integrations/test_a2h.py` (modify — append after client tests)
  - **What**: Add tests:
    - `test_a2h_provider_satisfies_protocol` — Verify `isinstance(A2HApprovalProvider(mock_client), HumanApprovalProvider)`.
    - `test_a2h_provider_approve` — Mock `A2HClient.authorize()` returning `A2HResponse(decision="APPROVE", ...)`. Call `request_approval()`. Verify `ApprovalResult.decision == ApprovalDecision.APPROVE`.
    - `test_a2h_provider_decline` — Mock `authorize()` returning `decision="DECLINE"`. Verify `DECLINE`.
    - `test_a2h_provider_maps_assurance_level` — Call with `assurance_level="HIGH"`. Verify `A2HClient.authorize()` receives `AssuranceConfig(level=AssuranceLevel.HIGH)`.
    - `test_a2h_provider_timeout_propagates` — Mock `authorize()` raising `TimeoutError`. Verify it propagates to caller.
    - `test_a2h_provider_notify` — Mock `A2HClient.inform()`. Call `notify()`. Verify `inform()` was called and returns `interaction_id`.
  - **Why**: Validates the bridge between the generic HITL Protocol and A2H-specific implementation.
  - **Verify**: `PYTHONPATH=src uv run pytest tests/integrations/test_a2h.py -v -k "provider"` — all provider tests pass.

- [ ] 4.4 Commit
  - **Command**: `git add tests/integrations/test_a2h.py src/asap/integrations/a2h.py && git commit -m "feat(integrations): add A2HApprovalProvider and comprehensive A2H tests"`
  - **Scope**: `tests/integrations/test_a2h.py`, `src/asap/integrations/a2h.py` (A2HApprovalProvider addition)

**Acceptance Criteria**:
- [ ] `A2HApprovalProvider` satisfies `HumanApprovalProvider` Protocol (`isinstance()` check).
- [ ] `request_approval()` maps A2H responses to `ApprovalResult` correctly.
- [ ] `notify()` wraps `A2HClient.inform()`.
- [ ] All tests in `tests/integrations/test_a2h.py` pass.
- [ ] Test coverage ≥ 90% on `src/asap/integrations/a2h.py`.
- [ ] `PYTHONPATH=src uv run pytest tests/integrations/test_a2h.py tests/handlers/test_hitl.py -v` — all pass.

---

### Task 5.0: Add lazy exports, example, and documentation

**Goal**: Wire up lazy exports in `__init__.py`, create a runnable example, and update project documentation.

**Context**: This is the integration glue. The lazy export in `integrations/__init__.py` follows the PEP 562 `__getattr__` pattern used by all existing integrations. The example follows the `src/asap/examples/` module pattern (runnable via `uv run python -m asap.examples.<name>`). Documentation updates reflect the new A2H integration in `AGENTS.md` and the examples README.

**Trigger**: Tasks 1.0–4.0 complete and merged.
**Enables**: Community engagement (Phase 2 in PRD §8.2). Developer adoption.
**Depends on**: Tasks 1.0, 2.0, 3.0, 4.0.

#### Sub-tasks

- [x] 5.1 Add lazy exports to `integrations/__init__.py`
  - **File**: `src/asap/integrations/__init__.py` (modify existing)
  - **What**:
    - Add to module docstring: `from asap.integrations import A2HClient, A2HApprovalProvider  # no extra deps`.
    - Add `"A2HClient"` and `"A2HApprovalProvider"` to `__all__` list.
    - Add two new `if` blocks in `__getattr__`:
      ```python
      if name == "A2HClient":
          from asap.integrations.a2h import A2HClient
          return A2HClient
      if name == "A2HApprovalProvider":
          from asap.integrations.a2h import A2HApprovalProvider
          return A2HApprovalProvider
      ```
  - **Why**: Follows the PEP 562 lazy import pattern. Unlike other integrations that need optional deps, A2H uses only core deps — but we still use lazy imports for consistency and to avoid importing httpx eagerly.
  - **Pattern**: Follow exact pattern of existing entries (LangChain, CrewAI, etc.) in the same file.
  - **Verify**: `python -c "from asap.integrations import A2HClient, A2HApprovalProvider; print('OK')"` prints `OK`.

- [x] 5.2 Add A2H exports to `integrations/__init__.py` tests
  - **File**: `tests/integrations/test_integrations_init.py` (modify existing)
  - **What**: Add test cases verifying `A2HClient` and `A2HApprovalProvider` are importable from `asap.integrations`. Follow the existing test pattern in this file.
  - **Why**: Ensures lazy exports work correctly and don't regress.
  - **Pattern**: Follow existing tests in the same file.
  - **Verify**: `PYTHONPATH=src uv run pytest tests/integrations/test_integrations_init.py -v` — all pass.

- [x] 5.3 Create A2H approval example module
  - **File**: `src/asap/examples/a2h_approval.py` (create new)
  - **What**: Create a runnable example demonstrating the ASAP + A2H flow:
    - Module docstring explaining the example and how to run it.
    - Constants: `DEFAULT_GATEWAY_URL`, `DEFAULT_PRINCIPAL_ID`, `DEFAULT_AGENT_ID`.
    - `async def run_approval_demo(gateway_url: str, principal_id: str) -> None`:
      1. Create `A2HClient(gateway_url)` (no auth for local dev).
      2. Optionally call `discover()` and print gateway capabilities.
      3. Send `inform()` to notify the human.
      4. Send `authorize()` with `body="Authorize agent to proceed with task?"`, `assurance=AssuranceConfig(level=AssuranceLevel.LOW)`.
      5. Print the `ApprovalResult`.
    - `def main() -> None` — argparse with `--gateway-url` and `--principal-id` args. Runs `asyncio.run(run_approval_demo(...))`.
    - `if __name__ == "__main__": main()`
    - Include try/except for `TimeoutError` and `httpx.HTTPStatusError` with user-friendly messages.
    - Add a note in the docstring: "To run against Twilio's local demo: `cd <a2h-repo>/demo && npm install && npm start`, then `uv run python -m asap.examples.a2h_approval --gateway-url http://localhost:3000`."
  - **Why**: Functional example required by PRD (P1 goal). Demonstrates the complete ASAP + A2H flow.
  - **Pattern**: Follow `src/asap/examples/mcp_integration.py` structure (argparse, async main, try/except).
  - **Verify**: `uv run python -m asap.examples.a2h_approval --help` prints usage.

- [x] 5.4 Add example to README and create smoke test
  - **File**: `src/asap/examples/README.md` (modify existing), `tests/examples/test_a2h_approval.py` (create new)
  - **What**:
    - In `README.md`: Add a new row to the "MCP and integration" table (or create a "Human-in-the-loop" section): `| **a2h_approval** | A2H approval: notify human + request authorization via A2H Gateway | \`uv run python -m asap.examples.a2h_approval [--gateway-url URL] [--principal-id ID]\` |`.
    - In `test_a2h_approval.py`: Create a smoke test that imports the module and verifies `main` and `run_approval_demo` are callable (following `tests/examples/test_echo_agent.py` pattern). Do NOT make real HTTP calls.
  - **Why**: Keeps the examples README complete and ensures the module is importable without errors.
  - **Pattern**: Follow `tests/examples/test_echo_agent.py` for smoke test structure.
  - **Verify**: `PYTHONPATH=src uv run pytest tests/examples/test_a2h_approval.py -v` passes.

- [x] 5.5 Update `AGENTS.md`
  - **File**: `AGENTS.md` (modify existing)
  - **What**: In the `## Project Context` section, add `A2H` to the **Framework Integrations** list: `LangChain, CrewAI, PydanticAI, LlamaIndex, SmolAgents, Vercel AI SDK, MCP, OpenClaw, A2H.`
  - **Why**: Keeps the agent context map accurate for AI agents reading the codebase.
  - **Verify**: `grep "A2H" AGENTS.md` returns a match.

- [x] 5.6 Run full CI check suite
  - **Command**: `uv run ruff check . && uv run ruff format --check . && uv run mypy src/ scripts/ tests/ && PYTHONPATH=src uv run pytest tests/handlers/ tests/integrations/test_a2h.py tests/integrations/test_integrations_init.py tests/examples/test_a2h_approval.py -v`
  - **What**: Run linting, formatting, type checking, and all A2H-related tests.
  - **Why**: Pre-push CI verification per git-commits.mdc rules.
  - **Verify**: All commands exit 0.

- [ ] 5.7 Commit
  - **Command**: `git add src/asap/integrations/__init__.py src/asap/examples/a2h_approval.py src/asap/examples/README.md tests/examples/test_a2h_approval.py tests/integrations/test_integrations_init.py AGENTS.md && git commit -m "feat(integrations): add A2H lazy exports, example, and documentation"`
  - **Scope**: All files from 5.1–5.5

**Acceptance Criteria**:
- [ ] `from asap.integrations import A2HClient, A2HApprovalProvider` works.
- [ ] `uv run python -m asap.examples.a2h_approval --help` prints usage without errors.
- [ ] Examples README includes A2H approval entry.
- [ ] `AGENTS.md` lists A2H in Framework Integrations.
- [ ] All linting, type checking, and tests pass.
- [ ] No changes to `pyproject.toml` (zero new dependencies verified).

---

## Definition of Done

- [ ] `HumanApprovalProvider` Protocol available in `asap.handlers` (core, decoupled)
- [ ] `A2HClient` and `A2HApprovalProvider` available in `asap.integrations` (lazy exports)
- [ ] All A2H Pydantic models validate against the A2H OpenAPI spec
- [ ] Unit test coverage ≥ 90% on new code
- [ ] Runnable example at `asap.examples.a2h_approval`
- [ ] `AGENTS.md` updated
- [ ] Zero new dependencies added to `pyproject.toml`
- [ ] Full CI suite passes: `ruff check`, `ruff format --check`, `mypy`, `pytest`

**Total Sub-tasks**: 24
