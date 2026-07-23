"""Tests for the typed LangGraph agent run stream adapter."""

from collections.abc import AsyncIterator

import pytest
from pydantic import BaseModel
from shared_common.schemas.ai_agent import (
    AgentCustomStreamEventKind,
    AgentOutputProduced,
    AgentOutputSchemaId,
    AgentProgressReported,
    AgentProgressStatus,
    AgentRAGFileImportRequest,
    AgentResumeCursor,
    AgentResumeRequest,
    AgentRunCompleted,
    AgentTurnRequest,
    HumanInputResponse,
    RAGFileImportPayload,
    StructuredDataPart,
    UserMessageInput,
)

from ai_agent_sdk import AgentAssistantId, AgentRunStream

OUTPUT_ID = "11111111-1111-5111-8111-111111111111"
PROGRESS_ID = "33333333-3333-5333-8333-333333333333"


class FakeRunsClient:
    def __init__(self, events: list[dict[str, object]]) -> None:
        self.events = events
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(kwargs)
        return {"run_id": "run-test-123", "status": "pending"}

    def stream(self, **kwargs: object) -> AsyncIterator[dict[str, object]]:
        self.calls.append(kwargs)

        async def iterate() -> AsyncIterator[dict[str, object]]:
            for event in self.events:
                yield event

        return iterate()

    def join_stream(self, **kwargs: object) -> AsyncIterator[dict[str, object]]:
        self.calls.append(kwargs)

        async def iterate() -> AsyncIterator[dict[str, object]]:
            for event in self.events:
                yield event

        return iterate()

    async def list(self, thread_id: str) -> list[dict[str, object]]:
        self.calls.append({"thread_id": thread_id})
        return [
            {
                "run_id": "run-test-123",
                "thread_id": thread_id,
                "status": "pending",
                "metadata": {"foo": "bar"},
            }
        ]




class FakeThreadsClient:
    def __init__(self, state: dict[str, object]) -> None:
        self.state = state
        self.calls: list[tuple[str, bool]] = []

    async def create(
        self,
        thread_id: str | None = None,
        if_exists: str | None = None,
        **kwargs: object,
    ) -> dict[str, object]:
        return {"thread_id": thread_id or "thread-created"}

    async def get_state(
        self,
        thread_id: str,
        *,
        subgraphs: bool,
    ) -> dict[str, object]:
        self.calls.append((thread_id, subgraphs))
        return self.state


class FakeLangGraphClient:
    def __init__(
        self,
        events: list[dict[str, object]],
        state: dict[str, object],
    ) -> None:
        self.runs = FakeRunsClient(events)
        self.threads = FakeThreadsClient(state)


