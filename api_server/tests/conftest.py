import logging
import os
from collections.abc import AsyncIterator

import microservice_client.ai_agent_client
import pytest
from app.api.deps import get_db
from app.core.mq_task import MQMessageBase
from app.main import app
from app.models.models import User, UserStatus, UserType
from fastapi.testclient import TestClient
from microservice_client.ai_agent_client import AIAgentServerInterface
from sqlmodel import Session, SQLModel, create_engine
from utils.commons import get_md5

from shared_common.schemas.ai_agent import (
    AgentCreateRunRequest,
    AgentCreateRunResponse,
    AgentDomainEvent,
    AgentGetStateEventsRequest,
    AgentJoinStreamRequest,
    AgentRAGFileImportRequest,
    AgentResumeRequest,
    AgentTurnRequest,
)


# Global Test Credentials
TEST_ADMIN_EMAIL = "admin@example.com"
TEST_ADMIN_PASSWORD = "adminpassword123"

TEST_TENANT_ADMIN_EMAIL = "tenant_admin@example.com"
TEST_TENANT_ADMIN_PASSWORD = "tenantadminpassword123"

TEST_USER_EMAIL = "user@example.com"
TEST_USER_PASSWORD = "userpassword123"

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
        # Pre-seed admin, tenant_admin and user accounts for testing
        admin = User(
            email=TEST_ADMIN_EMAIL,
            pwd_md5=get_md5(TEST_ADMIN_PASSWORD),
            user_type=UserType.ADMIN,
            status=UserStatus.ACTIVE,
            tenant_id=1
        )
        tenant_admin = User(
            email=TEST_TENANT_ADMIN_EMAIL,
            pwd_md5=get_md5(TEST_TENANT_ADMIN_PASSWORD),
            user_type=UserType.TENANT_ADMIN,
            status=UserStatus.ACTIVE,
            tenant_id=1
        )
        user = User(
            email=TEST_USER_EMAIL,
            pwd_md5=get_md5(TEST_USER_PASSWORD),
            user_type=UserType.USER,
            status=UserStatus.ACTIVE,
            tenant_id=1
        )
        session.add(admin)
        session.add(tenant_admin)
        session.add(user)
        session.commit()

        yield session
    SQLModel.metadata.drop_all(test_engine)





@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db(request):
    """
    Automatically delete the physical test database file and local storage files after the entire test session finishes.
    """
    def remove_test_artifacts():
        import shutil

        from app.core.config import settings
        
        # 1. Clean up test database file
        db_file = "test_db.sqlite3"
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except Exception as e:
                logging.getLogger("tests").error(f"Error removing test database file: {e}")
                
        # 2. Clean up test files storage directory
        if os.path.exists(settings.STORAGE_DIR):
            try:
                shutil.rmtree(settings.STORAGE_DIR)
            except Exception as e:
                logging.getLogger("tests").error(f"Error removing storage directory: {e}")
                
    # Register callback to run at the end of the test session
    request.addfinalizer(remove_test_artifacts)
    

@pytest.fixture(name="client")
def client_fixture(
    db_session: Session,
    mock_mq_task_manager: "MockMQTaskManager",
):
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


class MockMQTaskManager:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str, MQMessageBase]] = []

    def send_message(
        self,
        topic: str,
        partition_key: str,
        msg: MQMessageBase,
    ) -> None:
        self.messages.append((topic, partition_key, msg))


@pytest.fixture(name="mock_mq_task_manager")
def mock_mq_task_manager_fixture(monkeypatch: pytest.MonkeyPatch) -> MockMQTaskManager:
    manager = MockMQTaskManager()
    monkeypatch.setattr(
        "app.services.file_service.get_mq_task_manager",
        lambda: manager,
    )
    return manager


class MockAIAgentServer(AIAgentServerInterface):
    def start(self):
        pass

    def stop(self):
        pass

    async def create_run(
        self,
        request: AgentCreateRunRequest,
    ) -> AgentCreateRunResponse:
        return AgentCreateRunResponse(
            run_id="run-mock-123",
            thread_id=request.thread_id,
            status="pending",
        )

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
        return self._empty_stream()

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
        events: list[AgentDomainEvent] = []
        for event in events:
            yield event


@pytest.fixture(scope="session", autouse=True)
def mock_ai_agent_client_fixture():
    """
    Session-scoped autouse fixture: overrides the get_ai_agent_server_client factory function
    to return a mock instance, preventing any real network calls to the AI Agent server during testing.
    """
    mock_instance = MockAIAgentServer()
    original_func = microservice_client.ai_agent_client.get_ai_agent_server_client
    
    # Override
    microservice_client.ai_agent_client.get_ai_agent_server_client = lambda: mock_instance
    
    yield mock_instance
    
    # Restore
    microservice_client.ai_agent_client.get_ai_agent_server_client = original_func


    
