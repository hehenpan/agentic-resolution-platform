import os
import logging
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session


from app.main import app
from app.api.deps import get_db


TEST_DATABASE_URL = "sqlite:///test_db.sqlite3"
test_engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

@pytest.fixture(name="db_session")
def db_session_fixture():
    """
    Create tables before each test and drop them after, ensuring database isolation between test cases.
    """
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db(request):
    """
    Automatically delete the physical test database file after the entire test session finishes.
    """
    def remove_file():
        # Get the database file path (relative to the directory from which pytest was run)
        db_file = "test_db.sqlite3"
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except Exception as e:
                logging.getLogger("tests").error(f"Error removing test database file: {e}")
                
    # Register callback to run at the end of the test session
    request.addfinalizer(remove_file)
    

@pytest.fixture(name="client")
def client_fixture(db_session: Session):
    """
    Create a TestClient and override the get_db dependency.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    # Set the test engine in application state for middleware to access
    app.state.db_engine = test_engine
    # Override dependency to force all API requests to use the test database
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    # Restore original dependencies and application state after the test completes
    app.dependency_overrides.clear()
    if hasattr(app.state, "db_engine"):
        delattr(app.state, "db_engine")


    