def _client() -> FakeLangGraphClient:
    output = {
        "output_id": OUTPUT_ID,
        "parts": [{"kind": "text", "text": "Policy answer"}],
    }
    return FakeLangGraphClient(
        events=[
            {"type": "metadata", "data": {}},
            {
                "type": "custom",
                "data": {
                    "kind": AgentCustomStreamEventKind.PROGRESS.value,
                    "schema_version": "1",
                    "progress_id": PROGRESS_ID,
                    "operation": "policy_retrieval",
                    "status": AgentProgressStatus.STARTED.value,
                    "progress_current": None,
                    "progress_total": None,
                    "details": {},
                },
            },
            {"type": "updates", "data": {"node": {"outputs": [output]}}},
            {"type": "messages/complete", "data": [{"content": "ignored"}]},
        ],
        state={"values": {"outputs": [output]}, "interrupts": []},
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_stream_turn_calls_v2_supervisor_and_yields_only_domain_events() -> None:
    client = _client()
    stream = AgentRunStream(client)  # type: ignore[arg-type]
    request = AgentTurnRequest(
        thread_id="thread-1",
        message=UserMessageInput(
            content="What is the return policy?",
            metadata={"channel": "support"},
        ),
    )

    events = [event async for event in stream.stream_turn(request)]

    assert len(events) == 3
    assert isinstance(events[0], AgentProgressReported)
    assert events[0].event_id == PROGRESS_ID
    assert isinstance(events[1], AgentOutputProduced)
    assert isinstance(events[2], AgentRunCompleted)
    call = client.runs.calls[0]
    assert call["thread_id"] == "thread-1"
    assert call["assistant_id"] == AgentAssistantId.SUPERVISOR.value
    assert call["stream_mode"] == (
        "values",
        "messages",
        "updates",
        "events",
        "tasks",
        "checkpoints",
        "debug",
        "custom",
        "messages-tuple",
    )
    assert call["stream_subgraphs"] is True
    assert call["version"] == "v2"
    input_payload = call["input"]
    assert isinstance(input_payload, BaseModel)
    assert input_payload.model_dump() == {
        "messages": [
            {
                "role": "user",
                "content": "What is the return policy?",
                "additional_kwargs": {"channel": "support"},
            }
        ]
    }
    assert client.threads.calls == [("thread-1", True)]


@pytest.mark.anyio
async def test_resume_turn_uses_interrupt_and_resume_cursor() -> None:
    client = FakeLangGraphClient(
        events=[{"type": "metadata", "data": {}}],
        state={"values": {}, "interrupts": []},
    )
    stream = AgentRunStream(client)  # type: ignore[arg-type]
    request = AgentResumeRequest(
        thread_id="thread-1",
        interrupt_id="interrupt-1",
        resume_cursor=AgentResumeCursor(
            checkpoint_id="checkpoint-1",
            checkpoint_ns="supervisor",
            checkpoint_map={"root": "checkpoint-root"},
        ),
        response=HumanInputResponse(schema_id="test_schema", response_data={"approved": True}),

    )

    events = [event async for event in stream.resume_turn(request)]

    assert len(events) == 1
    assert isinstance(events[0], AgentRunCompleted)
    call = client.runs.calls[0]
    assert call["thread_id"] == "thread-1"
    assert call["assistant_id"] == AgentAssistantId.SUPERVISOR.value
    assert call["input"] is None
    assert call["command"] == {
        "resume": {"interrupt-1": {"approved": True}},
    }
    assert call["checkpoint"] == {
        "thread_id": "thread-1",
        "checkpoint_id": "checkpoint-1",
        "checkpoint_ns": "supervisor",
        "checkpoint_map": {"root": "checkpoint-root"},
    }


@pytest.mark.anyio
async def test_stream_rag_file_import_uses_file_ingest_assistant() -> None:
    output = {
        "output_id": OUTPUT_ID,
        "parts": [
            {
                "kind": "structured_data",
                "schema_id": AgentOutputSchemaId.RAG_FILE_IMPORT_RESULT_V1.value,
                "data": {
                    "file_id": 1,
                    "file_name": "policy.md",
                    "status": "success",
                },
            }
        ],
    }
    client = FakeLangGraphClient(
        events=[
            {"type": "updates", "data": {"node": {"outputs": [output]}}},
        ],
        state={"values": {"outputs": [output]}, "interrupts": []},
    )
    stream = AgentRunStream(client)  # type: ignore[arg-type]
    request = AgentRAGFileImportRequest(
        thread_id="rag-import:1:operation-1",
        payload=RAGFileImportPayload(
            file_id=1,
            file_name="policy.md",
            file_size=6,
            file_owner_id=2,
            file_tenant_id=3,
            file_content=b"policy",
            extra_meta={"source": "upload"},
        ),
    )

    events = [event async for event in stream.stream_rag_file_import(request)]

    assert len(events) == 2
    assert isinstance(events[0], AgentOutputProduced)
    assert isinstance(events[0].output.parts[0], StructuredDataPart)
    assert (
        events[0].output.parts[0].schema_id
        == AgentOutputSchemaId.RAG_FILE_IMPORT_RESULT_V1.value
    )
    assert isinstance(events[1], AgentRunCompleted)
    call = client.runs.calls[0]
    assert call["thread_id"] == request.thread_id
    assert call["assistant_id"] == AgentAssistantId.FILE_INGEST.value
    assert call["input"] == request.payload
    assert call["command"] is None
    assert call["checkpoint"] is None
    assert client.threads.calls == [(request.thread_id, True)]


@pytest.mark.anyio
async def test_stream_failure_yields_failed_domain_event_without_final_state() -> None:
    class FailingRunsClient(FakeRunsClient):
        def stream(self, **kwargs: object) -> AsyncIterator[dict[str, object]]:
            async def fail() -> AsyncIterator[dict[str, object]]:
                raise RuntimeError("transport secret")
                yield {}

            return fail()

    client = FakeLangGraphClient(events=[], state={})
    client.runs = FailingRunsClient([])
    stream = AgentRunStream(client)  # type: ignore[arg-type]
    request = AgentTurnRequest(
        thread_id="thread-1",
        message=UserMessageInput(content="Question"),
    )

    events = [event async for event in stream.stream_turn(request)]

    assert len(events) == 1
    assert events[0].kind == "agent.run_failed"
    assert client.threads.calls == []


@pytest.mark.anyio
async def test_create_run_and_join_stream_and_get_state_events() -> None:
    from shared_common.schemas.ai_agent import (
        AgentCreateRunRequest,
        AgentGetStateEventsRequest,
        AgentJoinStreamRequest,
    )

    client = _client()
    stream = AgentRunStream(client)  # type: ignore[arg-type]

    # Test create_run
    create_req = AgentCreateRunRequest(
        thread_id="thread-reconnect",
        assistant_id="supervisor_graph",
        message=UserMessageInput(content="Hello"),
    )
    create_res = await stream.create_run(create_req)
    assert create_res.run_id == "run-test-123"
    assert create_res.thread_id == "thread-reconnect"
    create_call = client.runs.calls[0]
    assert create_call["thread_id"] == "thread-reconnect"
    assert create_call["assistant_id"] == "supervisor_graph"
    create_input = create_call["input"]
    assert isinstance(create_input, BaseModel)
    assert create_input.model_dump() == {
        "messages": [
            {
                "role": "user",
                "content": "Hello",
                "additional_kwargs": {},
            }
        ]
    }

    # Test join_stream
    join_req = AgentJoinStreamRequest(
        thread_id="thread-reconnect",
        run_id="run-test-123",
    )
    join_events = [event async for event in stream.join_stream(join_req)]
    assert len(join_events) == 3
    assert join_events[0].run_id == "run-test-123"

    # Test get_state_events
    state_req = AgentGetStateEventsRequest(
        thread_id="thread-reconnect",
        run_id="run-test-123",
    )
    state_events = [event async for event in stream.get_state_events(state_req)]
    assert len(state_events) == 2
    assert state_events[0].run_id == "run-test-123"


@pytest.mark.anyio
async def test_list_runs() -> None:
    from shared_common.schemas.ai_agent import AgentListRunsRequest

    client = _client()
    stream = AgentRunStream(client)  # type: ignore[arg-type]

    req = AgentListRunsRequest(thread_id="thread-list-test")
    res = await stream.list_runs(req)

    assert len(res.runs) == 1
    assert res.runs[0].run_id == "run-test-123"
    assert res.runs[0].thread_id == "thread-list-test"
    assert res.runs[0].status == "pending"
    assert res.runs[0].metadata == {"foo": "bar"}

