"""Tests for Agent and Manifest entity models."""

import pytest
from pydantic import ValidationError

from asap.models.entities import Agent, AuthScheme, Capability, Endpoint, Manifest, Skill
from asap.models.ids import generate_id


class TestAgent:
    """Test suite for Agent entity model."""

    def test_agent_creation_minimal(self):
        """Test creating an Agent with minimal required fields."""
        agent = Agent(
            id="urn:asap:agent:test-v1",
            manifest_uri="https://example.com/.well-known/asap/manifest.json",
            capabilities=["task.execute"],
        )

        assert agent.id == "urn:asap:agent:test-v1"
        assert agent.manifest_uri == "https://example.com/.well-known/asap/manifest.json"
        assert agent.capabilities == ["task.execute"]

    def test_agent_creation_full(self):
        """Test creating an Agent with all fields."""
        agent = Agent(
            id="urn:asap:agent:research-v1",
            manifest_uri="https://agents.example.com/.well-known/asap/research-v1.json",
            capabilities=["task.execute", "state.persist", "mcp.tools"],
        )

        assert len(agent.capabilities) == 3
        assert "mcp.tools" in agent.capabilities

    def test_agent_is_immutable(self):
        """Test that Agent instances are immutable."""
        agent = Agent(
            id="urn:asap:agent:test",
            manifest_uri="https://example.com/manifest.json",
            capabilities=["task.execute"],
        )

        with pytest.raises(ValidationError, match="frozen"):
            agent.id = "new_id"  # type: ignore[misc]

    def test_agent_json_schema(self):
        """Test that Agent generates valid JSON Schema."""
        schema = Agent.model_json_schema()

        assert schema["type"] == "object"
        assert "id" in schema["properties"]
        assert "manifest_uri" in schema["properties"]
        assert "capabilities" in schema["properties"]
        assert set(schema["required"]) == {"id", "manifest_uri", "capabilities"}

    def test_agent_serialization(self):
        """Test Agent serialization to JSON."""
        agent = Agent(
            id="urn:asap:agent:test",
            manifest_uri="https://example.com/manifest.json",
            capabilities=["task.execute", "state.persist"],
        )

        json_data = agent.model_dump()
        assert json_data["id"] == "urn:asap:agent:test"
        assert len(json_data["capabilities"]) == 2

    def test_agent_deserialization(self):
        """Test Agent deserialization from JSON."""
        data = {
            "id": "urn:asap:agent:test",
            "manifest_uri": "https://example.com/manifest.json",
            "capabilities": ["task.execute"],
        }

        agent = Agent.model_validate(data)
        assert agent.id == data["id"]
        assert agent.capabilities == data["capabilities"]


class TestSkill:
    """Test suite for Skill model."""

    def test_skill_creation(self):
        """Test creating a Skill with all fields."""
        skill = Skill(
            id="web_research",
            description="Search and synthesize information from the web",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"summary": {"type": "string"}}},
        )

        assert skill.id == "web_research"
        assert "search" in skill.description.lower()
        assert skill.input_schema["type"] == "object"
        assert skill.output_schema["type"] == "object"

    def test_skill_optional_schemas(self):
        """Test that input/output schemas are optional."""
        skill = Skill(id="simple_skill", description="A simple skill")

        assert skill.input_schema is None
        assert skill.output_schema is None


class TestCapability:
    """Test suite for Capability model."""

    def test_capability_creation(self):
        """Test creating Capability with all fields."""
        capability = Capability(
            asap_version="0.1",
            skills=[Skill(id="web_research", description="Research skill")],
            state_persistence=True,
            streaming=True,
            mcp_tools=["web_search", "url_fetch"],
        )

        assert capability.asap_version == "0.1"
        assert len(capability.skills) == 1
        assert capability.state_persistence is True
        assert capability.streaming is True
        assert len(capability.mcp_tools) == 2

    def test_capability_optional_fields(self):
        """Test that optional fields default correctly."""
        capability = Capability(asap_version="0.1", skills=[])

        assert capability.state_persistence is False
        assert capability.streaming is False
        assert capability.mcp_tools == []


