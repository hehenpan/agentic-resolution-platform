import os
import sqlite3
import pytest
from dotenv import load_dotenv

# Load environment variables for tests (e.g. GOOGLE_API_KEY)
load_dotenv()

from agent.core.config import settings
from agent.core.logger import logger
from langgraph.checkpoint.sqlite import SqliteSaver

TEST_DB_FILE = "test_db_ai_agent.sqlite"

# Override configuration database file dynamically for tests
settings.DB_FILE = TEST_DB_FILE
settings.QDRANT_LOCATION = ":memory:"
settings.QDRANT_PATH = None
settings.QDRANT_URL = None

@pytest.fixture(scope="session", autouse=True)
def mock_embedding_query_cache():
    """
    Fixture that automatically intercepts and mocks GeminiEmbeddingModel.aembed_query
    to use the offline JSON query cache during tests, preventing online API calls.
    """
    import json
    from pathlib import Path
    from agent.core.embedding import GeminiEmbeddingModel
    from unittest.mock import patch
    
    cache_path = Path(__file__).resolve().parent / "test_data" / "query_embeddings_cache.json"
    
    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            cache = json.load(f)
    else:
        cache = {}

    async def mock_aembed_query(self, text: str):
        if text in cache:
            return cache[text]
        raise ValueError(
            f"Query embedding not found in offline cache for text: '{text}'. "
            f"Please run `tests/scripts/build_test_vectordb.py` to regenerate the cache."
        )

    with patch.object(GeminiEmbeddingModel, "aembed_query", mock_aembed_query):
        yield

@pytest.fixture(scope="function")
def prebuilt_qdrant_env():
    """
    Fixture that temporarily configures the Qdrant client to use the pre-built local database
    instead of the default in-memory database, clearing client cache as needed.
    """
    from agent.core.qdrant import get_qdrant_client
    from pathlib import Path
    
    db_path = str(Path(__file__).resolve().parent / "test_data" / "qdrant_prebuilt_db")
    
    orig_location = settings.QDRANT_LOCATION
    orig_path = settings.QDRANT_PATH
    
    settings.QDRANT_LOCATION = None
    settings.QDRANT_PATH = db_path
    
    # Clear get_qdrant_client cache to force reload with the new path
    get_qdrant_client.cache_clear()
    
    yield
    
    settings.QDRANT_LOCATION = orig_location
    settings.QDRANT_PATH = orig_path
    get_qdrant_client.cache_clear()

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="session", autouse=True)
def clean_test_db_fixture():
    """
    Session-scoped fixture: ensures the test database is clean before running tests,
    triggers schema creation, and cleans up the SQLite file after tests complete.
    """
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass

    # Initialize checkpointer database schemas/tables
    conn = sqlite3.connect(TEST_DB_FILE, check_same_thread=False)
    try:
        memory = SqliteSaver(conn)
        memory.setup()
    finally:
        conn.close()

    yield

    # Clean up after all tests complete
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception as error:
            logger.error("Failed to remove test SQLite file: {}", error)


@pytest.fixture(scope="function", autouse=True)
def set_test_checkpointer():
    """
    Function-scoped autouse fixture: automatically configures example_graph
    and file_ingest_graph with an in-memory checkpointer for testing.
    """
    from langgraph.checkpoint.memory import MemorySaver
    from agent.example_graph import example_graph
    from agent.file_ingest import file_ingest_graph
    from agent.supervisor import supervisor_graph

    example_graph.checkpointer = MemorySaver()
    file_ingest_graph.checkpointer = MemorySaver()
    supervisor_graph.checkpointer = MemorySaver()
