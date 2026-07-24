"""Typed streaming adapter for LangGraph agent runs."""

import logging
from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


from langgraph_sdk.client import LangGraphClient
from langgraph_sdk.schema import (
    Checkpoint,
    Command,
    Input,
    StreamMode,
)
from pydantic import BaseModel, Field, JsonValue
from shared_common.schemas.ai_agent import (
    AgentCreateRunRequest,
    AgentCreateRunResponse,
    AgentDomainEvent,
    AgentGetStateEventsRequest,
    AgentJoinStreamRequest,
    AgentListRunsRequest,
    AgentListRunsResponse,
    AgentRAGFileImportRequest,
    AgentResumeRequest,
    AgentRunObject,
    AgentRunStatus,
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


def _parse_run_status(raw_status: str) -> AgentRunStatus:
    try:
        return AgentRunStatus(raw_status)
    except ValueError as error:
        logger.error(
            "Failed to parse raw agent run status into AgentRunStatus enum: raw_status=%s",
            raw_status,
            exc_info=True,
        )
        return AgentRunStatus.PENDING




class AgentRunStream:
    """Expose LangGraph runs as an iterator of stable domain events."""

    def __init__(self, client: LangGraphClient) -> None:
        """Initialize the stream adapter with a LangGraph SDK client."""
        self._client = client

    async def create_run(
        self,
        request: AgentCreateRunRequest,
    ) -> AgentCreateRunResponse:
        """Explicitly create a background agent run on a thread."""
        input_payload: Input | None = None
        if request.message is not None:
            message = _AgentUserMessageInput(
                content=request.message.content,
                additional_kwargs=request.message.metadata,
            )
            input_payload = _AgentSupervisorInput(messages=[message])

        try:
            await self._client.threads.create(
                thread_id=request.thread_id,
                if_exists="do_nothing",
            )
        except Exception as err:
            logger.warning(
                f"Thread registration note for thread_id={request.thread_id}: {err}"
            )

        run = await self._client.runs.create(
            thread_id=request.thread_id,
            assistant_id=request.assistant_id,
            input=input_payload,
            stream_mode=AGENT_STREAM_MODES,
            stream_subgraphs=True,
        )
        if isinstance(run, dict):
            run_id = str(run.get("run_id") or run.get("id") or "")
            raw_status = str(run.get("status", "pending"))
        else:
            run_id = str(getattr(run, "run_id", getattr(run, "id", str(run))))
            raw_status = str(getattr(run, "status", "pending"))

        return AgentCreateRunResponse(
            run_id=run_id,
            thread_id=request.thread_id,
            status=_parse_run_status(raw_status),
        )

    async def list_runs(
        self,
        request: AgentListRunsRequest,
    ) -> AgentListRunsResponse:
        """List all agent runs associated with a thread."""
        raw_runs = await self._client.runs.list(thread_id=request.thread_id)
        runs: list[AgentRunObject] = []
        for run in raw_runs:
            if isinstance(run, dict):
                run_id = str(run.get("run_id") or run.get("id") or "")
                thread_id = str(run.get("thread_id") or request.thread_id)
                raw_status = str(run.get("status", "pending"))
                raw_meta = run.get("metadata")
                metadata = raw_meta if isinstance(raw_meta, dict) else {}
            else:
                run_id = str(getattr(run, "run_id", getattr(run, "id", str(run))))
                thread_id = str(getattr(run, "thread_id", request.thread_id))
                raw_status = str(getattr(run, "status", "pending"))
                raw_meta = getattr(run, "metadata", {})
                metadata = raw_meta if isinstance(raw_meta, dict) else {}

            runs.append(
                AgentRunObject(
                    run_id=run_id,
                    thread_id=thread_id,
                    status=_parse_run_status(raw_status),
                    metadata=metadata,
                )
            )

        return AgentListRunsResponse(runs=runs)



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
            run_id=request.run_id,
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
                request.interrupt_id: request.response.response_data,
            }
        }

        return self._stream(
            thread_id=request.thread_id,
            assistant_id=AgentAssistantId.SUPERVISOR,
            run_id=request.run_id,
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

    def join_stream(
        self,
        request: AgentJoinStreamRequest,
    ) -> AsyncIterator[AgentDomainEvent]:
        """Re-join an active or completed run stream by run_id."""
        return self._join_stream(
            thread_id=request.thread_id,
            run_id=request.run_id,
        )

    async def _join_stream(
        self,
        thread_id: str,
        run_id: str,
    ) -> AsyncIterator[AgentDomainEvent]:
        projector = AgentRunProjector(thread_id=thread_id, run_id=run_id)
        try:
            raw_stream = self._client.runs.join_stream(
                thread_id=thread_id,
                run_id=run_id,
            )
            source_sequence = 0
            async for raw_event in raw_stream:
                for event in projector.process(raw_event, source_sequence):
                    logger.info(f"######## event kind:{event.kind} event_id:{event.event_id}")
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

    def get_state_events(
        self,
        request: AgentGetStateEventsRequest,
    ) -> AsyncIterator[AgentDomainEvent]:
        """Fetch historical domain events projected from thread state."""
        return self._get_state_events(
            thread_id=request.thread_id,
            run_id=request.run_id,
        )

    async def _get_state_events(
        self,
        thread_id: str,
        run_id: str | None = None,
    ) -> AsyncIterator[AgentDomainEvent]:
        projector = AgentRunProjector(thread_id=thread_id, run_id=run_id)
        try:
            thread_state = await self._client.threads.get_state(
                thread_id,
                subgraphs=True,
            )
            events = projector.project_thread_state(thread_state, run_id=run_id)
            for event in events:
                yield event
        except Exception as error:
            for event in projector.fail(error):
                yield event

    async def _stream(
        self,
        *,
        thread_id: str,
        assistant_id: AgentAssistantId,
        run_id: str | None = None,
        input_payload: Input | None = None,
        command: Command | None = None,
        checkpoint: Checkpoint | None = None,
    ) -> AsyncIterator[AgentDomainEvent]:
        projector = AgentRunProjector(thread_id=thread_id, run_id=run_id)

        try:
            # NOTE: run_id is intentionally NOT forwarded to runs.stream().
            # RunsClient.stream() creates a new run; on resume it locates the
            # interrupted state via the `checkpoint` parameter and provides the
            # user's response through `command`.  The original run_id is only
            # used by AgentRunProjector for internal tracking / correlation.
            raw_stream = self._client.runs.stream(
                thread_id=thread_id,
                assistant_id=assistant_id.value if hasattr(assistant_id, "value") else str(assistant_id),
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
                    logger.info(f"event kind:{event.kind} event_id:{event.event_id}")
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