class TestEndpoint:
    """Test suite for Endpoint model."""

    def test_endpoint_creation(self):
        """Test creating Endpoint with required and optional fields."""
        endpoint = Endpoint(
            asap="https://api.example.com/asap", events="wss://api.example.com/asap/events"
        )

        assert endpoint.asap == "https://api.example.com/asap"
        assert endpoint.events == "wss://api.example.com/asap/events"

    def test_endpoint_optional_events(self):
        """Test that events endpoint is optional."""
        endpoint = Endpoint(asap="https://api.example.com/asap")

        assert endpoint.asap == "https://api.example.com/asap"
        assert endpoint.events is None


class TestAuthScheme:
    """Test suite for AuthScheme model."""

    def test_auth_scheme_bearer_only(self):
        """Test AuthScheme with bearer token only."""
        auth = AuthScheme(schemes=["bearer"])

        assert auth.schemes == ["bearer"]
        assert auth.oauth2 is None

    def test_auth_scheme_with_oauth2(self):
        """Test AuthScheme with OAuth2 configuration."""
        auth = AuthScheme(
            schemes=["bearer", "oauth2"],
            oauth2={
                "authorization_url": "https://auth.example.com/authorize",
                "token_url": "https://auth.example.com/token",
                "scopes": ["asap:execute", "asap:read"],
            },
        )

        assert "oauth2" in auth.schemes
        assert auth.oauth2 is not None
        assert auth.oauth2["authorization_url"] == "https://auth.example.com/authorize"
        assert len(auth.oauth2["scopes"]) == 2


class TestManifest:
    """Test suite for Manifest entity model."""

    def test_manifest_creation_minimal(self):
        """Test creating a Manifest with minimal required fields."""
        manifest = Manifest(
            id="urn:asap:agent:test-v1",
            name="Test Agent",
            version="1.0.0",
            description="A test agent",
            capabilities=Capability(asap_version="0.1", skills=[]),
            endpoints=Endpoint(asap="https://api.example.com/asap"),
        )

        assert manifest.id == "urn:asap:agent:test-v1"
        assert manifest.name == "Test Agent"
        assert manifest.version == "1.0.0"
        assert manifest.capabilities.asap_version == "0.1"

    def test_manifest_creation_full(self):
        """Test creating a Manifest with all fields."""
        manifest = Manifest(
            id="urn:asap:agent:research-v1",
            name="Research Agent",
            version="1.0.0",
            description="Performs web research and summarization",
            capabilities=Capability(
                asap_version="0.1",
                skills=[
                    Skill(
                        id="web_research",
                        description="Search and synthesize information",
                        input_schema={"type": "object"},
                        output_schema={"type": "object"},
                    )
                ],
                state_persistence=True,
                streaming=True,
                mcp_tools=["web_search", "url_fetch"],
            ),
            endpoints=Endpoint(
                asap="https://api.example.com/asap", events="wss://api.example.com/asap/events"
            ),
            auth=AuthScheme(
                schemes=["bearer", "oauth2"],
                oauth2={
                    "authorization_url": "https://auth.example.com/authorize",
                    "token_url": "https://auth.example.com/token",
                    "scopes": ["asap:execute", "asap:read"],
                },
            ),
            signature="eyJhbGciOiJFZDI1NTE5...",
        )

        assert manifest.name == "Research Agent"
        assert len(manifest.capabilities.skills) == 1
        assert manifest.capabilities.skills[0].id == "web_research"
        assert manifest.endpoints.events is not None
        assert manifest.auth is not None
        assert manifest.auth.schemes == ["bearer", "oauth2"]
        assert manifest.signature == "eyJhbGciOiJFZDI1NTE5..."

    def test_manifest_optional_fields(self):
        """Test that optional fields are None by default."""
        manifest = Manifest(
            id="urn:asap:agent:simple",
            name="Simple Agent",
            version="1.0.0",
            description="A simple agent",
            capabilities=Capability(asap_version="0.1", skills=[]),
            endpoints=Endpoint(asap="https://api.example.com/asap"),
        )

        assert manifest.auth is None
        assert manifest.signature is None

    def test_manifest_is_immutable(self):
        """Test that Manifest instances are immutable."""
        manifest = Manifest(
            id="urn:asap:agent:test",
            name="Test",
            version="1.0.0",
            description="Test",
            capabilities=Capability(asap_version="0.1", skills=[]),
            endpoints=Endpoint(asap="https://example.com/asap"),
        )

        with pytest.raises(ValidationError, match="frozen"):
            manifest.name = "New Name"  # type: ignore[misc]

    def test_manifest_json_schema(self):
        """Test that Manifest generates valid JSON Schema."""
        schema = Manifest.model_json_schema()

        assert schema["type"] == "object"
        assert "id" in schema["properties"]
        assert "name" in schema["properties"]
        assert "version" in schema["properties"]
        assert "capabilities" in schema["properties"]
        assert "endpoints" in schema["properties"]

        required_fields = set(schema["required"])
        assert "id" in required_fields
        assert "name" in required_fields
        assert "version" in required_fields
        assert "description" in required_fields
        assert "capabilities" in required_fields
        assert "endpoints" in required_fields

    def test_manifest_serialization(self):
        """Test Manifest serialization to JSON."""
        manifest = Manifest(
            id="urn:asap:agent:test",
            name="Test Agent",
            version="1.0.0",
            description="Test",
            capabilities=Capability(
                asap_version="0.1", skills=[Skill(id="test_skill", description="Test")]
            ),
            endpoints=Endpoint(asap="https://example.com/asap"),
        )

        json_data = manifest.model_dump()
        assert json_data["id"] == "urn:asap:agent:test"
        assert json_data["name"] == "Test Agent"
        assert len(json_data["capabilities"]["skills"]) == 1

    def test_manifest_deserialization(self):
        """Test Manifest deserialization from JSON."""
        data = {
            "id": "urn:asap:agent:test",
            "name": "Test Agent",
            "version": "1.0.0",
            "description": "A test agent",
            "capabilities": {
                "asap_version": "0.1",
                "skills": [{"id": "test_skill", "description": "Test skill"}],
                "state_persistence": False,
                "streaming": False,
                "mcp_tools": [],
            },
            "endpoints": {"asap": "https://example.com/asap"},
        }

        manifest = Manifest.model_validate(data)
        assert manifest.id == data["id"]
        assert manifest.name == data["name"]
        assert len(manifest.capabilities.skills) == 1


