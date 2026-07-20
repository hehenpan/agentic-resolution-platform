"""Tests for the local MQ adapter's streamed RAG file import workflow."""

from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from uuid import UUID

import pytest
from app.core import mq_task
from app.core.mq_task import (
    MQMessageBase,
    MQMessageUploadFileFinish,
    MQTaskManagerImpLocal,
    MSGContextData,
    MSGMetaData,
)
from app.models.models import (
    FileInfo,
    FileStatus,
    FileStorageType,
    FileSyncStatus,
)
from microservice_client.ai_agent_client import AIAgentServerInterface
from sqlmodel import Session
from tests.conftest import test_engine

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
    AgentRAGFileImportRequest,
    AgentResumeRequest,
    AgentRunCompleted,
    AgentRunFailed,
    AgentTurnRequest,
    StructuredDataPart,
)

FILE_ID = 501
FILE_NAME = "ingest.md"
OWNER_ID = 502
TENANT_ID = 503
OUTPUT_ID = "55555555-5555-5555-8555-555555555555"
CREATED_AT = 1_725_000_000


class FakeAgentClient(AIAgentServerInterface):
    def __init__(self, events: list[AgentDomainEvent]) -> None:
        self.events = events
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


def _store_file(db_session: Session) -> None:
    db_session.add(
        FileInfo(
            file_id=FILE_ID,
            tenant_id=TENANT_ID,
            owner_user_id=OWNER_ID,
            owner_email="owner@example.com",
            file_name=FILE_NAME,
            file_type="md",
            file_md5_hash="hash",
            file_storage_location="ingest.md",
            file_storage_type=FileStorageType.LOCAL,
            file_size=6,
            create_ts=CREATED_AT,
            status=FileStatus.ACTIVE,
            vector_db_sync_status=FileSyncStatus.PENDING,
        )
    )
    db_session.commit()


def _message() -> MQMessageUploadFileFinish:
    return MQMessageUploadFileFinish(
        topic_name="file_upload_events",
        partition_key=str(FILE_ID),
        meta_data=MSGMetaData(
            producer_svc_name="api_server",
            produce_time_ts=CREATED_AT,
            operator_user_id=OWNER_ID,
            extra_meta={"source": "upload"},
        ),
        context_data=MSGContextData(
            request_id="request-1",
            extra_context={"channel": "api"},
        ),
        file_id=FILE_ID,
        file_name=FILE_NAME,
        file_type="md",
        file_size=6,
        file_content=b"policy",
        tenant_id=TENANT_ID,
    )


def _success_events() -> list[AgentDomainEvent]:
    return [
        AgentOutputProduced(
            event_id=OUTPUT_ID,
            thread_id="thread-1",
            run_id="run-mock-123",
            sequence=0,
            created_at=CREATED_AT,
            output=AgentOutput(
                output_id=OUTPUT_ID,
                parts=[
                    StructuredDataPart(
                        schema_id=(
                            AgentOutputSchemaId.RAG_FILE_IMPORT_RESULT_V1.value
                        ),
                        data={
                            "file_id": FILE_ID,
                            "file_name": FILE_NAME,
                            "status": "success",
                        },
                    )
                ],
            ),
        ),
        AgentRunCompleted(
            event_id="completed-1",
            thread_id="thread-1",
            run_id="run-mock-123",
            sequence=1,
            created_at=CREATED_AT,
            output_ids=[OUTPUT_ID],
        ),
    ]


def _sync_status(db_session: Session) -> FileSyncStatus:
    db_session.expire_all()
    file_info = db_session.get(FileInfo, FILE_ID)
    assert file_info is not None
    return file_info.vector_db_sync_status


@pytest.mark.anyio
async def test_local_task_maps_message_and_consumes_stream(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _store_file(db_session)
    client = FakeAgentClient(_success_events())
    session_calls = 0

    @contextmanager
    def test_session() -> Iterator[Session]:
        nonlocal session_calls
        session_calls += 1
        with Session(test_engine) as session:
            yield session

    monkeypatch.setattr(mq_task, "get_session", test_session)
    monkeypatch.setattr(
        mq_task.ai_agent_client,
        "get_ai_agent_server_client",
        lambda: client,
    )
    manager = MQTaskManagerImpLocal()

    result = await manager.local_task_upload_file_finish(_message())

    assert result is not None
    assert result.file_id == FILE_ID
    assert session_calls == 1
    assert len(client.requests) == 1
    request = client.requests[0]
    assert request.thread_id.startswith("rag-file-import:")
    UUID(request.thread_id.removeprefix("rag-file-import:"))
    assert request.payload.file_content == b"policy"
    assert request.payload.file_owner_id == OWNER_ID
    assert request.payload.file_tenant_id == TENANT_ID
    assert request.payload.extra_meta == {"source": "upload"}
    assert request.payload.extra_context == {"channel": "api"}
    assert _sync_status(db_session) == FileSyncStatus.SYNCED


@pytest.mark.anyio
async def test_local_task_returns_none_and_marks_failed_terminal(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _store_file(db_session)
    failed = AgentRunFailed(
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
    )

    client = FakeAgentClient([failed])

    @contextmanager
    def test_session() -> Iterator[Session]:
        with Session(test_engine) as session:
            yield session

    monkeypatch.setattr(mq_task, "get_session", test_session)
    monkeypatch.setattr(
        mq_task.ai_agent_client,
        "get_ai_agent_server_client",
        lambda: client,
    )
    manager = MQTaskManagerImpLocal()

    result = await manager.local_task_upload_file_finish(_message())

    assert result is None
    assert _sync_status(db_session) == FileSyncStatus.FAILED


def test_send_message_rejects_unknown_event_type() -> None:
    message = MQMessageBase(
        topic_name="unknown",
        partition_key="key",
        event_type="unknown",
        meta_data=MSGMetaData(
            producer_svc_name="api_server",
            produce_time_ts=CREATED_AT,
            operator_user_id=OWNER_ID,
            extra_meta={},
        ),
        context_data=MSGContextData(request_id="request-1", extra_context={}),
    )

    with pytest.raises(ValueError, match="Unknown event type"):
        MQTaskManagerImpLocal().send_message("unknown", "key", message)
