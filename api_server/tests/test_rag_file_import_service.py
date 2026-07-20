"""Tests for consuming typed RAG file import domain events."""

from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from app.models.models import (
    FileInfo,
    FileStatus,
    FileStorageType,
    FileSyncStatus,
)
from app.services.rag_file_import_service import (
    RAGFileImportError,
    RAGFileImportService,
    build_rag_file_import_thread_id,
)
from microservice_client.ai_agent_client import AIAgentServerInterface
from sqlmodel import Session

from shared_common.schemas.ai_agent import (
    AgentCreateRunRequest,
    AgentCreateRunResponse,
    AgentDomainEvent,
    AgentError,
    AgentGetStateEventsRequest,
    AgentJoinStreamRequest,
    AgentOutput,
    AgentOutputProduced,
    AgentOutputSchemaId,
    AgentProgressReported,
    AgentProgressStatus,
    AgentRAGFileImportRequest,
    AgentResumeRequest,
    AgentRunCompleted,
    AgentRunFailed,
    AgentRunInterrupted,
    AgentTurnRequest,
    RAGFileImportPayload,
    StructuredDataPart,
)


FILE_ID = 101
FILE_NAME = "policy.md"
OWNER_ID = 202
TENANT_ID = 303
OUTPUT_ID = "11111111-1111-5111-8111-111111111111"
CREATED_AT = 1_725_000_000


class FakeAgentClient(AIAgentServerInterface):
    def __init__(
        self,
        events: list[AgentDomainEvent] | None = None,
        stream_error: Exception | None = None,
    ) -> None:
        self.events = events or []
        self.stream_error = stream_error
        self.requests: list[AgentRAGFileImportRequest] = []

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def stream_turn(
        self,
        request: AgentTurnRequest,
    ) -> AsyncIterator[AgentDomainEvent]:
        return self._empty_stream()

    def resume_turn(
        self,
        request: AgentResumeRequest,
    ) -> AsyncIterator[AgentDomainEvent]:
        return self._empty_stream()

    def stream_rag_file_import(
        self,
        request: AgentRAGFileImportRequest,
    ) -> AsyncIterator[AgentDomainEvent]:
        self.requests.append(request)

        async def iterate() -> AsyncIterator[AgentDomainEvent]:
            for event in self.events:
                yield event
            if self.stream_error is not None:
                raise self.stream_error

        return iterate()

    async def create_run(
        self,
        request: AgentCreateRunRequest,
    ) -> AgentCreateRunResponse:
        return AgentCreateRunResponse(
            run_id="run-mock-123",
            thread_id=request.thread_id,
            status="pending",
        )

    def join_stream(
        self,
        request: AgentJoinStreamRequest,
    ) -> AsyncIterator[AgentDomainEvent]:
        return self._empty_stream()

    def get_state_events(
        self,
        request: AgentGetStateEventsRequest,
    ) -> AsyncIterator[AgentDomainEvent]:
        return self._empty_stream()

    @staticmethod
    async def _empty_stream() -> AsyncIterator[AgentDomainEvent]:
        if False:
            yield AgentRunCompleted(
                event_id="unused",
                thread_id="unused",
                run_id="run-mock-123",
                sequence=0,
                created_at=CREATED_AT,
            )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _payload() -> RAGFileImportPayload:
    return RAGFileImportPayload(
        file_id=FILE_ID,
        file_name=FILE_NAME,
        file_size=6,
        file_owner_id=OWNER_ID,
        file_tenant_id=TENANT_ID,
        file_content=b"policy",
    )


def _store_file(
    db_session: Session,
    sync_status: FileSyncStatus = FileSyncStatus.PENDING,
) -> FileInfo:
    file_info = FileInfo(
        file_id=FILE_ID,
        tenant_id=TENANT_ID,
        owner_user_id=OWNER_ID,
        owner_email="owner@example.com",
        file_name=FILE_NAME,
        file_type="md",
        file_md5_hash="hash",
        file_storage_location="policy.md",
        file_storage_type=FileStorageType.LOCAL,
        file_size=6,
        create_ts=CREATED_AT,
        status=FileStatus.ACTIVE,
        vector_db_sync_status=sync_status,
    )
    db_session.add(file_info)
    db_session.commit()
    db_session.refresh(file_info)
    return file_info


