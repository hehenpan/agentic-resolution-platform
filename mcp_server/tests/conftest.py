import os
import pytest
from sqlmodel import SQLModel, create_engine
from core import database

TEST_DB_FILE = "mcp_test.sqlite3"


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Session-scoped fixture to automatically configure a clean SQLite test database
    and clean it up after the test suite completes.
    """
    # Force use of a test database URL
    test_db_url = f"sqlite:///{TEST_DB_FILE}"
    
    # Create test database engine
    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    
    # Intercept engine in database module
    old_engine = database.engine
    database.engine = test_engine
    
    # Create all metadata tables
    SQLModel.metadata.create_all(test_engine)
    
    yield
    
    # Dispose connection pools
    test_engine.dispose()
    
    # Restore original engine
    database.engine = old_engine
    
    # Clean up test SQLite file
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
            print(f"\nRemoved test SQLite file: {TEST_DB_FILE}")
        except Exception as e:
            print(f"\nFailed to remove test SQLite file: {e}")


@pytest.fixture(scope="function", autouse=True)
def clean_database_tables():
    """
    Function-scoped fixture to truncate all tables before each test runs,
    guaranteeing a clean database environment for every unit test.
    """
    with database.get_session() as session:
        for table in reversed(SQLModel.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()


@pytest.fixture
def seed_ecommerce_user():
    """
    Fixture to seed an ECommerceUser record in the database for testing.
    Returns a dictionary of the seeded user's attributes to prevent DetachedInstanceError.
    """
    from models.db_models import ECommerceUser
    with database.get_session() as session:
        user = ECommerceUser(
            user_name="Jane Doe",
            pwd="hashed_password_2",
            email="jane@example.com",
            status=1,
            create_ts=1700000001
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return {
            "user_id": user.user_id,
            "user_name": user.user_name,
            "email": user.email,
            "status": user.status,
            "create_ts": user.create_ts
        }