class TestConversation:
    """Test suite for Conversation entity model."""

    def test_conversation_creation_minimal(self):
        """Test creating a Conversation with minimal required fields."""
        from datetime import datetime, timezone
        from asap.models.entities import Conversation

        conv_id = generate_id()
        created_at = datetime.now(timezone.utc)

        conversation = Conversation(
            id=conv_id,
            participants=["urn:asap:agent:coordinator", "urn:asap:agent:research-v1"],
            created_at=created_at,
        )

        assert conversation.id == conv_id
        assert len(conversation.participants) == 2
        assert conversation.created_at == created_at
        assert conversation.metadata is None

    def test_conversation_with_metadata(self):
        """Test creating a Conversation with metadata."""
        from datetime import datetime, timezone
        from asap.models.entities import Conversation

        conversation = Conversation(
            id=generate_id(),
            participants=["urn:asap:agent:a", "urn:asap:agent:b"],
            created_at=datetime.now(timezone.utc),
            metadata={"purpose": "quarterly_report_research", "ttl_hours": 72},
        )

        assert conversation.metadata is not None
        assert conversation.metadata["purpose"] == "quarterly_report_research"
        assert conversation.metadata["ttl_hours"] == 72

    def test_conversation_json_schema(self):
        """Test that Conversation generates valid JSON Schema."""
        from asap.models.entities import Conversation

        schema = Conversation.model_json_schema()

        assert schema["type"] == "object"
        assert "id" in schema["properties"]
        assert "participants" in schema["properties"]
        assert "created_at" in schema["properties"]
        assert set(schema["required"]) == {"id", "participants", "created_at"}


