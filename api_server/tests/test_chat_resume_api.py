"""Unit tests for Chat Resume SSE API endpoint (POST /api/v1/chat/sessions/{chat_session_id}/resume)."""

import json
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.models import (
    User,
    ChatSession,
    ChatMessage,
    ChatMessageSenderType,
    ChatSessionStatus,
)
from app.schemas.chat_msg_payload import WebHumanInputSchemaId
from shared_common.schemas.ai_agent import (
    AgentCreateRunResponse,
    AgentRunStatus,
    AgentOutputProduced,
    AgentRunCompleted,
    HumanInputRequested,
    HumanInputRequest,
    AgentResumeCursor,
    AgentOutput,
    TextPart,
)
from microservice_client.ai_agent_client import AIAgentServerInterface
from app.api.deps import get_ai_agent_client
from app.main import app
from tests.conftest import (
    TEST_USER_EMAIL,
    TEST_USER_PASSWORD,
)
from utils.commons import generate_uuid_hex, get_current_ts




def login_user_client(client: TestClient):
    """Helper to authenticate test client."""
    login_payload = {
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD,
    }
    response = client.post("https://testserver/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    return response




class MockResumeAIAgentClient(AIAgentServerInterface):
    """Mock AIAgentServerInterface implementation for resume testing."""

    def __init__(self, mock_run_id: str, mock_events: list):
        self.mock_run_id = mock_run_id
        self.mock_events = mock_events
        self.received_resume_request = None

    def start(self):
        pass

    def stop(self):
        pass

    async def create_run(self, request):
        return AgentCreateRunResponse(
            run_id=self.mock_run_id,
            thread_id=request.thread_id,
            status=AgentRunStatus.PENDING,
        )

    async def list_runs(self, request):
        pass

    def stream_turn(self, request):
        pass

    async def _resume_event_generator(self, request):
        self.received_resume_request = request
        for event in self.mock_events:
            yield event

    def resume_turn(self, request):
        return self._resume_event_generator(request)

    def stream_rag_file_import(self, request):
        pass

    def join_stream(self, request):
        pass

    def get_state_events(self, request):
        pass


def test_resume_chat_message_success(client: TestClient, db_session: Session):
    """
    Test successful interrupt resume:
    1. Create ChatSession and seed a HumanInputRequested message in DB.
    2. Post to /api/v1/chat/sessions/{chat_session_id}/resume with WebGetOrdersByEmailInputModel payload.
    3. Verify SSE stream output.
    4. Verify DB records for user resume message and agent output.
    """
    login_user_client(client)

    user = db_session.exec(select(User).where(User.email == TEST_USER_EMAIL)).first()
    session_id = f"cs_{generate_uuid_hex()}"
    thread_id = f"thread_{generate_uuid_hex()}"
    interrupt_id = f"intr_{generate_uuid_hex()}"
    run_id_1 = f"run_{generate_uuid_hex()}"
    run_id_2 = f"run_{generate_uuid_hex()}"

    cs = ChatSession(
        chat_session_id=session_id,
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        title="Test Interrupt Session",
        status=ChatSessionStatus.ACTIVE,
        create_ts=get_current_ts(),
        update_ts=get_current_ts(),
    )
    db_session.add(cs)
    db_session.commit()

    # Seed pending interrupt message in DB
    domain_interrupt_event = HumanInputRequested(
        event_id=f"evt_{generate_uuid_hex()}",
        thread_id=thread_id,
        run_id=run_id_1,
        sequence=1,
        created_at=get_current_ts(),
        interrupt_id=interrupt_id,
        request=HumanInputRequest(
            prompt="Please supply customer email to query orders",
            schema_id=WebHumanInputSchemaId.GET_ORDERS_INPUT_V1.value,
            input_schema={},
        ),
        resume_cursor=AgentResumeCursor(
            checkpoint_id="cp_test_123",
            checkpoint_ns="",
            checkpoint_map={},
        ),
    )
    db_msg = ChatMessage(
        event_id=domain_interrupt_event.event_id,
        chat_session_id=session_id,
        thread_id=thread_id,
        run_id=run_id_1,
        sender_type=ChatMessageSenderType.AGENT,
        event_kind="agent.human_input_requested",
        sequence=1,
        payload_json=domain_interrupt_event.model_dump_json(),
    )
    db_session.add(db_msg)
    db_session.commit()

    # Mock agent output event on resume
    output_event = AgentOutputProduced(
        event_id=f"evt_{generate_uuid_hex()}",
        thread_id=thread_id,
        run_id=run_id_2,
        sequence=1,
        created_at=get_current_ts(),
        output=AgentOutput(
            output_id=f"out_{generate_uuid_hex()}",
            parts=[TextPart(text="Found 2 orders for customer@example.com")],
        ),
    )
    completed_event = AgentRunCompleted(
        event_id=f"evt_{generate_uuid_hex()}",
        thread_id=thread_id,
        run_id=run_id_2,
        sequence=2,
        created_at=get_current_ts(),
        output_ids=[output_event.output.output_id],
    )

    mock_client = MockResumeAIAgentClient(
        mock_run_id=run_id_2,
        mock_events=[output_event, completed_event],
    )
    app.dependency_overrides[get_ai_agent_client] = lambda: mock_client

    try:
        payload = {
            "chat_session_id": session_id,
            "thread_id": thread_id,
            "schema_id": WebHumanInputSchemaId.GET_ORDERS_INPUT_V1.value,
            "resume_payload": {"email": "customer@example.com"},
        }
        res = client.post(
            f"https://testserver/api/v1/chat/sessions/{session_id}/resume",
            json=payload,
        )
        assert res.status_code == 200
        assert "text/event-stream" in res.headers["content-type"]

        content = res.text
        assert "event: agent.output_produced" in content
        assert "Found 2 orders for customer@example.com" in content
        assert "event: agent.run_completed" in content

        # Verify SDK received the correctly extracted resume_cursor and interrupt_id
        assert mock_client.received_resume_request is not None
        assert mock_client.received_resume_request.interrupt_id == interrupt_id
        assert mock_client.received_resume_request.resume_cursor.checkpoint_id == "cp_test_123"
        assert mock_client.received_resume_request.response.schema_id == WebHumanInputSchemaId.GET_ORDERS_INPUT_V1.value
        assert mock_client.received_resume_request.response.response_data == {"email": "customer@example.com", "llm_text": None}

        # Verify DB records saved
        user_resume_msg = db_session.exec(
            select(ChatMessage)
            .where(ChatMessage.chat_session_id == session_id)
            .where(ChatMessage.sender_type == ChatMessageSenderType.USER)
            .where(ChatMessage.event_kind == "user_resume")
        ).first()
        assert user_resume_msg is not None

        agent_output_msg = db_session.exec(
            select(ChatMessage)
            .where(ChatMessage.chat_session_id == session_id)
            .where(ChatMessage.event_id == output_event.event_id)
        ).first()
        assert agent_output_msg is not None

    finally:
        app.dependency_overrides.clear()


def test_resume_chat_message_no_pending_interrupt(client: TestClient, db_session: Session):
    """Test resuming when no interrupt exists in DB returns HTTP 400."""
    login_user_client(client)

    user = db_session.exec(select(User).where(User.email == TEST_USER_EMAIL)).first()
    session_id = f"cs_{generate_uuid_hex()}"
    thread_id = f"thread_{generate_uuid_hex()}"

    cs = ChatSession(
        chat_session_id=session_id,
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        title="Session Without Interrupt",
        status=ChatSessionStatus.ACTIVE,
        create_ts=get_current_ts(),
        update_ts=get_current_ts(),
    )
    db_session.add(cs)
    db_session.commit()

    payload = {
        "chat_session_id": session_id,
        "thread_id": thread_id,
        "schema_id": WebHumanInputSchemaId.GET_ORDERS_INPUT_V1.value,
        "resume_payload": {"email": "test@example.com"},
    }
    res = client.post(
        f"https://testserver/api/v1/chat/sessions/{session_id}/resume",
        json=payload,
    )
    assert res.status_code == 400
    assert "No pending interrupt message found" in res.json()["detail"]


def test_resume_chat_message_unsupported_schema(client: TestClient, db_session: Session):
    """Test resuming with unsupported schema_id returns HTTP 400."""
    login_user_client(client)

    user = db_session.exec(select(User).where(User.email == TEST_USER_EMAIL)).first()
    session_id = f"cs_{generate_uuid_hex()}"
    thread_id = f"thread_{generate_uuid_hex()}"

    cs = ChatSession(
        chat_session_id=session_id,
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        title="Session Test Schema",
        status=ChatSessionStatus.ACTIVE,
        create_ts=get_current_ts(),
        update_ts=get_current_ts(),
    )
    db_session.add(cs)
    db_session.commit()

    # Case 1: Invalid enum string triggers FastAPI Pydantic request validation 422
    payload = {
        "chat_session_id": session_id,
        "thread_id": thread_id,
        "schema_id": "invalid_unknown_schema",
        "resume_payload": {"foo": "bar"},
    }
    res = client.post(
        f"https://testserver/api/v1/chat/sessions/{session_id}/resume",
        json=payload,
    )
    assert res.status_code == 422

    # Case 2: "unknown" schema_id passes enum validation but is unmapped in service, returning 400
    payload["schema_id"] = "unknown"
    res = client.post(
        f"https://testserver/api/v1/chat/sessions/{session_id}/resume",
        json=payload,
    )
    assert res.status_code == 400
    assert "Unsupported schema_id" in res.json()["detail"]


def test_resume_chat_message_path_mismatch(client: TestClient, db_session: Session):
    """Test path session_id mismatch with body returns HTTP 400."""
    login_user_client(client)

    payload = {
        "chat_session_id": "cs_body_id",
        "thread_id": "thread_123",
        "schema_id": WebHumanInputSchemaId.GET_ORDERS_INPUT_V1.value,
        "resume_payload": {"email": "test@example.com"},
    }
    res = client.post(
        "https://testserver/api/v1/chat/sessions/cs_path_id/resume",
        json=payload,
    )
    assert res.status_code == 400
    assert "does not match" in res.json()["detail"]
