"""Tests for File Ingest public output mapping."""

import pytest
from langgraph.runtime import ExecutionInfo, Runtime
from shared_common.schemas.ai_agent import (
    AgentOutputSchemaId,
    RAGFileImportResult,
    StructuredDataPart,
)

from agent.file_ingest.nodes import build_file_ingest_output
from agent.file_ingest.outputs import build_rag_file_import_output
from agent.file_ingest.state import (
    BuildFileIngestOutputUpdate,
    FileIngestState,
)

IDENTITY_SCOPE = "task-1"


def _runtime(task_id: str = IDENTITY_SCOPE) -> Runtime[None]:
    return Runtime(
        execution_info=ExecutionInfo(
            checkpoint_id="checkpoint-1",
            checkpoint_ns="",
            task_id=task_id,
        )
    )


def _state(status: str | None = "success") -> FileIngestState:
    return FileIngestState(
        file_id=123,
        file_name="policy.md",
        file_size=6,
        file_owner_id=10,
        file_tenant_id=20,
        file_content=b"policy",
        text="policy",
        vector=[0.1, 0.2],
        status=status,
    )


def test_build_rag_file_import_output_maps_structured_result() -> None:
    output = build_rag_file_import_output(
        identity_scope=IDENTITY_SCOPE,
        file_id=123,
        file_name="policy.md",
    )

    assert len(output.parts) == 1
    part = output.parts[0]
    assert isinstance(part, StructuredDataPart)
    assert part.schema_id == AgentOutputSchemaId.RAG_FILE_IMPORT_RESULT_V1.value
    assert RAGFileImportResult.model_validate(part.data) == RAGFileImportResult(
        file_id=123,
        file_name="policy.md",
    )
    assert "file_content" not in part.data
    assert "vector" not in part.data


def test_build_rag_file_import_output_identity_is_stable() -> None:
    first = build_rag_file_import_output(
        identity_scope=IDENTITY_SCOPE,
        file_id=123,
        file_name="policy.md",
    )
    replayed = build_rag_file_import_output(
        identity_scope=IDENTITY_SCOPE,
        file_id=123,
        file_name="policy.md",
    )
    different = build_rag_file_import_output(
        identity_scope="task-2",
        file_id=123,
        file_name="policy.md",
    )

    assert replayed.output_id == first.output_id
    assert different.output_id != first.output_id


@pytest.mark.anyio
async def test_build_file_ingest_output_returns_typed_update() -> None:
    raw_update = await build_file_ingest_output(_state(), _runtime())

    update = BuildFileIngestOutputUpdate.model_validate(raw_update)

    assert len(update.outputs) == 1
    assert isinstance(update.outputs[0].parts[0], StructuredDataPart)


@pytest.mark.anyio
async def test_build_file_ingest_output_rejects_unsuccessful_state() -> None:
    with pytest.raises(RuntimeError, match="did not complete vector storage"):
        await build_file_ingest_output(_state(None), _runtime())


@pytest.mark.anyio
async def test_build_file_ingest_output_rejects_missing_task_id() -> None:
    with pytest.raises(RuntimeError, match="requires a task ID"):
        await build_file_ingest_output(_state(), _runtime(""))
