import hashlib
from pathlib import Path

import pytest
from pydantic import BaseModel
from shared_common.schemas.ai_agent import (
    AgentOutput,
    AgentOutputSchemaId,
    RAGFileImportResult,
    StructuredDataPart,
)

from agent.core.config import settings
from agent.core.constants import QDRANT_COLLECTION_RAG
from agent.core.logger import logger
from agent.core.qdrant import get_async_qdrant_client
from agent.file_ingest import file_ingest_graph
from agent.file_ingest import nodes as file_ingest_nodes

pytestmark = pytest.mark.anyio

TEST_DATA_DIR = Path(__file__).resolve().parent.parent / "test_data"
INGEST_FILE = TEST_DATA_DIR / "ingest_test_file.md"
EMBEDDING_RECORD_FILE = TEST_DATA_DIR / "ingest_test_file_embedding.json"


class EmbeddingRecord(BaseModel):
    """Represent the recorded provider embedding used by this test."""

    model: str
    file_name: str
    content_sha256: str
    embedding: list[float]
    recorded_at: str


class OfflineEmbeddingModel:
    """Return a mock embedding for any ingested text chunk."""

    def __init__(self, embedding: list[float]) -> None:
        self.embedding = embedding
        self.inputs: list[str] = []

    async def aembed_query(self, text: str) -> list[float]:
        self.inputs.append(text)
        return self.embedding.copy()


async def test_file_ingest_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify file ingestion with chunked points storing deterministic UUIDs."""
    file_content = INGEST_FILE.read_bytes()
    record = EmbeddingRecord.model_validate_json(
        EMBEDDING_RECORD_FILE.read_text(encoding="utf-8")
    )
    assert record.file_name == INGEST_FILE.name
    assert record.content_sha256 == hashlib.sha256(file_content).hexdigest()
    assert len(record.embedding) == settings.EMBEDDING_DIM

    embedding_model = OfflineEmbeddingModel(record.embedding)
    monkeypatch.setattr(
        file_ingest_nodes,
        "get_embedding_model",
        lambda: embedding_model,
    )

    inputs = {
        "file_id": 9999,
        "file_name": INGEST_FILE.name,
        "file_size": len(file_content),
        "file_owner_id": 100,
        "file_tenant_id": 200,
        "file_content": file_content,
        "extra_meta": {"tag": "test-ingest"},
        "extra_context": {"project": "unit-test"},
    }
    config = {"configurable": {"thread_id": "test-ingest-thread"}}

    res = await file_ingest_graph.ainvoke(inputs, config=config)

    assert set(res) == {"outputs"}
    assert len(res["outputs"]) == 1
    output = AgentOutput.model_validate(res["outputs"][0])
    assert len(output.parts) == 1
    part = output.parts[0]
    assert isinstance(part, StructuredDataPart)
    assert part.schema_id == AgentOutputSchemaId.RAG_FILE_IMPORT_RESULT_V1.value
    assert RAGFileImportResult.model_validate(part.data) == RAGFileImportResult(
        file_id=9999,
        file_name=INGEST_FILE.name,
    )
    assert "text" not in res
    assert "vector" not in res
    assert "file_content" not in res
    
    # Assert multiple chunks were generated
    assert len(embedding_model.inputs) > 1

    client = await get_async_qdrant_client()
    collection_name = QDRANT_COLLECTION_RAG

    assert await client.collection_exists(collection_name)

    from uuid import UUID, uuid5
    INGEST_NAMESPACE = UUID("507db244-9336-55f5-a55f-146301c9b928")
    
    expected_ids = [
        str(uuid5(INGEST_NAMESPACE, f"chunk:9999:{i}"))
        for i in range(len(embedding_model.inputs))
    ]

    points = await client.retrieve(collection_name=collection_name, ids=expected_ids)
    assert len(points) == len(expected_ids)

    for idx, point in enumerate(points):
        assert point.payload["file_name"] == INGEST_FILE.name
        assert point.payload["file_owner_id"] == 100
        assert point.payload["file_tenant_id"] == 200
        assert point.payload["text"] == embedding_model.inputs[idx]
        assert point.payload["extra_meta"] == {"tag": "test-ingest"}
        assert point.payload["extra_context"] == {"project": "unit-test"}
        
    logger.info("file_ingest_graph integration test passed successfully!")