def _output_event(
    *,
    output_id: str = OUTPUT_ID,
    schema_id: str = AgentOutputSchemaId.RAG_FILE_IMPORT_RESULT_V1.value,
    data: object | None = None,
    sequence: int = 0,
) -> AgentOutputProduced:
    result_data = data or {
        "file_id": FILE_ID,
        "file_name": FILE_NAME,
        "status": "success",
    }
    return AgentOutputProduced(
        event_id=output_id,
        thread_id="thread-1",
        run_id="run-mock-123",
        sequence=sequence,
        created_at=CREATED_AT,
        output=AgentOutput(
            output_id=output_id,
            parts=[StructuredDataPart(schema_id=schema_id, data=result_data)],
        ),
    )


def _completed(
    output_ids: list[str] | None = None,
    sequence: int = 1,
) -> AgentRunCompleted:
    return AgentRunCompleted(
        event_id="completed-1",
        thread_id="thread-1",
        run_id="run-mock-123",
        sequence=sequence,
        created_at=CREATED_AT,
        output_ids=output_ids if output_ids is not None else [OUTPUT_ID],
    )



def _service(
    db_session: Session,
    client: FakeAgentClient,
) -> RAGFileImportService:
    return RAGFileImportService(
        dbsession=db_session,
        agent_client=client,
    )


def _sync_status(db_session: Session) -> FileSyncStatus:
    db_session.expire_all()
    file_info = db_session.get(FileInfo, FILE_ID)
    assert file_info is not None
    return file_info.vector_db_sync_status


@pytest.mark.anyio
async def test_import_file_marks_valid_completed_result_as_synced(
    db_session: Session,
) -> None:
    _store_file(db_session)
    client = FakeAgentClient([_output_event(), _completed()])

    result = await _service(db_session, client).import_file(
        payload=_payload(),
        operation_id="operation-1",
    )

    assert result.file_id == FILE_ID
    assert result.file_name == FILE_NAME
    assert _sync_status(db_session) == FileSyncStatus.SYNCED
    thread_id = client.requests[0].thread_id
    assert thread_id.startswith("rag-file-import:")
    UUID(thread_id.removeprefix("rag-file-import:"))


@pytest.mark.anyio
async def test_import_file_ignores_progress_before_valid_completion(
    db_session: Session,
) -> None:
    _store_file(db_session)
    progress = AgentProgressReported(
        event_id="progress-1",
        thread_id="thread-1",
        run_id="run-mock-123",
        sequence=0,
        created_at=CREATED_AT,
        operation="rag_file_import",
        status=AgentProgressStatus.IN_PROGRESS,
    )
    client = FakeAgentClient(
        [_output_event(sequence=1), progress, _completed(sequence=2)]
    )

    await _service(db_session, client).import_file(
        payload=_payload(),
        operation_id="operation-1",
    )

    assert _sync_status(db_session) == FileSyncStatus.SYNCED


@pytest.mark.anyio
@pytest.mark.parametrize(
    "events",
    [
        [_completed()],
        [
            _output_event(schema_id="unsupported.schema.v1"),
            _completed(),
        ],
        [
            _output_event(data={"file_id": FILE_ID}),
            _completed(),
        ],
        [
            _output_event(
                data={
                    "file_id": FILE_ID + 1,
                    "file_name": FILE_NAME,
                    "status": "success",
                }
            ),
            _completed(),
        ],
        [_output_event(), _completed(output_ids=["different-output"])],
        [_output_event()],
    ],
    ids=[
        "missing-result",
        "wrong-schema",
        "invalid-result",
        "mismatched-file",
        "unreferenced-output",
        "missing-terminal",
    ],
)
async def test_import_file_marks_invalid_completed_stream_as_failed(
    db_session: Session,
    events: list[AgentDomainEvent],
) -> None:
    _store_file(db_session)
    client = FakeAgentClient(events)

    with pytest.raises(RAGFileImportError):
        await _service(db_session, client).import_file(
            payload=_payload(),
            operation_id="operation-1",
        )

    assert _sync_status(db_session) == FileSyncStatus.FAILED


