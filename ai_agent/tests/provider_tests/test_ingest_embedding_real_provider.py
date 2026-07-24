"""Record a real provider embedding for the file-ingest integration test."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from agent.core.config import settings
from agent.core.embedding import GeminiEmbeddingModel, get_embedding_model
from agent.core.logger import logger

pytestmark = pytest.mark.anyio

TEST_DATA_DIR = Path(__file__).resolve().parent.parent / "test_data"
INGEST_FILE = TEST_DATA_DIR / "ingest_test_file.md"
EMBEDDING_RECORD_FILE = TEST_DATA_DIR / "ingest_test_file_embedding.json"
REAL_AEMBED_QUERY = GeminiEmbeddingModel.aembed_query


@pytest.mark.skipif(
    os.getenv("RUN_REAL_EMBEDDING") != "1",
    reason="Set RUN_REAL_EMBEDDING=1 to call the real embedding provider",
)
async def test_record_ingest_file_real_embedding(monkeypatch) -> None:
    """Generate and persist the real embedding used by offline tests."""
    monkeypatch.setattr(
        GeminiEmbeddingModel,
        "aembed_query",
        REAL_AEMBED_QUERY,
    )
    file_content = INGEST_FILE.read_bytes()
    text = file_content.decode("utf-8", errors="ignore")

    embedding = await get_embedding_model().aembed_query(text)

    assert len(embedding) == settings.EMBEDDING_DIM
    record = {
        "model": settings.EMBEDDING_MODEL,
        "file_name": INGEST_FILE.name,
        "content_sha256": hashlib.sha256(file_content).hexdigest(),
        "embedding": embedding,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    EMBEDDING_RECORD_FILE.write_text(
        json.dumps(record, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    logger.info(
        "Recorded {}-dimension embedding for {} in {}",
        len(embedding),
        INGEST_FILE.name,
        EMBEDDING_RECORD_FILE,
    )
