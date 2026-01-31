"""Property-based tests for ASAP Pydantic models.

Serialization roundtrip: model -> JSON -> model preserves data for all protocol models.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone

from hypothesis import given
from hypothesis import strategies as st

from asap.models.base import ASAPBaseModel
from asap.models.entities import (
    Agent,
    Artifact,
    AuthScheme,
    Capability,
    Conversation,
    Endpoint,
    Manifest,
    Message,
    Skill,
    StateSnapshot,
    Task,
)
from asap.models.envelope import Envelope
from asap.models.enums import MessageRole, TaskStatus, UpdateType
from asap.models.parts import DataPart, FilePart, ResourcePart, TemplatePart, TextPart
from asap.models.payloads import (
    ArtifactNotify,
    McpResourceData,
    McpResourceFetch,
    McpToolCall,
    McpToolResult,
    MessageSend,
    StateQuery,
    StateRestore,
    TaskCancel,
    TaskRequest,
    TaskResponse,
    TaskUpdate,
)

# --- Shared strategies ---

_ULID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def st_ulid_like() -> st.SearchStrategy[str]:
    """Generate ULID-like strings (26 chars, Crockford Base32)."""
    return st.text(alphabet=_ULID_ALPHABET, min_size=26, max_size=26)


def st_agent_urn() -> st.SearchStrategy[str]:
    """Generate valid agent URNs (urn:asap:agent:name or urn:asap:agent:name:sub)."""
    name = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1, max_size=60)
    return st.builds(lambda n: f"urn:asap:agent:{n}", name)


def st_semver() -> st.SearchStrategy[str]:
    """Generate valid semantic version strings."""
    return st.sampled_from(["0.1", "1.0.0", "1.2.3", "2.0.0-beta.1"])


def st_datetime_utc() -> st.SearchStrategy[datetime]:
    """Generate timezone-aware UTC datetimes (Hypothesis requires naive min/max)."""
    return st.datetimes(
        min_value=datetime(2000, 1, 1),  # noqa: DTZ001
        max_value=datetime(9999, 12, 31, 23, 59, 59, 999999),  # noqa: DTZ001
        timezones=st.just(timezone.utc),
    )


def st_json_dict() -> st.SearchStrategy[dict]:
    """Generate JSON-serializable dicts (str keys, simple values)."""
    return st.dictionaries(
        keys=st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=1, max_size=20),
        values=st.one_of(
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.booleans(),
            st.text(max_size=100),
            st.lists(st.integers() | st.text(max_size=50), max_size=5),
        ),
        max_size=8,
    )


def st_mime_type() -> st.SearchStrategy[str]:
    """Generate valid MIME types (type/subtype)."""
    main = st.sampled_from(["application", "text", "image", "audio"])
    sub = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789.+-", min_size=1, max_size=30)
    return st.builds(lambda a, b: f"{a}/{b}", main, sub)


def st_file_uri() -> st.SearchStrategy[str]:
    """Generate URIs allowed by FilePart (no file://, no ..)."""
    return st.one_of(
        st.builds(lambda p: f"https://example.com/{p}", st.text(alphabet="a-z0-9/", max_size=30)),
        st.builds(
            lambda b: f"data:application/octet-stream;base64,{b}",
            st.binary(max_size=20).map(lambda x: base64.b64encode(x).decode()),
        ),
    )


# --- Model strategies (leaf to root) ---


@st.composite
def st_skill(draw: st.DrawFn) -> Skill:
    """Strategy for Skill."""
    return Skill(
        id=draw(st.text(alphabet="a-z0-9_-", min_size=1, max_size=40)),
        description=draw(st.text(max_size=200)),
        input_schema=draw(st.none() | st_json_dict()),
        output_schema=draw(st.none() | st_json_dict()),
    )


@st.composite
def st_text_part(draw: st.DrawFn) -> TextPart:
    """Strategy for TextPart."""
    return TextPart(type="text", content=draw(st.text(max_size=500)))


@st.composite
def st_data_part(draw: st.DrawFn) -> DataPart:
    """Strategy for DataPart."""
    return DataPart(
        type="data",
        data=draw(st_json_dict()),
        schema_uri=draw(st.none() | st.just("https://example.com/schema.json")),
    )


@st.composite
def st_file_part(draw: st.DrawFn) -> FilePart:
    """Strategy for FilePart (valid URI, MIME, optional base64 inline)."""
    uri = draw(st_file_uri())
    mime = draw(st_mime_type())
    inline = draw(st.none() | st.binary(max_size=12).map(lambda x: base64.b64encode(x).decode()))
    return FilePart(type="file", uri=uri, mime_type=mime, inline_data=inline)


@st.composite
def st_resource_part(draw: st.DrawFn) -> ResourcePart:
    """Strategy for ResourcePart."""
    return ResourcePart(
        type="resource",
        resource_uri=draw(st.text(alphabet="a-z0-9:/.-", min_size=10, max_size=120)),
    )


@st.composite
def st_template_part(draw: st.DrawFn) -> TemplatePart:
    """Strategy for TemplatePart."""
    return TemplatePart(
        type="template",
        template=draw(st.text(max_size=200)),
        variables=draw(st_json_dict()),
    )


@st.composite
def st_endpoint(draw: st.DrawFn) -> Endpoint:
    """Strategy for Endpoint."""
    return Endpoint(
        asap=draw(st.just("https://example.com/asap")),
        events=draw(st.none() | st.just("wss://example.com/events")),
    )


@st.composite
def st_auth_scheme(draw: st.DrawFn) -> AuthScheme:
    """Strategy for AuthScheme (schemes must be supported: bearer, basic)."""
    schemes = draw(st.lists(st.sampled_from(["bearer", "basic"]), min_size=1, max_size=2).map(list))
    schemes = list(dict.fromkeys(schemes))  # unique
    return AuthScheme(
        schemes=schemes,
        oauth2=draw(st.none() | st_json_dict()),
    )


@st.composite
def st_capability(draw: st.DrawFn) -> Capability:
    """Strategy for Capability."""
    return Capability(
        asap_version=draw(st_semver()),
        skills=draw(st.lists(st_skill(), max_size=4)),
        state_persistence=draw(st.booleans()),
        streaming=draw(st.booleans()),
        mcp_tools=draw(st.lists(st.text(alphabet="a-z_", max_size=30), max_size=3)),
    )


@st.composite
def st_agent(draw: st.DrawFn) -> Agent:
    """Strategy for Agent."""
    return Agent(
        id=draw(st_agent_urn()),
        manifest_uri=draw(st.just("https://example.com/.well-known/asap/manifest.json")),
        capabilities=draw(
            st.lists(st.text(alphabet="a-z.", min_size=1, max_size=40), min_size=1, max_size=5)
        ),
    )


@st.composite
def st_manifest(draw: st.DrawFn) -> Manifest:
    """Strategy for Manifest (auth optional; if present must be valid)."""
    auth = draw(st.none() | st_auth_scheme())
    return Manifest(
        id=draw(st_agent_urn()),
        name=draw(st.text(alphabet="a-z ", max_size=50)),
        version=draw(st_semver()),
        description=draw(st.text(max_size=200)),
        capabilities=draw(st_capability()),
        endpoints=draw(st_endpoint()),
        auth=auth,
        signature=draw(st.none() | st.text(max_size=100)),
    )


@st.composite
def st_conversation(draw: st.DrawFn) -> Conversation:
    """Strategy for Conversation."""
    return Conversation(
        id=draw(st_ulid_like()),
        participants=draw(st.lists(st_agent_urn(), min_size=1, max_size=4)),
        created_at=draw(st_datetime_utc()),
        metadata=draw(st.none() | st_json_dict()),
    )


@st.composite
def st_task(draw: st.DrawFn) -> Task:
    """Strategy for Task."""
    return Task(
        id=draw(st_ulid_like()),
        conversation_id=draw(st_ulid_like()),
        parent_task_id=draw(st.none() | st_ulid_like()),
        status=draw(st.sampled_from(list(TaskStatus))),
        depth=draw(st.integers(min_value=0, max_value=10)),
        progress=draw(
            st.none() | st.dictionaries(keys=st.just("percent"), values=st.integers(0, 100))
        ),
        created_at=draw(st_datetime_utc()),
        updated_at=draw(st_datetime_utc()),
    )


@st.composite
def st_message(draw: st.DrawFn) -> Message:
    """Strategy for Message."""
    return Message(
        id=draw(st_ulid_like()),
        task_id=draw(st_ulid_like()),
        sender=draw(st_agent_urn()),
        role=draw(st.sampled_from(list(MessageRole))),
        parts=draw(st.lists(st_ulid_like(), min_size=0, max_size=5)),
        timestamp=draw(st_datetime_utc()),
    )


@st.composite
def st_artifact(draw: st.DrawFn) -> Artifact:
    """Strategy for Artifact."""
    return Artifact(
        id=draw(st_ulid_like()),
        task_id=draw(st_ulid_like()),
        name=draw(st.text(max_size=80)),
        parts=draw(st.lists(st_ulid_like(), max_size=5)),
        created_at=draw(st_datetime_utc()),
    )


@st.composite
def st_state_snapshot(draw: st.DrawFn) -> StateSnapshot:
    """Strategy for StateSnapshot."""
    return StateSnapshot(
        id=draw(st_ulid_like()),
        task_id=draw(st_ulid_like()),
        version=draw(st.integers(min_value=1, max_value=1000)),
        data=draw(st_json_dict()),
        checkpoint=draw(st.booleans()),
        created_at=draw(st_datetime_utc()),
    )


# --- Payload strategies ---


@st.composite
def st_task_request(draw: st.DrawFn) -> TaskRequest:
    """Strategy for TaskRequest."""
    return TaskRequest(
        conversation_id=draw(st_ulid_like()),
        parent_task_id=draw(st.none() | st_ulid_like()),
        skill_id=draw(st.text(alphabet="a-z0-9_", min_size=1, max_size=40)),
        input=draw(st_json_dict()),
        config=draw(st.none() | st_json_dict()),
    )


@st.composite
def st_task_response(draw: st.DrawFn) -> TaskResponse:
    """Strategy for TaskResponse."""
    return TaskResponse(
        task_id=draw(st_ulid_like()),
        status=draw(st.sampled_from(list(TaskStatus))),
        result=draw(st.none() | st_json_dict()),
        final_state=draw(st.none() | st_json_dict()),
        metrics=draw(st.none() | st_json_dict()),
    )


@st.composite
def st_task_update(draw: st.DrawFn) -> TaskUpdate:
    """Strategy for TaskUpdate (progress percent 0-100 if present)."""
    progress = draw(
        st.none()
        | st.dictionaries(
            keys=st.sampled_from(["percent", "message"]),
            values=st.one_of(st.integers(0, 100), st.text(max_size=50)),
        )
    )
    if progress and "percent" in progress and not isinstance(progress["percent"], (int, float)):
        progress = {k: v for k, v in progress.items() if k != "percent"}
    if progress and "percent" in progress:
        pct = progress["percent"]
        progress = dict(progress)
        progress["percent"] = max(0, min(100, int(pct) if isinstance(pct, (int, float)) else 50))
    return TaskUpdate(
        task_id=draw(st_ulid_like()),
        update_type=draw(st.sampled_from(list(UpdateType))),
        status=draw(st.sampled_from(list(TaskStatus))),
        progress=progress,
        input_request=draw(st.none() | st_json_dict()),
    )


@st.composite
def st_task_cancel(draw: st.DrawFn) -> TaskCancel:
    """Strategy for TaskCancel."""
    return TaskCancel(
        task_id=draw(st_ulid_like()),
        reason=draw(st.none() | st.text(max_size=100)),
    )


@st.composite
def st_message_send(draw: st.DrawFn) -> MessageSend:
    """Strategy for MessageSend."""
    return MessageSend(
        task_id=draw(st_ulid_like()),
        message_id=draw(st_ulid_like()),
        sender=draw(st_agent_urn()),
        role=draw(st.sampled_from(list(MessageRole))),
        parts=draw(st.lists(st_ulid_like(), max_size=5)),
    )


@st.composite
def st_state_query(draw: st.DrawFn) -> StateQuery:
    """Strategy for StateQuery."""
    return StateQuery(
        task_id=draw(st_ulid_like()),
        version=draw(st.none() | st.integers(1, 100)),
    )


@st.composite
def st_state_restore(draw: st.DrawFn) -> StateRestore:
    """Strategy for StateRestore."""
    return StateRestore(
        task_id=draw(st_ulid_like()),
        snapshot_id=draw(st_ulid_like()),
    )


@st.composite
def st_artifact_notify(draw: st.DrawFn) -> ArtifactNotify:
    """Strategy for ArtifactNotify."""
    return ArtifactNotify(
        artifact_id=draw(st_ulid_like()),
        task_id=draw(st_ulid_like()),
        name=draw(st.none() | st.text(max_size=80)),
    )


@st.composite
def st_mcp_tool_call(draw: st.DrawFn) -> McpToolCall:
    """Strategy for McpToolCall."""
    return McpToolCall(
        request_id=draw(st_ulid_like()),
        tool_name=draw(st.text(alphabet="a-z_", min_size=1, max_size=40)),
        arguments=draw(st_json_dict()),
        mcp_context=draw(st.none() | st_json_dict()),
    )


@st.composite
def st_mcp_tool_result(draw: st.DrawFn) -> McpToolResult:
    """Strategy for McpToolResult (result/error mutually exclusive by success)."""
    success = draw(st.booleans())
    if success:
        return McpToolResult(
            request_id=draw(st_ulid_like()),
            success=True,
            result=draw(st_json_dict()),
            error=None,
        )
    return McpToolResult(
        request_id=draw(st_ulid_like()),
        success=False,
        result=None,
        error=draw(st.text(min_size=1, max_size=200)),
    )


@st.composite
def st_mcp_resource_fetch(draw: st.DrawFn) -> McpResourceFetch:
    """Strategy for McpResourceFetch."""
    return McpResourceFetch(
        resource_uri=draw(st.text(alphabet="a-z0-9:/.-", min_size=10, max_size=100)),
    )


@st.composite
def st_mcp_resource_data(draw: st.DrawFn) -> McpResourceData:
    """Strategy for McpResourceData."""
    return McpResourceData(
        resource_uri=draw(st.text(alphabet="a-z0-9:/.-", min_size=10, max_size=100)),
        content=draw(st_json_dict()),
    )


# --- Envelope strategy (payload_type + payload; correlation_id when response) ---

_RESPONSE_PAYLOAD_TYPES = {"TaskResponse", "McpToolResult", "McpResourceData"}


@st.composite
def st_envelope(draw: st.DrawFn) -> Envelope:
    """Strategy for Envelope (correlation_id set when payload_type is response type)."""
    payload_type = draw(
        st.sampled_from(
            [
                "TaskRequest",
                "TaskResponse",
                "TaskUpdate",
                "TaskCancel",
                "MessageSend",
                "StateQuery",
                "StateRestore",
                "ArtifactNotify",
                "McpToolCall",
                "McpToolResult",
                "McpResourceFetch",
                "McpResourceData",
            ]
        )
    )
    payload = draw(st_json_dict())
    correlation_id = (
        draw(st.none() | st_ulid_like())
        if payload_type not in _RESPONSE_PAYLOAD_TYPES
        else draw(st_ulid_like())
    )
    return Envelope(
        id=draw(st.none() | st_ulid_like()),
        asap_version=draw(st_semver()),
        timestamp=draw(st.none() | st_datetime_utc()),
        sender=draw(st_agent_urn()),
        recipient=draw(st_agent_urn()),
        payload_type=payload_type,
        payload=payload,
        correlation_id=correlation_id,
        trace_id=draw(st.none() | st_ulid_like()),
        extensions=draw(st.none() | st_json_dict()),
    )


# --- Roundtrip helper ---


def _roundtrip_preserves_data(model_class: type[ASAPBaseModel], instance: ASAPBaseModel) -> None:
    """Assert model -> JSON -> model preserves data."""
    json_str = instance.model_dump_json()
    parsed = model_class.model_validate_json(json_str)
    assert parsed == instance, f"Roundtrip failed for {model_class.__name__}"


# --- Property tests: serialization roundtrip per model ---


class TestModelPropertiesScaffold:
    """Placeholder property (kept for compatibility)."""

    @given(st.text(min_size=0, max_size=100))
    def test_text_roundtrip_identity(self, value: str) -> None:
        """Any string roundtrips through itself."""
        assert value == value


class TestEntityRoundtrip:
    """Serialization roundtrip for entity models."""

    @given(st_skill())
    def test_skill_roundtrip(self, model: Skill) -> None:
        """Skill -> JSON -> Skill preserves data."""
        _roundtrip_preserves_data(Skill, model)

    @given(st_capability())
    def test_capability_roundtrip(self, model: Capability) -> None:
        """Capability -> JSON -> Capability preserves data."""
        _roundtrip_preserves_data(Capability, model)

    @given(st_endpoint())
    def test_endpoint_roundtrip(self, model: Endpoint) -> None:
        """Endpoint -> JSON -> Endpoint preserves data."""
        _roundtrip_preserves_data(Endpoint, model)

    @given(st_auth_scheme())
    def test_auth_scheme_roundtrip(self, model: AuthScheme) -> None:
        """AuthScheme -> JSON -> AuthScheme preserves data."""
        _roundtrip_preserves_data(AuthScheme, model)

    @given(st_agent())
    def test_agent_roundtrip(self, model: Agent) -> None:
        """Agent -> JSON -> Agent preserves data."""
        _roundtrip_preserves_data(Agent, model)

    @given(st_manifest())
    def test_manifest_roundtrip(self, model: Manifest) -> None:
        """Manifest -> JSON -> Manifest preserves data."""
        _roundtrip_preserves_data(Manifest, model)

    @given(st_conversation())
    def test_conversation_roundtrip(self, model: Conversation) -> None:
        """Conversation -> JSON -> Conversation preserves data."""
        _roundtrip_preserves_data(Conversation, model)

    @given(st_task())
    def test_task_roundtrip(self, model: Task) -> None:
        """Task -> JSON -> Task preserves data."""
        _roundtrip_preserves_data(Task, model)

    @given(st_message())
    def test_message_roundtrip(self, model: Message) -> None:
        """Message -> JSON -> Message preserves data."""
        _roundtrip_preserves_data(Message, model)

    @given(st_artifact())
    def test_artifact_roundtrip(self, model: Artifact) -> None:
        """Artifact -> JSON -> Artifact preserves data."""
        _roundtrip_preserves_data(Artifact, model)

    @given(st_state_snapshot())
    def test_state_snapshot_roundtrip(self, model: StateSnapshot) -> None:
        """StateSnapshot -> JSON -> StateSnapshot preserves data."""
        _roundtrip_preserves_data(StateSnapshot, model)


class TestPartsRoundtrip:
    """Serialization roundtrip for part models."""

    @given(st_text_part())
    def test_text_part_roundtrip(self, model: TextPart) -> None:
        """TextPart -> JSON -> TextPart preserves data."""
        _roundtrip_preserves_data(TextPart, model)

    @given(st_data_part())
    def test_data_part_roundtrip(self, model: DataPart) -> None:
        """DataPart -> JSON -> DataPart preserves data."""
        _roundtrip_preserves_data(DataPart, model)

    @given(st_file_part())
    def test_file_part_roundtrip(self, model: FilePart) -> None:
        """FilePart -> JSON -> FilePart preserves data."""
        _roundtrip_preserves_data(FilePart, model)

    @given(st_resource_part())
    def test_resource_part_roundtrip(self, model: ResourcePart) -> None:
        """ResourcePart -> JSON -> ResourcePart preserves data."""
        _roundtrip_preserves_data(ResourcePart, model)

    @given(st_template_part())
    def test_template_part_roundtrip(self, model: TemplatePart) -> None:
        """TemplatePart -> JSON -> TemplatePart preserves data."""
        _roundtrip_preserves_data(TemplatePart, model)


class TestPayloadsRoundtrip:
    """Serialization roundtrip for payload models."""

    @given(st_task_request())
    def test_task_request_roundtrip(self, model: TaskRequest) -> None:
        """TaskRequest -> JSON -> TaskRequest preserves data."""
        _roundtrip_preserves_data(TaskRequest, model)

    @given(st_task_response())
    def test_task_response_roundtrip(self, model: TaskResponse) -> None:
        """TaskResponse -> JSON -> TaskResponse preserves data."""
        _roundtrip_preserves_data(TaskResponse, model)

    @given(st_task_update())
    def test_task_update_roundtrip(self, model: TaskUpdate) -> None:
        """TaskUpdate -> JSON -> TaskUpdate preserves data."""
        _roundtrip_preserves_data(TaskUpdate, model)

    @given(st_task_cancel())
    def test_task_cancel_roundtrip(self, model: TaskCancel) -> None:
        """TaskCancel -> JSON -> TaskCancel preserves data."""
        _roundtrip_preserves_data(TaskCancel, model)

    @given(st_message_send())
    def test_message_send_roundtrip(self, model: MessageSend) -> None:
        """MessageSend -> JSON -> MessageSend preserves data."""
        _roundtrip_preserves_data(MessageSend, model)

    @given(st_state_query())
    def test_state_query_roundtrip(self, model: StateQuery) -> None:
        """StateQuery -> JSON -> StateQuery preserves data."""
        _roundtrip_preserves_data(StateQuery, model)

    @given(st_state_restore())
    def test_state_restore_roundtrip(self, model: StateRestore) -> None:
        """StateRestore -> JSON -> StateRestore preserves data."""
        _roundtrip_preserves_data(StateRestore, model)

    @given(st_artifact_notify())
    def test_artifact_notify_roundtrip(self, model: ArtifactNotify) -> None:
        """ArtifactNotify -> JSON -> ArtifactNotify preserves data."""
        _roundtrip_preserves_data(ArtifactNotify, model)

    @given(st_mcp_tool_call())
    def test_mcp_tool_call_roundtrip(self, model: McpToolCall) -> None:
        """McpToolCall -> JSON -> McpToolCall preserves data."""
        _roundtrip_preserves_data(McpToolCall, model)

    @given(st_mcp_tool_result())
    def test_mcp_tool_result_roundtrip(self, model: McpToolResult) -> None:
        """McpToolResult -> JSON -> McpToolResult preserves data."""
        _roundtrip_preserves_data(McpToolResult, model)

    @given(st_mcp_resource_fetch())
    def test_mcp_resource_fetch_roundtrip(self, model: McpResourceFetch) -> None:
        """McpResourceFetch -> JSON -> McpResourceFetch preserves data."""
        _roundtrip_preserves_data(McpResourceFetch, model)

    @given(st_mcp_resource_data())
    def test_mcp_resource_data_roundtrip(self, model: McpResourceData) -> None:
        """McpResourceData -> JSON -> McpResourceData preserves data."""
        _roundtrip_preserves_data(McpResourceData, model)


class TestEnvelopeRoundtrip:
    """Serialization roundtrip for Envelope."""

    @given(st_envelope())
    def test_envelope_roundtrip(self, model: Envelope) -> None:
        """Envelope -> JSON -> Envelope preserves data."""
        _roundtrip_preserves_data(Envelope, model)