class TestTask:
    """Test suite for Task entity model."""

    def test_task_creation_minimal(self):
        """Test creating a Task with minimal required fields."""
        from datetime import datetime, timezone
        from asap.models.entities import Task

        task_id = generate_id()
        conv_id = generate_id()
        created_at = datetime.now(timezone.utc)

        task = Task(
            id=task_id,
            conversation_id=conv_id,
            status="submitted",
            created_at=created_at,
            updated_at=created_at,
        )

        assert task.id == task_id
        assert task.conversation_id == conv_id
        assert task.status == "submitted"
        assert task.parent_task_id is None
        assert task.progress is None

    def test_task_with_progress(self):
        """Test creating a Task with progress information."""
        from datetime import datetime, timezone
        from asap.models.entities import Task

        task = Task(
            id=generate_id(),
            conversation_id=generate_id(),
            status="working",
            progress={"percent": 45, "message": "Analyzing search results..."},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        assert task.status == "working"
        assert task.progress is not None
        assert task.progress["percent"] == 45
        assert "Analyzing" in task.progress["message"]

    def test_task_with_parent(self):
        """Test creating a Task with a parent task."""
        from datetime import datetime, timezone
        from asap.models.entities import Task

        parent_id = generate_id()
        task = Task(
            id=generate_id(),
            conversation_id=generate_id(),
            parent_task_id=parent_id,
            status="working",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        assert task.parent_task_id == parent_id

    def test_task_timestamps(self):
        """Test that Task timestamps are properly set."""
        from datetime import datetime, timezone
        from asap.models.entities import Task

        created = datetime.now(timezone.utc)
        task = Task(
            id=generate_id(),
            conversation_id=generate_id(),
            status="submitted",
            created_at=created,
            updated_at=created,
        )

        assert task.created_at == created
        assert task.updated_at == created
        assert task.created_at.tzinfo == timezone.utc

    def test_task_json_schema(self):
        """Test that Task generates valid JSON Schema."""
        from asap.models.entities import Task

        schema = Task.model_json_schema()

        assert schema["type"] == "object"
        assert "id" in schema["properties"]
        assert "conversation_id" in schema["properties"]
        assert "status" in schema["properties"]
        assert "progress" in schema["properties"]
        assert "created_at" in schema["properties"]
        assert "updated_at" in schema["properties"]

        required = set(schema["required"])
        assert "id" in required
        assert "conversation_id" in required
        assert "status" in required


class TestMessage:
    """Test suite for Message entity model."""

    def test_message_creation_minimal(self):
        """Test creating a Message with minimal required fields."""
        from datetime import datetime, timezone
        from asap.models.entities import Message

        msg_id = generate_id()
        task_id = generate_id()
        timestamp = datetime.now(timezone.utc)

        message = Message(
            id=msg_id,
            task_id=task_id,
            sender="urn:asap:agent:coordinator",
            role="user",
            parts=[],
            timestamp=timestamp,
        )

        assert message.id == msg_id
        assert message.task_id == task_id
        assert message.sender == "urn:asap:agent:coordinator"
        assert message.role == "user"
        assert len(message.parts) == 0

    def test_message_with_parts_reference(self):
        """Test creating a Message with parts reference."""
        from datetime import datetime, timezone
        from asap.models.entities import Message

        # Parts will be a list of part IDs (references)
        message = Message(
            id=generate_id(),
            task_id=generate_id(),
            sender="urn:asap:agent:test",
            role="assistant",
            parts=["part_01HX5K...", "part_01HX5L..."],
            timestamp=datetime.now(timezone.utc),
        )

        assert len(message.parts) == 2
        assert message.role == "assistant"

    def test_message_roles(self):
        """Test different message roles."""
        from datetime import datetime, timezone
        from asap.models.entities import Message

        for role in ["user", "assistant", "system"]:
            message = Message(
                id=generate_id(),
                task_id=generate_id(),
                sender="urn:asap:agent:test",
                role=role,
                parts=[],
                timestamp=datetime.now(timezone.utc),
            )
            assert message.role == role

    def test_message_timestamp(self):
        """Test that Message timestamp is timezone-aware."""
        from datetime import datetime, timezone
        from asap.models.entities import Message

        timestamp = datetime.now(timezone.utc)
        message = Message(
            id=generate_id(),
            task_id=generate_id(),
            sender="urn:asap:agent:test",
            role="user",
            parts=[],
            timestamp=timestamp,
        )

        assert message.timestamp == timestamp
        assert message.timestamp.tzinfo == timezone.utc

    def test_message_json_schema(self):
        """Test that Message generates valid JSON Schema."""
        from asap.models.entities import Message

        schema = Message.model_json_schema()

        assert schema["type"] == "object"
        assert "id" in schema["properties"]
        assert "task_id" in schema["properties"]
        assert "sender" in schema["properties"]
        assert "role" in schema["properties"]
        assert "parts" in schema["properties"]
        assert "timestamp" in schema["properties"]

        required = set(schema["required"])
        assert "id" in required
        assert "task_id" in required
        assert "sender" in required
        assert "role" in required
        assert "parts" in required
        assert "timestamp" in required


class TestArtifact:
    """Test suite for Artifact entity model."""

    def test_artifact_creation_minimal(self):
        """Test creating an Artifact with minimal required fields."""
        from datetime import datetime, timezone
        from asap.models.entities import Artifact

        artifact_id = generate_id()
        task_id = generate_id()
        created_at = datetime.now(timezone.utc)

        artifact = Artifact(
            id=artifact_id,
            task_id=task_id,
            name="Q3 Market Analysis Report",
            parts=["part_01HX5K..."],
            created_at=created_at,
        )

        assert artifact.id == artifact_id
        assert artifact.task_id == task_id
        assert artifact.name == "Q3 Market Analysis Report"
        assert len(artifact.parts) == 1

    def test_artifact_with_multiple_parts(self):
        """Test creating an Artifact with multiple parts."""
        from datetime import datetime, timezone
        from asap.models.entities import Artifact

        artifact = Artifact(
            id=generate_id(),
            task_id=generate_id(),
            name="Research Report",
            parts=["part_01HX5K...", "part_01HX5L...", "part_01HX5M..."],
            created_at=datetime.now(timezone.utc),
        )

        assert len(artifact.parts) == 3
        assert artifact.name == "Research Report"

    def test_artifact_timestamp(self):
        """Test that Artifact timestamp is timezone-aware."""
        from datetime import datetime, timezone
        from asap.models.entities import Artifact

        created = datetime.now(timezone.utc)
        artifact = Artifact(
            id=generate_id(),
            task_id=generate_id(),
            name="Test Artifact",
            parts=[],
            created_at=created,
        )

        assert artifact.created_at == created
        assert artifact.created_at.tzinfo == timezone.utc

    def test_artifact_json_schema(self):
        """Test that Artifact generates valid JSON Schema."""
        from asap.models.entities import Artifact

        schema = Artifact.model_json_schema()

        assert schema["type"] == "object"
        assert "id" in schema["properties"]
        assert "task_id" in schema["properties"]
        assert "name" in schema["properties"]
        assert "parts" in schema["properties"]
        assert "created_at" in schema["properties"]

        required = set(schema["required"])
        assert "id" in required
        assert "task_id" in required
        assert "name" in required
        assert "parts" in required
        assert "created_at" in required


class TestStateSnapshot:
    """Test suite for StateSnapshot entity model."""

    def test_state_snapshot_creation_minimal(self):
        """Test creating a StateSnapshot with minimal required fields."""
        from datetime import datetime, timezone
        from asap.models.entities import StateSnapshot

        snapshot_id = generate_id()
        task_id = generate_id()
        created_at = datetime.now(timezone.utc)

        snapshot = StateSnapshot(
            id=snapshot_id,
            task_id=task_id,
            version=1,
            data={"search_completed": True, "sources_analyzed": 15},
            created_at=created_at,
        )

        assert snapshot.id == snapshot_id
        assert snapshot.task_id == task_id
        assert snapshot.version == 1
        assert snapshot.data["search_completed"] is True
        assert snapshot.checkpoint is False  # Default

    def test_state_snapshot_with_checkpoint(self):
        """Test creating a StateSnapshot with checkpoint flag."""
        from datetime import datetime, timezone
        from asap.models.entities import StateSnapshot

        snapshot = StateSnapshot(
            id=generate_id(),
            task_id=generate_id(),
            version=3,
            data={"key_findings": ["finding1", "finding2"]},
            checkpoint=True,
            created_at=datetime.now(timezone.utc),
        )

        assert snapshot.version == 3
        assert snapshot.checkpoint is True
        assert len(snapshot.data["key_findings"]) == 2

    def test_state_snapshot_version_increment(self):
        """Test that StateSnapshot versions can be incremented."""
        from datetime import datetime, timezone
        from asap.models.entities import StateSnapshot

        task_id = generate_id()
        created = datetime.now(timezone.utc)

        # Create snapshots with incrementing versions
        snapshot1 = StateSnapshot(
            id=generate_id(), task_id=task_id, version=1, data={"step": 1}, created_at=created
        )

        snapshot2 = StateSnapshot(
            id=generate_id(), task_id=task_id, version=2, data={"step": 2}, created_at=created
        )

        snapshot3 = StateSnapshot(
            id=generate_id(), task_id=task_id, version=3, data={"step": 3}, created_at=created
        )

        assert snapshot1.version == 1
        assert snapshot2.version == 2
        assert snapshot3.version == 3
        assert snapshot1.task_id == snapshot2.task_id == snapshot3.task_id

    def test_state_snapshot_complex_data(self):
        """Test StateSnapshot with complex nested data."""
        from datetime import datetime, timezone
        from asap.models.entities import StateSnapshot

        complex_data = {
            "search_completed": True,
            "sources_analyzed": 15,
            "key_findings": [
                {"title": "Finding 1", "confidence": 0.95},
                {"title": "Finding 2", "confidence": 0.87},
            ],
            "metadata": {"total_time_ms": 45000, "tokens_used": 12500},
        }

        snapshot = StateSnapshot(
            id=generate_id(),
            task_id=generate_id(),
            version=1,
            data=complex_data,
            created_at=datetime.now(timezone.utc),
        )

        assert snapshot.data["sources_analyzed"] == 15
        assert len(snapshot.data["key_findings"]) == 2
        assert snapshot.data["metadata"]["tokens_used"] == 12500

    def test_state_snapshot_timestamp(self):
        """Test that StateSnapshot timestamp is timezone-aware."""
        from datetime import datetime, timezone
        from asap.models.entities import StateSnapshot

        created = datetime.now(timezone.utc)
        snapshot = StateSnapshot(
            id=generate_id(), task_id=generate_id(), version=1, data={}, created_at=created
        )

        assert snapshot.created_at == created
        assert snapshot.created_at.tzinfo == timezone.utc

    def test_state_snapshot_json_schema(self):
        """Test that StateSnapshot generates valid JSON Schema."""
        from asap.models.entities import StateSnapshot

        schema = StateSnapshot.model_json_schema()

        assert schema["type"] == "object"
        assert "id" in schema["properties"]
        assert "task_id" in schema["properties"]
        assert "version" in schema["properties"]
        assert "data" in schema["properties"]
        assert "checkpoint" in schema["properties"]
        assert "created_at" in schema["properties"]

        required = set(schema["required"])
        assert "id" in required
        assert "task_id" in required
        assert "version" in required
        assert "data" in required
        assert "created_at" in required

    def test_manifest_agent_id_urn_validation_failure(self) -> None:
        """Test that invalid agent URNs in manifest raise validation errors."""
        from asap.models.entities import Capability, Endpoint

        with pytest.raises(ValidationError) as exc_info:
            Manifest(
                id="invalid-urn",  # Should be urn:asap:agent:name format
                name="test-manifest",
                version="1.0.0",
                description="Test manifest",
                capabilities=Capability(asap_version="0.1", skills=[]),
                endpoints=Endpoint(asap="https://example.com"),
            )

        error_detail = exc_info.value.errors()[0]
        assert "must follow URN format" in error_detail["msg"]

    def test_manifest_version_validation_failure(self) -> None:
        """Test that invalid semantic versions raise validation errors."""
        from asap.models.entities import Capability, Endpoint

        with pytest.raises(ValidationError) as exc_info:
            Manifest(
                id="urn:asap:agent:test",
                name="test-manifest",
                version="invalid.version",  # Invalid semver
                description="Test manifest",
                capabilities=Capability(asap_version="0.1", skills=[]),
                endpoints=Endpoint(asap="https://example.com"),
            )

        error_detail = exc_info.value.errors()[0]
        assert "Invalid semantic version" in error_detail["msg"]

    def test_task_can_be_cancelled_method(self) -> None:
        """Test the can_be_cancelled method on Task."""
        from asap.models.entities import Task
        from asap.models.enums import TaskStatus
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        # Test SUBMITTED task can be cancelled
        submitted_task = Task(
            id="task_01HX5K4N000000000000000000",
            conversation_id="conv_01HX5K3MQVN8000000000000000",
            status=TaskStatus.SUBMITTED,
            created_at=now,
            updated_at=now,
        )
        assert submitted_task.can_be_cancelled()

        # Test WORKING task can be cancelled
        working_task = Task(
            id="task_01HX5K4N000000000000000001",
            conversation_id="conv_01HX5K3MQVN8000000000000000",
            status=TaskStatus.WORKING,
            created_at=now,
            updated_at=now,
        )
        assert working_task.can_be_cancelled()

        # Test COMPLETED task cannot be cancelled
        completed_task = Task(
            id="task_01HX5K4N000000000000000002",
            conversation_id="conv_01HX5K3MQVN8000000000000000",
            status=TaskStatus.COMPLETED,
            created_at=now,
            updated_at=now,
        )
        assert not completed_task.can_be_cancelled()
