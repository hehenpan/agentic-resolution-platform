from sqlmodel import Session
from app.models.models import ChatSession, ChatMessage
from app.models.chat_wrapper import ChatDBWrapper
from loguru import logger



class ChatService:
    """Service layer encapsulating Chat business logic."""

    def __init__(self, dbsession: Session):
        self.wrapper = ChatDBWrapper(db_session=dbsession)

    def create_chat_session(
        self,
        tenant_id: int,
        user_id: int,
        title: str | None = None
    ) -> ChatSession:
        """
        Create a new ChatSession.
        Does NOT interact with ai_agent service.
        """
        session_title = title if title and title.strip() else "New Chat"
        return self.wrapper.create_chat_session(
            tenant_id=tenant_id,
            user_id=user_id,
            title=session_title
        )

    def list_chat_sessions_by_user(
        self,
        tenant_id: int,
        user_id: int,
        limit: int = 50,
        cursor: str | None = None
    ) -> tuple[list[ChatSession], bool, str | None]:
        """List chat session metadata for a user using cursor pagination."""
        return self.wrapper.list_chat_sessions_by_user(
            tenant_id=tenant_id,
            user_id=user_id,
            limit=limit,
            cursor=cursor
        )

    def list_chat_messages_by_session(
        self,
        chat_session_id: str,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[ChatMessage], bool, str | None]:
        """List chat history messages for a chat session using cursor pagination."""
        return self.wrapper.list_chat_messages_by_session(
            chat_session_id=chat_session_id,
            limit=limit,
            cursor=cursor,
        )