@pytest.mark.anyio
async def test_import_file_rejects_multiple_different_results(
    db_session: Session,
) -> None:
    _store_file(db_session)
    second_output_id = "22222222-2222-5222-8222-222222222222"
    client = FakeAgentClient(
        [
            _output_event(),
            _output_event(output_id=second_output_id, sequence=1),
            _completed(output_ids=[OUTPUT_ID, second_output_id], sequence=2),
        ]
    )

    with pytest.raises(RAGFileImportError):
        await _service(db_session, client).import_file(
            payload=_payload(),
            operation_id="operation-1",
        )

    assert _sync_status(db_session) == FileSyncStatus.FAILED


@pytest.mark.anyio
@pytest.mark.parametrize(
    "terminal",
    [
        AgentRunFailed(
            event_id="failed-1",
            thread_id="thread-1",
            run_id="run-mock-123",
            sequence=0,
            created_at=CREATED_AT,
            error=AgentError(
                code="AGENT_RUN_FAILED",
                message="The run failed.",
                retryable=True,
            ),
        ),
        AgentRunInterrupted(
            event_id="interrupted-1",
            thread_id="thread-1",
            run_id="run-mock-123",
            sequence=0,
            created_at=CREATED_AT,
            interrupt_ids=["interrupt-1"],
        ),
    ],
    ids=["failed", "interrupted"],
)
async def test_import_file_marks_unsuccessful_terminal_as_failed(
    db_session: Session,
    terminal: AgentDomainEvent,
) -> None:
    _store_file(db_session)

    with pytest.raises(RAGFileImportError):
        await _service(db_session, FakeAgentClient([terminal])).import_file(
            payload=_payload(),
            operation_id="operation-1",
        )

    assert _sync_status(db_session) == FileSyncStatus.FAILED


@pytest.mark.anyio
async def test_import_file_marks_stream_exception_as_failed(
    db_session: Session,
) -> None:
    _store_file(db_session)
    client = FakeAgentClient(stream_error=RuntimeError("transport failed"))

    with pytest.raises(RAGFileImportError):
        await _service(db_session, client).import_file(
            payload=_payload(),
            operation_id="operation-1",
        )

    assert _sync_status(db_session) == FileSyncStatus.FAILED


@pytest.mark.anyio
async def test_import_file_skips_agent_when_file_is_already_synced(
    db_session: Session,
) -> None:
    _store_file(db_session, FileSyncStatus.SYNCED)
    client = FakeAgentClient()

    result = await _service(db_session, client).import_file(
        payload=_payload(),
        operation_id="operation-1",
    )

    assert result.file_id == FILE_ID
    assert client.requests == []


@pytest.mark.anyio
async def test_import_file_does_not_retry_failed_file_without_policy(
    db_session: Session,
) -> None:
    _store_file(db_session, FileSyncStatus.FAILED)
    client = FakeAgentClient()

    with pytest.raises(RAGFileImportError):
        await _service(db_session, client).import_file(
            payload=_payload(),
            operation_id="operation-1",
        )

    assert client.requests == []


def test_thread_id_is_a_prefixed_uuid() -> None:
    thread_id = build_rag_file_import_thread_id(
        file_id=FILE_ID,
        operation_id="operation-1",
    )

    assert thread_id.startswith("rag-file-import:")
    UUID(thread_id.removeprefix("rag-file-import:"))


def test_thread_id_rejects_empty_operation_id() -> None:
    with pytest.raises(ValueError):
        build_rag_file_import_thread_id(
            file_id=FILE_ID,
            operation_id=" ",
        )
