"""Consume typed AI Agent events for one RAG file import operation."""

from time import time_ns
from uuid import NAMESPACE_URL, uuid5

from loguru import logger
from pydantic import BaseModel, Field, ValidationError
from sqlmodel import Session

from app.models.models import FileInfo, FileSyncStatus
from microservice_client.ai_agent_client import AIAgentServerInterface
from shared_common.schemas.ai_agent import (
    AgentDomainEvent,
    AgentOutputProduced,
    AgentOutputSchemaId,
    AgentRAGFileImportRequest,
    AgentRunCompleted,
    AgentRunFailed,
    AgentRunInterrupted,
    HumanInputRequested,
    RAGFileImportPayload,
    RAGFileImportResult,
    StructuredDataPart,
)

RAG_FILE_IMPORT_THREAD_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "agentic-resolution-platform/rag-file-import-thread",
)


def _unix_time_ms() -> int:
    return time_ns() // 1_000_000


def build_rag_file_import_thread_id(
    *,
    file_id: int,
    operation_id: str,
) -> str:
    """Build a thread ID using the current millisecond identity seed."""
    if not operation_id.strip():
        raise ValueError("RAG file import operation ID must not be empty")

    timestamp_ms = _unix_time_ms()
    seed = f"{file_id}:{operation_id}:{timestamp_ms}"
    thread_uuid = uuid5(RAG_FILE_IMPORT_THREAD_NAMESPACE, seed)
    return f"rag-file-import:{thread_uuid}"


class RAGFileImportError(RuntimeError):
    """Report an invalid or unsuccessful RAG file import operation."""


class _RAGFileImportStreamState(BaseModel):
    result: RAGFileImportResult | None = None
    output_id: str | None = None
    terminal: AgentRunCompleted | AgentRunInterrupted | AgentRunFailed | None = None
    human_input_requested: bool = False
    protocol_errors: list[str] = Field(default_factory=list)


