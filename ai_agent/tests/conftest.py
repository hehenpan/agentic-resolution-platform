import os
import sqlite3
import pytest
from agent.core.config import settings
from langgraph.checkpoint.sqlite import SqliteSaver

TEST_DB_FILE = "test_db_ai_agent.sqlite"

# Override configuration database file dynamically for tests
settings.DB_FILE = TEST_DB_FILE
settings.QDRANT_LOCATION = ":memory:"
settings.QDRANT_PATH = None
settings.QDRANT_URL = None

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
        except Exception as e:
            print(f"Failed to remove test SQLite file: {e}")
