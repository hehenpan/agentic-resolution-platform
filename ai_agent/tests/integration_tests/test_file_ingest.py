import os
import pytest
from loguru import logger
from agent.file_ingest_graph import file_ingest_graph
from agent.core.qdrant import get_qdrant_client
from agent.core.constants import QDRANT_COLLECTION_RAG, GEMINI_EMBEDDING_DIM

pytestmark = pytest.mark.anyio

@pytest.mark.langsmith
async def test_file_ingest_success() -> None:
    """
    Integration test: reads test.md, feeds it into file_ingest_graph, 
    and verifies that the text is correctly vectorized and indexed in Qdrant.
    """
    # 1. Read the test data markdown file
    test_data_path = os.path.join(os.path.dirname(__file__), "..", "test_data", "test.md")
    with open(test_data_path, "rb") as f:
        file_content = f.read()
        
    # 2. Construct inputs mimicking RAGFileImportPayload
    inputs = {
        "file_id": 9999,
        "file_name": "test.md",
        "file_size": len(file_content),
        "file_owner_id": 100,
        "file_tenant_id": 200,
        "file_content": file_content,
        "extra_meta": {"tag": "test-ingest"},
        "extra_context": {"project": "unit-test"},
    }
    
    config = {"configurable": {"thread_id": "test-ingest-thread"}}
    
    # 3. Invoke the graph
    res = await file_ingest_graph.ainvoke(inputs, config=config)
    
    # 4. Assert response status and output state
    assert res is not None
    assert res.get("status") == "success"
    assert res.get("text") is not None
    assert len(res.get("vector")) == GEMINI_EMBEDDING_DIM
    
    # 5. Query Qdrant to verify indexing
    client = get_qdrant_client()
    collection_name = QDRANT_COLLECTION_RAG
    
    assert client.collection_exists(collection_name)
    
    # Fetch the point by ID
    points = client.retrieve(
        collection_name=collection_name,
        ids=[9999]
    )
    
    assert len(points) == 1
    point = points[0]
    assert point.id == 9999
    assert point.payload["file_name"] == "test.md"
    assert point.payload["file_owner_id"] == 100
    assert point.payload["file_tenant_id"] == 200
    assert "Process Codex Storyboard Tasks" in point.payload["text"]
    assert point.payload["extra_meta"] == {"tag": "test-ingest"}
    assert point.payload["extra_context"] == {"project": "unit-test"}
    logger.info("file_ingest_graph integration test passed successfully!")
