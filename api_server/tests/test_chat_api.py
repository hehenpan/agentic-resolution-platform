import json
import uuid
from fastapi import status
from sqlmodel import Session, select
from app.models.models import (
    ChatSession,
    ChatSessionStatus as ModelChatSessionStatus,
    User,
    ChatThread,
    ThreadRun,
    ChatMessage,
)
from app.schemas.chat import ChatSessionStatus
from app.schemas.common import BizCode
from app.api.deps import get_ai_agent_client
from app.models.chat_wrapper import ChatDBWrapper
from microservice_client.ai_agent_client import AIAgentServerInterface
from shared_common.schemas.ai_agent import (
    AgentCreateRunResponse,
    AgentOutputProduced,
    AgentRunCompleted,
    AgentRunStatus,
    AgentOutput,
    TextPart,
)
from tests.conftest import (
    TEST_USER_EMAIL,
    TEST_USER_PASSWORD,
)



def login_user_client(client):
    """Helper to log in as default test user."""
    login_payload = {
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD,
    }
    res = client.post("https://testserver/api/v1/auth/login", json=login_payload)
    assert res.status_code == status.HTTP_200_OK
    return res


def test_create_chat_session_success(client, db_session: Session):
    """
    Test creating a chat session:
    1. Log in as test user (tenant_id=1).
    2. Post to /api/v1/chat/sessions with custom title.
    3. Verify response code 201 and data payload.
    4. Verify ChatSession record created in DB.
    """
    login_user_client(client)

    payload = {"title": "Support Session 1"}
    response = client.post("https://testserver/api/v1/chat/sessions", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    res_data = response.json()

    assert res_data["code"] == BizCode.SUCCESS
    assert res_data["message"] == "Chat session created successfully"
    assert "chat_session_id" in res_data["data"]

    session_info = res_data["data"]["session_info"]
    assert session_info["title"] == "Support Session 1"
    assert session_info["tenant_id"] == 1
    assert session_info["status"] == ChatSessionStatus.ACTIVE

    # DB Assertion
    chat_session_id = res_data["data"]["chat_session_id"]
    db_record = db_session.exec(
        select(ChatSession).where(ChatSession.chat_session_id == chat_session_id)
    ).first()
    assert db_record is not None
    assert db_record.title == "Support Session 1"
    assert db_record.tenant_id == 1


def test_create_chat_session_default_title(client, db_session: Session):
    """
    Test creating a chat session without specifying a title.
    Title should default to 'New Chat'.
    """
    login_user_client(client)

    payload = {}
    response = client.post("https://testserver/api/v1/chat/sessions", json=payload)

    assert response.status_code == status.HTTP_201_CREATED
    res_data = response.json()
    assert res_data["code"] == BizCode.SUCCESS
    assert res_data["data"]["session_info"]["title"] == "New Chat"


def test_list_chat_sessions_success(client, db_session: Session):
    """
    Test listing chat sessions using composite cursor format '{create_ts}_{id}'.
    """
    login_user_client(client)

    from app.models.models import User
    from utils.commons import generate_uuid_hex, get_current_ts

    user = db_session.exec(select(User).where(User.email == TEST_USER_EMAIL)).first()
    now_ts = get_current_ts()

    # Insert 3 sessions with distinct create_ts
    s1 = ChatSession(
        chat_session_id=f"cs_{generate_uuid_hex()}",
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        title="Session Oldest",
        status=ChatSessionStatus.ACTIVE,
        create_ts=now_ts - 200,
        update_ts=now_ts - 200,
    )
    s2 = ChatSession(
        chat_session_id=f"cs_{generate_uuid_hex()}",
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        title="Session Middle",
        status=ChatSessionStatus.ACTIVE,
        create_ts=now_ts - 100,
        update_ts=now_ts - 100,
    )
    s3 = ChatSession(
        chat_session_id=f"cs_{generate_uuid_hex()}",
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        title="Session Newest",
        status=ChatSessionStatus.ACTIVE,
        create_ts=now_ts,
        update_ts=now_ts,
    )
    db_session.add_all([s1, s2, s3])
    db_session.commit()

    # First page with limit=2 (should return Session Newest and Session Middle)
    response = client.get("https://testserver/api/v1/chat/sessions?limit=2")

    assert response.status_code == status.HTTP_200_OK
    res_data = response.json()
    assert res_data["code"] == BizCode.SUCCESS
    assert len(res_data["data"]["items"]) == 2
    assert res_data["data"]["items"][0]["title"] == "Session Newest"
    assert res_data["data"]["items"][1]["title"] == "Session Middle"
    assert res_data["data"]["has_more"] is True
    next_cursor = res_data["data"]["next_cursor"]
    assert next_cursor == f"{s2.create_ts}_{s2.id}"

    # Second page using next_cursor
    response_page2 = client.get(f"https://testserver/api/v1/chat/sessions?limit=2&cursor={next_cursor}")
    assert response_page2.status_code == status.HTTP_200_OK
    res_data2 = response_page2.json()
    assert res_data2["code"] == BizCode.SUCCESS
    assert len(res_data2["data"]["items"]) == 1
    assert res_data2["data"]["items"][0]["title"] == "Session Oldest"
    assert res_data2["data"]["has_more"] is False
    assert res_data2["data"]["next_cursor"] is None


def test_list_chat_sessions_same_timestamp_composite_cursor(client, db_session: Session):
    """
    Test cursor pagination when multiple sessions share the EXACT same create_ts.
    Verifies that composite cursor '{create_ts}_{id}' breaks ties using id.desc().
    """
    login_user_client(client)

    from app.models.models import User
    from utils.commons import generate_uuid_hex, get_current_ts

    user = db_session.exec(select(User).where(User.email == TEST_USER_EMAIL)).first()
    same_ts = get_current_ts()

    s1 = ChatSession(
        chat_session_id=f"cs_{generate_uuid_hex()}",
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        title="Same TS Item 1",
        status=ChatSessionStatus.ACTIVE,
        create_ts=same_ts,
        update_ts=same_ts,
    )
    s2 = ChatSession(
        chat_session_id=f"cs_{generate_uuid_hex()}",
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        title="Same TS Item 2",
        status=ChatSessionStatus.ACTIVE,
        create_ts=same_ts,
        update_ts=same_ts,
    )
    db_session.add_all([s1, s2])
    db_session.commit()

    # Query with limit 1 to force pagination on same timestamp
    response = client.get("https://testserver/api/v1/chat/sessions?limit=1")
    assert response.status_code == status.HTTP_200_OK
    res_data = response.json()
    assert len(res_data["data"]["items"]) == 1
    first_item = res_data["data"]["items"][0]
    next_cursor = res_data["data"]["next_cursor"]
    assert next_cursor == f"{first_item['create_ts']}_{first_item['id']}"

    # Fetch next page using composite cursor
    response_page2 = client.get(f"https://testserver/api/v1/chat/sessions?limit=1&cursor={next_cursor}")
    assert response_page2.status_code == status.HTTP_200_OK
    res_data2 = response_page2.json()
    assert len(res_data2["data"]["items"]) == 1
    second_item = res_data2["data"]["items"][0]
    assert second_item["id"] < first_item["id"]
    assert second_item["create_ts"] == same_ts


def test_list_chat_messages_success_and_pagination(client, db_session: Session):
    """
    Test listing chat messages for a session:
    1. Insert 3 ChatMessage records with distinct create_ts_ms.
    2. Query page 1 with limit=2, assert DESC ordering by create_ts_ms and payload_json passthrough.
    3. Query page 2 using next_cursor string.
    """
    login_user_client(client)

    from app.models.models import ChatMessage, ChatMessageSenderType as ModelSenderType
    from utils.commons import generate_uuid_hex

    session_id = f"cs_{generate_uuid_hex()}"

    msg1 = ChatMessage(
        event_id=f"evt_{generate_uuid_hex()}",
        chat_session_id=session_id,
        thread_id="thread_1",
        run_id="run_1",
        sender_type=ModelSenderType.USER,
        event_kind="user_message",
        sequence=1,
        payload_json='{"text": "Hello"}',
        create_ts_ms=1000.0,
    )
    msg2 = ChatMessage(
        event_id=f"evt_{generate_uuid_hex()}",
        chat_session_id=session_id,
        thread_id="thread_1",
        run_id="run_1",
        sender_type=ModelSenderType.AGENT,
        event_kind="agent_message",
        sequence=2,
        payload_json='{"text": "Hi there!"}',
        create_ts_ms=2000.0,
    )
    msg3 = ChatMessage(
        event_id=f"evt_{generate_uuid_hex()}",
        chat_session_id=session_id,
        thread_id="thread_1",
        run_id="run_1",
        sender_type=ModelSenderType.USER,
        event_kind="user_message",
        sequence=3,
        payload_json='{"text": "How are you?"}',
        create_ts_ms=3000.0,
    )
    db_session.add_all([msg1, msg2, msg3])
    db_session.commit()

    # Query Page 1 (limit=2)
    response = client.get(f"https://testserver/api/v1/chat/sessions/{session_id}/messages?limit=2")
    assert response.status_code == status.HTTP_200_OK
    res_data = response.json()
    assert res_data["code"] == BizCode.SUCCESS
    assert res_data["message"] == "Chat history messages retrieved successfully"

    items = res_data["data"]["items"]
    assert len(items) == 2
    assert items[0]["create_ts_ms"] == 3000.0
    assert items[0]["payload_json"] == '{"text": "How are you?"}'
    assert items[1]["create_ts_ms"] == 2000.0
    assert items[1]["payload_json"] == '{"text": "Hi there!"}'
    assert res_data["data"]["has_more"] is True

    next_cursor = res_data["data"]["next_cursor"]
    assert next_cursor == "2000.0"

    # Query Page 2 (cursor=2000.0)
    response_page2 = client.get(
        f"https://testserver/api/v1/chat/sessions/{session_id}/messages?limit=2&cursor={next_cursor}"
    )
    assert response_page2.status_code == status.HTTP_200_OK
    res_data2 = response_page2.json()
    assert res_data2["code"] == BizCode.SUCCESS

    items2 = res_data2["data"]["items"]
    assert len(items2) == 1
    assert items2[0]["create_ts_ms"] == 1000.0
    assert items2[0]["payload_json"] == '{"text": "Hello"}'
    assert res_data2["data"]["has_more"] is False
    assert res_data2["data"]["next_cursor"] is None


def test_list_chat_messages_invalid_cursor(client, db_session: Session):
    """
    Test passing an invalid non-float string as cursor for message history.
    Should return HTTP 400 Bad Request.
    """
    login_user_client(client)

    session_id = "cs_test_invalid_cursor"
    response = client.get(f"https://testserver/api/v1/chat/sessions/{session_id}/messages?cursor=invalid_cursor_str")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Invalid cursor format" in response.json()["detail"]


class DummyMockAIAgentClient(AIAgentServerInterface):
    """Dummy mock implementation of AIAgentServerInterface for testing SSE streaming."""

    def __init__(self, run_id: str, events: list):
        self.mock_run_id = run_id
        self.mock_events = events
        self.create_run_request = None
        self.join_stream_request = None

    def start(self):
        pass

    def stop(self):
        pass

    async def create_run(self, request):
        self.create_run_request = request
        return AgentCreateRunResponse(
            run_id=self.mock_run_id,
            thread_id=request.thread_id,
            status=AgentRunStatus.PENDING,
        )

    async def list_runs(self, request):
        pass

    async def _event_generator(self):
        for event in self.mock_events:
            yield event

    def stream_turn(self, request):
        return self._event_generator()

    def join_stream(self, request):
        self.join_stream_request = request
        return self._event_generator()

    def resume_turn(self, request):
        pass

    def stream_rag_file_import(self, request):
        pass

    def get_state_events(self, request):
        pass


def test_send_chat_message_sse_success(client, db_session: Session):
    """
    Test sending chat message and receiving SSE event stream:
    1. Create a session in DB.
    2. Override get_ai_agent_client dependency with DummyMockAIAgentClient.
    3. Post message to /api/v1/chat/sessions/{session_id}/messages.
    4. Assert SSE stream wire format ('event: <kind>\ndata: <json>\n\n').
    5. Assert DB records created in ChatThread, ThreadRun, and ChatMessage.
    """
    login_user_client(client)
    from utils.commons import generate_uuid_hex, get_current_ts

    user = db_session.exec(select(User).where(User.email == TEST_USER_EMAIL)).first()
    session_id = f"cs_{generate_uuid_hex()}"
    cs = ChatSession(
        chat_session_id=session_id,
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        title="Test SSE Session",
        status=ModelChatSessionStatus.ACTIVE,
        create_ts=get_current_ts(),
        update_ts=get_current_ts(),
    )
    db_session.add(cs)
    db_session.commit()

    run_id = f"run_{generate_uuid_hex()}"
    thread_id = f"thread_{generate_uuid_hex()}"

    # Prepare domain events
    event1 = AgentOutputProduced(
        event_id=f"evt_{generate_uuid_hex()}",
        thread_id=thread_id,
        run_id=run_id,
        sequence=1,
        created_at=get_current_ts(),
        output=AgentOutput(
            output_id=f"out_{generate_uuid_hex()}",
            parts=[TextPart(text="Hello! How can I assist you today?")],
        ),
    )
    event2 = AgentRunCompleted(
        event_id=f"evt_{generate_uuid_hex()}",
        thread_id=thread_id,
        run_id=run_id,
        sequence=2,
        created_at=get_current_ts(),
        output_ids=[event1.output.output_id],
    )

    mock_agent_client = DummyMockAIAgentClient(run_id=run_id, events=[event1, event2])
    client.app.dependency_overrides[get_ai_agent_client] = lambda: mock_agent_client

    try:
        payload = {"content": "Hello AI Assistant"}
        response = client.post(
            f"https://testserver/api/v1/chat/sessions/{session_id}/messages",
            json=payload,
        )

        assert response.status_code == status.HTTP_200_OK
        assert "text/event-stream" in response.headers["content-type"]
        assert mock_agent_client.create_run_request.message.content == payload["content"]
        assert (
            mock_agent_client.join_stream_request.thread_id
            == mock_agent_client.create_run_request.thread_id
        )
        assert mock_agent_client.join_stream_request.run_id == run_id

        # Parse SSE wire format
        response_text = response.text
        blocks = [b.strip() for b in response_text.split("\n\n") if b.strip()]
        assert len(blocks) == 2

        # Validate Block 1 (agent.output_produced)
        lines1 = blocks[0].split("\n")
        assert lines1[0] == f"event: {event1.kind.value}"
        assert lines1[1].startswith("data: ")
        data1 = json.loads(lines1[1][6:])
        assert data1["event_id"] == event1.event_id
        assert data1["kind"] == "agent.output_produced"
        assert data1["output"]["parts"][0]["text"] == "Hello! How can I assist you today?"

        # Validate Block 2 (agent.run_completed)
        lines2 = blocks[1].split("\n")
        assert lines2[0] == f"event: {event2.kind.value}"
        assert lines2[1].startswith("data: ")
        data2 = json.loads(lines2[1][6:])
        assert data2["event_id"] == event2.event_id
        assert data2["kind"] == "agent.run_completed"

        # DB Record Assertions
        thread_record = db_session.exec(
            select(ChatThread).where(ChatThread.chat_session_id == session_id)
        ).first()
        assert thread_record is not None
        assert thread_record.chat_session_id == session_id

        run_record = db_session.exec(
            select(ThreadRun).where(ThreadRun.run_id == run_id)
        ).first()
        assert run_record is not None
        assert run_record.chat_session_id == session_id

        messages = db_session.exec(
            select(ChatMessage)
            .where(ChatMessage.chat_session_id == session_id)
            .order_by(ChatMessage.sequence.asc())
        ).all()
        assert len(messages) == 3
        # Message 0: User Message
        assert messages[0].sender_type == 1  # USER
        assert messages[0].event_kind == "user_message"
        user_payload_data = json.loads(messages[0].payload_json)
        assert user_payload_data["content"] == "Hello AI Assistant"

        # Message 1: Agent Output Produced
        assert messages[1].sender_type == 2  # AGENT
        assert messages[1].event_kind == "agent.output_produced"
        agent_payload_1 = json.loads(messages[1].payload_json)
        assert agent_payload_1["event_id"] == event1.event_id
        assert agent_payload_1["kind"] == "agent.output_produced"
        assert agent_payload_1["output"]["parts"][0]["text"] == "Hello! How can I assist you today?"

        # Message 2: System Run Completed
        assert messages[2].sender_type == 3  # SYSTEM
        assert messages[2].event_kind == "agent.run_completed"
        agent_payload_2 = json.loads(messages[2].payload_json)
        assert agent_payload_2["event_id"] == event2.event_id
        assert agent_payload_2["kind"] == "agent.run_completed"

    finally:
        client.app.dependency_overrides.pop(get_ai_agent_client, None)


def test_send_chat_message_does_not_stream_when_turn_persistence_fails(
    client,
    db_session: Session,
    monkeypatch,
):
    """Run and user message records must both persist before streaming starts."""
    login_user_client(client)
    from utils.commons import generate_uuid_hex, get_current_ts

    user = db_session.exec(select(User).where(User.email == TEST_USER_EMAIL)).first()
    session_id = f"cs_{generate_uuid_hex()}"
    db_session.add(
        ChatSession(
            chat_session_id=session_id,
            tenant_id=user.tenant_id,
            user_id=user.user_id,
            title="Turn persistence failure",
            status=ModelChatSessionStatus.ACTIVE,
            create_ts=get_current_ts(),
            update_ts=get_current_ts(),
        )
    )
    db_session.commit()

    run_id = f"run_{generate_uuid_hex()}"
    mock_agent_client = DummyMockAIAgentClient(run_id=run_id, events=[])
    client.app.dependency_overrides[get_ai_agent_client] = lambda: mock_agent_client

    def fail_turn_persistence(
        self: ChatDBWrapper,
        run_id: str,
        thread_id: str,
        chat_session_id: str,
        user_message: ChatMessage,
    ) -> None:
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(ChatDBWrapper, "save_turn_start", fail_turn_persistence)

    try:
        response = client.post(
            f"https://testserver/api/v1/chat/sessions/{session_id}/messages",
            json={"content": "Do not lose this message"},
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to persist initialized agent run" in response.json()["detail"]
        assert mock_agent_client.create_run_request is not None
        assert mock_agent_client.join_stream_request is None
        assert (
            db_session.exec(
                select(ThreadRun).where(ThreadRun.chat_session_id == session_id)
            ).first()
            is None
        )
        assert (
            db_session.exec(
                select(ChatMessage).where(ChatMessage.chat_session_id == session_id)
            ).first()
            is None
        )
    finally:
        client.app.dependency_overrides.pop(get_ai_agent_client, None)


def test_send_chat_message_thread_reuse(client, db_session: Session):
    """
    Test that send_chat_message reuses existing latest ChatThread record
    for the given session, hitting idx_chatthread_session_create index (create_ts DESC).
    """
    login_user_client(client)
    from utils.commons import generate_uuid_hex, get_current_ts

    user = db_session.exec(select(User).where(User.email == TEST_USER_EMAIL)).first()
    session_id = f"cs_{generate_uuid_hex()}"
    cs = ChatSession(
        chat_session_id=session_id,
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        title="Test Thread Reuse Session",
        status=ModelChatSessionStatus.ACTIVE,
        create_ts=get_current_ts(),
        update_ts=get_current_ts(),
    )
    db_session.add(cs)

    # Insert older and newer threads
    old_thread_id = str(uuid.uuid4())
    new_thread_id = str(uuid.uuid4())
    t_old = ChatThread(
        thread_id=old_thread_id,
        chat_session_id=session_id,
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        create_ts=get_current_ts() - 100,
        update_ts=get_current_ts() - 100,
    )
    t_new = ChatThread(
        thread_id=new_thread_id,
        chat_session_id=session_id,
        tenant_id=user.tenant_id,
        user_id=user.user_id,
        create_ts=get_current_ts(),
        update_ts=get_current_ts(),
    )
    db_session.add_all([t_old, t_new])
    db_session.commit()

    run_id = f"run_{generate_uuid_hex()}"
    event = AgentRunCompleted(
        event_id=f"evt_{generate_uuid_hex()}",
        thread_id=new_thread_id,
        run_id=run_id,
        sequence=1,
        created_at=get_current_ts(),
        output_ids=[],
    )
    mock_agent_client = DummyMockAIAgentClient(run_id=run_id, events=[event])
    client.app.dependency_overrides[get_ai_agent_client] = lambda: mock_agent_client

    try:
        response = client.post(
            f"https://testserver/api/v1/chat/sessions/{session_id}/messages",
            json={"content": "Reuse thread check"},
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify DB ThreadRun uses new_thread_id
        run_record = db_session.exec(
            select(ThreadRun).where(ThreadRun.run_id == run_id)
        ).first()
        assert run_record is not None
        assert run_record.thread_id == new_thread_id

    finally:
        client.app.dependency_overrides.pop(get_ai_agent_client, None)


def test_send_chat_message_session_not_found(client):
    """
    Test sending chat message to a non-existent session_id.
    Should fail during pre-stream preparation steps 1-4 and return HTTP 500 Internal Server Error
    (instead of an SSE stream).
    """
    login_user_client(client)
    non_existent_session_id = "cs_non_existent_12345"
    response = client.post(
        f"https://testserver/api/v1/chat/sessions/{non_existent_session_id}/messages",
        json={"content": "Hello in non existent session"},
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json()["detail"] == "Chat session not found or access denied"


def test_project_schema_id_known_and_unknown():
    """
    Test ChatEventProjector.project_schema_id:
    1. Valid domain schema_id maps to corresponding WebStructuredDataSchemaId.
    2. Unknown domain schema_id maps to WebStructuredDataSchemaId.UNKNOWN and logs error.
    """
    from app.services.chat_event_projector import ChatEventProjector
    from app.schemas.chat_msg_payload import WebStructuredDataSchemaId

    # Known schema_id
    res_known = ChatEventProjector.project_schema_id("ecommerce.user_result.v1")
    assert res_known == WebStructuredDataSchemaId.ECOMMERCE_USER_RESULT_V1

    # Unmapped schema_id fallback
    res_unknown = ChatEventProjector.project_schema_id("future.new_unmapped_schema.v99")
    assert res_unknown == WebStructuredDataSchemaId.UNKNOWN


def test_user_payload_schemas_and_projector():
    """
    Test user input payload schemas:
    1. WebChatUserPayload (kind="user_message")
    2. WebUserResumePayload (kind="user_resume")
    """
    from app.services.chat_event_projector import ChatEventProjector
    from app.schemas.chat_msg_payload import WebUserEventKind, WebChatUserPayload, WebUserResumePayload, WebHumanInputSchemaId

    # Test user text message payload
    user_msg_payload = ChatEventProjector.project_user_message("Hello assist")
    assert isinstance(user_msg_payload, WebChatUserPayload)
    assert user_msg_payload.kind == WebUserEventKind.USER_MESSAGE
    assert user_msg_payload.content == "Hello assist"

    # Test user resume payload
    user_resume_payload = ChatEventProjector.project_user_resume(
        interrupt_id="intr_123",
        schema_id="human_input.get_orders.v1",
        action="confirm",
        response_data={"approved": True},
    )
    assert isinstance(user_resume_payload, WebUserResumePayload)
    assert user_resume_payload.kind == WebUserEventKind.USER_RESUME
    assert user_resume_payload.interrupt_id == "intr_123"
    assert user_resume_payload.schema_id == WebHumanInputSchemaId.GET_ORDERS_INPUT_V1
    assert user_resume_payload.action == "confirm"
    assert user_resume_payload.response_data == {"approved": True}


def test_project_web_input_to_domain_input():
    """
    Test Anti-Corruption Layer: ChatEventProjector.project_web_input_to_domain_input
    transforms Web DTO models to downstream ai_agent domain models.
    """
    from app.services.chat_event_projector import ChatEventProjector
    from app.schemas.chat_msg_payload import (
        WebHumanInputSchemaId,
        WebGetUserByEmailInputModel,
    )
    from shared_common.schemas.ai_agent import GetUserByEmailInputModel

    web_input = WebGetUserByEmailInputModel(email="test@example.com", llm_text=None)
    domain_input = ChatEventProjector.project_web_input_to_domain_input(
        schema_id=WebHumanInputSchemaId.GET_USER_INPUT_V1,
        web_input=web_input,
    )

    assert isinstance(domain_input, GetUserByEmailInputModel)
    assert domain_input.email == "test@example.com"


def test_project_human_input_schema_id_known_and_unknown():
    """
    Test ChatEventProjector.project_human_input_schema_id:
    1. Valid domain schema_id maps to corresponding WebHumanInputSchemaId.
    2. Unknown domain schema_id maps to WebHumanInputSchemaId.UNKNOWN and logs error.
    """
    from app.services.chat_event_projector import ChatEventProjector
    from app.schemas.chat_msg_payload import WebHumanInputSchemaId, WebHumanInputRequested
    from shared_common.schemas.ai_agent import (
        HumanInputRequested,
        HumanInputRequest,
        AgentResumeCursor,
    )

    # 1. Known human input schema_id
    res_known = ChatEventProjector.project_human_input_schema_id("human_input.get_user.v1")
    assert res_known == WebHumanInputSchemaId.GET_USER_INPUT_V1

    # 2. Unknown human input schema_id fallback
    res_unknown = ChatEventProjector.project_human_input_schema_id("human_input.unknown_future.v999")
    assert res_unknown == WebHumanInputSchemaId.UNKNOWN

    # 3. Test project_human_input_schema for known model (passing enum or raw str) and fallback for unknown
    schema_dict_enum = ChatEventProjector.project_human_input_schema(WebHumanInputSchemaId.GET_USER_INPUT_V1)
    schema_dict_str = ChatEventProjector.project_human_input_schema("human_input.get_user.v1")
    assert "properties" in schema_dict_enum
    assert "email" in schema_dict_enum["properties"]
    assert schema_dict_enum == schema_dict_str

    fallback_dict = ChatEventProjector.project_human_input_schema(
        "human_input.unknown_future.v999",
        {"custom_field": "custom_val"},
    )
    assert fallback_dict == {"custom_field": "custom_val"}

    # 4. Test HumanInputRequested event projection with ACL input_schema
    domain_event = HumanInputRequested(
        event_id="evt_human_1",
        thread_id="th_1",
        run_id="run_1",
        sequence=1,
        source_sequences=[1],
        created_at=1600000000,
        interrupt_id="intr_99",
        request=HumanInputRequest(
            prompt="Please provide user email",
            schema_id="human_input.get_user.v1",
            input_schema={"ignored_domain_schema": True},
            context={"user_id": "u1"},
            allowed_actions=["submit"],
        ),
        resume_cursor=AgentResumeCursor(checkpoint_id="cp_1"),
    )
    web_event = ChatEventProjector.project_domain_event(domain_event)
    assert isinstance(web_event, WebHumanInputRequested)
    assert web_event.request.schema_id == WebHumanInputSchemaId.GET_USER_INPUT_V1
    assert web_event.request.prompt == "Please provide user email"
    assert "properties" in web_event.request.input_schema
    assert "email" in web_event.request.input_schema["properties"]