class RAGFileImportService:
    """Run a RAG file import and persist its validated completion status."""

    def __init__(
        self,
        *,
        dbsession: Session,
        agent_client: AIAgentServerInterface,
    ) -> None:
        self._dbsession = dbsession
        self._agent_client = agent_client

    async def import_file(
        self,
        *,
        payload: RAGFileImportPayload,
        operation_id: str,
    ) -> RAGFileImportResult:
        """Import one pending file and return its validated structured result."""
        file_info = self._get_file(payload.file_id)
        self._validate_file_identity(file_info, payload)

        if file_info.vector_db_sync_status == FileSyncStatus.SYNCED:
            return RAGFileImportResult(
                file_id=file_info.file_id,
                file_name=file_info.file_name,
            )
        if file_info.vector_db_sync_status == FileSyncStatus.FAILED:
            logger.error(
                f"RAG file import retry requires an explicit retry policy: "
                f"file_id={payload.file_id}"
            )
            raise RAGFileImportError("Failed RAG file imports cannot be retried")

        try:
            thread_id = build_rag_file_import_thread_id(
                file_id=payload.file_id,
                operation_id=operation_id,
            )
            request = AgentRAGFileImportRequest(
                thread_id=thread_id,
                payload=payload,
            )
            result = await self._consume_stream(request)
        except Exception as error:
            logger.error(
                f"RAG file import failed: file_id={payload.file_id}, "
                f"error={type(error).__name__}: {error}"
            )
            self._set_sync_status(file_info, FileSyncStatus.FAILED)
            if isinstance(error, RAGFileImportError):
                raise
            raise RAGFileImportError("RAG file import did not complete") from error

        self._set_sync_status(file_info, FileSyncStatus.SYNCED)
        return result

    async def _consume_stream(
        self,
        request: AgentRAGFileImportRequest,
    ) -> RAGFileImportResult:
        state = _RAGFileImportStreamState()
        async for event in self._agent_client.stream_rag_file_import(request):
            self._consume_event(state, event, request.payload)
        return self._validate_completed_stream(state)

    def _consume_event(
        self,
        state: _RAGFileImportStreamState,
        event: AgentDomainEvent,
        payload: RAGFileImportPayload,
    ) -> None:
        if isinstance(event, AgentOutputProduced):
            self._consume_output(state, event, payload)
            return
        if isinstance(event, HumanInputRequested):
            state.human_input_requested = True
            return
        if isinstance(event, (AgentRunCompleted, AgentRunInterrupted, AgentRunFailed)):
            if state.terminal is not None:
                state.protocol_errors.append("Multiple terminal events were received")
                return
            state.terminal = event

    @staticmethod
    def _consume_output(
        state: _RAGFileImportStreamState,
        event: AgentOutputProduced,
        payload: RAGFileImportPayload,
    ) -> None:
        for part in event.output.parts:
            if not isinstance(part, StructuredDataPart):
                continue
            if part.schema_id != AgentOutputSchemaId.RAG_FILE_IMPORT_RESULT_V1.value:
                continue
            try:
                result = RAGFileImportResult.model_validate(part.data)
            except ValidationError as error:
                state.protocol_errors.append(f"Invalid RAG file import result: {error}")
                continue
            if result.file_id != payload.file_id or result.file_name != payload.file_name:
                state.protocol_errors.append(
                    "RAG file import result does not match the requested file"
                )
                continue
            if state.output_id is not None and (
                state.output_id != event.output.output_id or state.result != result
            ):
                state.protocol_errors.append(
                    "Multiple different RAG file import outputs were received"
                )
                continue
            state.output_id = event.output.output_id
            state.result = result

    @staticmethod
    def _validate_completed_stream(
        state: _RAGFileImportStreamState,
    ) -> RAGFileImportResult:
        if state.protocol_errors:
            raise RAGFileImportError("; ".join(state.protocol_errors))
        if state.human_input_requested:
            raise RAGFileImportError("RAG file import requested unsupported human input")
        if state.terminal is None:
            raise RAGFileImportError("RAG file import stream ended without a terminal event")
        if isinstance(state.terminal, AgentRunFailed):
            raise RAGFileImportError(
                f"AI Agent failed the RAG file import: {state.terminal.error.code}"
            )
        if isinstance(state.terminal, AgentRunInterrupted):
            raise RAGFileImportError("RAG file import was interrupted")
        if state.result is None or state.output_id is None:
            raise RAGFileImportError(
                "RAG file import completed without a structured result"
            )
        if state.output_id not in state.terminal.output_ids:
            raise RAGFileImportError(
                "RAG file import completion does not reference its result output"
            )
        return state.result

    def _get_file(self, file_id: int) -> FileInfo:
        file_info = self._dbsession.get(FileInfo, file_id)
        if file_info is None:
            logger.error(f"RAG file import file does not exist: file_id={file_id}")
            raise RAGFileImportError("RAG file import file does not exist")
        return file_info

    @staticmethod
    def _validate_file_identity(
        file_info: FileInfo,
        payload: RAGFileImportPayload,
    ) -> None:
        if (
            file_info.file_name != payload.file_name
            or file_info.owner_user_id != payload.file_owner_id
            or file_info.tenant_id != payload.file_tenant_id
        ):
            logger.error(
                f"RAG file import payload does not match FileInfo: "
                f"file_id={payload.file_id}"
            )
            raise RAGFileImportError("RAG file import payload identity is invalid")

    def _set_sync_status(
        self,
        file_info: FileInfo,
        status: FileSyncStatus,
    ) -> None:
        try:
            file_info.vector_db_sync_status = status
            self._dbsession.add(file_info)
            self._dbsession.commit()
            self._dbsession.refresh(file_info)
        except Exception as error:
            self._dbsession.rollback()
            logger.error(
                f"Failed to update RAG file sync status: "
                f"file_id={file_info.file_id}, status={status.name}, error={error}"
            )
            raise
