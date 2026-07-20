from fastapi import status
from sqlmodel import Session, select
from app.models.models import ChatSession, ChatSessionStatus as ModelChatSessionStatus
from app.schemas.chat import ChatSessionStatus
from app.schemas.common import BizCode
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
