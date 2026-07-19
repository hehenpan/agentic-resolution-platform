"""Typed streaming adapter for LangGraph agent runs."""

from collections.abc import AsyncIterator

from langgraph_sdk.client import LangGraphClient
from langgraph_sdk.schema import (
    Checkpoint,
    Command,
    Input,
    StreamMode,
)
from pydantic import BaseModel, Field, JsonValue
from shared_common.schemas.ai_agent import (
    AgentDomainEvent,
    AgentRAGFileImportRequest,
    AgentResumeRequest,
    AgentTurnRequest,
)

from ai_agent_sdk.agent_run_projector import AgentRunProjector
from ai_agent_sdk.assistants import AgentAssistantId

AGENT_STREAM_MODES: tuple[StreamMode, ...] = (
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


class _AgentUserMessageInput(BaseModel):
    role: str = Field(
        default="user",
        description="LangChain chat role for the submitted message.",
    )
    content: str = Field(description="Plain text content for the user message.")
    additional_kwargs: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Additional LangChain message metadata.",
    )


class _AgentSupervisorInput(BaseModel):
    messages: list[_AgentUserMessageInput] = Field(
        description="Messages submitted to the supervisor graph."
    )


class AgentRunStream:
    """Expose LangGraph runs as an iterator of stable domain events."""

    def __init__(self, client: LangGraphClient) -> None:
        """Initialize the stream adapter with a LangGraph SDK client."""
        self._client = client

    def stream_turn(
        self,
        request: AgentTurnRequest,
    ) -> AsyncIterator[AgentDomainEvent]:
        """Stream one ordinary supervisor turn."""
        message = _AgentUserMessageInput(
            content=request.message.content,
            additional_kwargs=request.message.metadata,
        )
        input_payload: Input = _AgentSupervisorInput(messages=[message])
        return self._stream(
            thread_id=request.thread_id,
            assistant_id=AgentAssistantId.SUPERVISOR,
            input_payload=input_payload,
        )

    def resume_turn(
        self,
        request: AgentResumeRequest,
    ) -> AsyncIterator[AgentDomainEvent]:
        """Resume one interrupted supervisor turn."""
        cursor = request.resume_cursor
        checkpoint: Checkpoint = {
            "thread_id": request.thread_id,
            "checkpoint_id": cursor.checkpoint_id,
            "checkpoint_ns": cursor.checkpoint_ns,
            "checkpoint_map": cursor.checkpoint_map,
        }
        command: Command = {
            "resume": {
                request.interrupt_id: request.response.data,
            }
        }
        return self._stream(
            thread_id=request.thread_id,
            assistant_id=AgentAssistantId.SUPERVISOR,
            command=command,
            checkpoint=checkpoint,
        )

    def stream_rag_file_import(
        self,
        request: AgentRAGFileImportRequest,
    ) -> AsyncIterator[AgentDomainEvent]:
        """Stream one RAG file import operation."""
        input_payload: Input = request.payload
        return self._stream(
            thread_id=request.thread_id,
            assistant_id=AgentAssistantId.FILE_INGEST,
            input_payload=input_payload,
        )

    async def _stream(
        self,
        *,
        thread_id: str,
        assistant_id: AgentAssistantId,
        input_payload: Input | None = None,
        command: Command | None = None,
        checkpoint: Checkpoint | None = None,
    ) -> AsyncIterator[AgentDomainEvent]:
        projector = AgentRunProjector(thread_id=thread_id)

        try:
            raw_stream = self._client.runs.stream(
                thread_id=thread_id,
                assistant_id=assistant_id.value,
                input=input_payload,
                command=command,
                checkpoint=checkpoint,
                stream_mode=AGENT_STREAM_MODES,
                stream_subgraphs=True,
                version="v2",
            )
            source_sequence = 0
            async for raw_event in raw_stream:
                for event in projector.process(raw_event, source_sequence):
                    yield event
                source_sequence += 1

            thread_state = await self._client.threads.get_state(
                thread_id,
                subgraphs=True,
            )
            for event in projector.finalize(thread_state):
                yield event
        except Exception as error:
            for event in projector.fail(error):
                yield event
