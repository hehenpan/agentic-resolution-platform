"""Tests for the public AI Agent client streaming interface."""

from collections.abc import AsyncIterator

import pytest
from shared_common.schemas.ai_agent import (
    AgentDomainEvent,
    AgentOutput,
    AgentOutputProduced,
    AgentRAGFileImportRequest,
    AgentResumeCursor,
    AgentResumeRequest,
    AgentTurnRequest,
    HumanInputResponse,
    RAGFileImportPayload,
    TextPart,
    UserMessageInput,
)

from microservice_client.ai_agent_client import AIAgentServerLangGraph


class FakeAgentRunStream:
    def __init__(self, event: AgentOutputProduced) -> None:
        self.event = event
        self.turn_request: AgentTurnRequest | None = None
        self.resume_request: AgentResumeRequest | None = None
        self.rag_file_import_request: AgentRAGFileImportRequest | None = None

    def stream_turn(
        self,
        request: AgentTurnRequest,
    ) -> AsyncIterator[AgentDomainEvent]:
        self.turn_request = request
        return self._events()

    def resume_turn(
        self,
        request: AgentResumeRequest,
    ) -> AsyncIterator[AgentDomainEvent]:
        self.resume_request = request
        return self._events()

    def stream_rag_file_import(
        self,
        request: AgentRAGFileImportRequest,
    ) -> AsyncIterator[AgentDomainEvent]:
        self.rag_file_import_request = request
        return self._events()

    async def _events(self) -> AsyncIterator[AgentDomainEvent]:
        yield self.event


def _client() -> tuple[AIAgentServerLangGraph, FakeAgentRunStream]:
    output_id = "11111111-1111-5111-8111-111111111111"
    event = AgentOutputProduced(
        event_id=output_id,
        thread_id="thread-1",
        sequence=0,
        created_at=1_725_000_000,
        output=AgentOutput(
            output_id=output_id,
            parts=[TextPart(text="Answer")],
        ),
    )
    run_stream = FakeAgentRunStream(event)
    client = AIAgentServerLangGraph.__new__(AIAgentServerLangGraph)
    client.run_stream = run_stream  # type: ignore[assignment]
    return client, run_stream


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_client_stream_turn_exposes_only_domain_events() -> None:
    client, run_stream = _client()
    request = AgentTurnRequest(
        thread_id="thread-1",
        message=UserMessageInput(content="Question"),
    )

    events = [event async for event in client.stream_turn(request)]

    assert events == [run_stream.event]
    assert run_stream.turn_request == request


@pytest.mark.anyio
async def test_client_resume_turn_exposes_only_domain_events() -> None:
    client, run_stream = _client()
    request = AgentResumeRequest(
        thread_id="thread-1",
        interrupt_id="interrupt-1",
        resume_cursor=AgentResumeCursor(checkpoint_id="checkpoint-1"),
        response=HumanInputResponse(data=True),
    )

    events = [event async for event in client.resume_turn(request)]

    assert events == [run_stream.event]
    assert run_stream.resume_request == request


@pytest.mark.anyio
async def test_client_stream_rag_file_import_exposes_only_domain_events() -> None:
    client, run_stream = _client()
    request = AgentRAGFileImportRequest(
        thread_id="rag-import:1:operation-1",
        payload=RAGFileImportPayload(
            file_id=1,
            file_name="policy.md",
            file_size=6,
            file_owner_id=2,
            file_tenant_id=3,
            file_content=b"policy",
        ),
    )

    events = [event async for event in client.stream_rag_file_import(request)]

    assert events == [run_stream.event]
    assert run_stream.rag_file_import_request == request
