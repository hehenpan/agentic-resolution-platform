from sqlmodel import Session, select, func, or_, and_
from app.models.models import (
    ChatSession,
    ChatSessionStatus,
    ChatMessage,
    ChatThread,
    ChatThreadStatus,
    ThreadRun,
)
from utils.commons import generate_uuid_hex, get_current_ts
from loguru import logger



class ChatDBWrapper:
    """Encapsulates all direct database operations for Chat related tables."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def create_chat_session(
        self,
        tenant_id: int,
        user_id: int,
        title: str = "New Chat"
    ) -> ChatSession:
        """Insert a new ChatSession record into database."""
        chat_session_id = f"cs_{generate_uuid_hex()}"
        now_ts = get_current_ts()

        chat_session = ChatSession(
            chat_session_id=chat_session_id,
            tenant_id=tenant_id,
            user_id=user_id,
            title=title,
            status=ChatSessionStatus.ACTIVE,
            create_ts=now_ts,
            update_ts=now_ts,
        )

        try:
            self.db.add(chat_session)
            self.db.commit()
            self.db.refresh(chat_session)
            logger.info(
                f"Successfully created ChatSession in DB: chat_session_id={chat_session_id}, "
                f"tenant_id={tenant_id}, user_id={user_id}"
            )
            return chat_session
        except Exception as e:
            self.db.rollback()
            logger.exception(
                f"Database error while creating ChatSession: tenant_id={tenant_id}, "
                f"user_id={user_id}, error={e}"
            )
            raise e

    def list_chat_sessions_by_user(
        self,
        tenant_id: int,
        user_id: int,
        limit: int = 50,
        cursor: str | None = None
    ) -> tuple[list[ChatSession], bool, str | None]:
        """
        Query ChatSession records by tenant_id and user_id using composite index
        idx_chatsession_user_create (user_id, create_ts).
        Cursor is a string in format '{create_ts}_{id}'.
        Returns sessions ordered by create_ts DESC, id DESC.
        """
        try:
            query_stmt = (
                select(ChatSession)
                .where(
                    ChatSession.tenant_id == tenant_id,
                    ChatSession.user_id == user_id,
                    ChatSession.status != ChatSessionStatus.INVALID,
                )
            )
            if cursor and cursor.strip():
                try:
                    parts = cursor.strip().split("_")
                    cursor_ts = int(parts[0])
                    cursor_id = int(parts[1])
                    query_stmt = query_stmt.where(
                        or_(
                            ChatSession.create_ts < cursor_ts,
                            and_(
                                ChatSession.create_ts == cursor_ts,
                                ChatSession.id < cursor_id
                            )
                        )
                    )
                except (ValueError, IndexError) as e:
                    logger.error(f"Invalid cursor format: cursor={cursor}, error={e}")
                    raise ValueError(f"Invalid cursor format: {cursor}")

            query_stmt = query_stmt.order_by(
                ChatSession.create_ts.desc(),
                ChatSession.id.desc()
            ).limit(limit + 1)

            sessions = list(self.db.exec(query_stmt).all())

            has_more = len(sessions) > limit
            if has_more:
                sessions = sessions[:limit]
                last_item = sessions[-1]
                next_cursor = f"{last_item.create_ts}_{last_item.id}"
            else:
                next_cursor = None

            return sessions, has_more, next_cursor
        except Exception as e:
            logger.exception(
                f"Database error while listing ChatSessions: tenant_id={tenant_id}, "
                f"user_id={user_id}, error={e}"
            )
            raise e

    def list_chat_messages_by_session(
        self,
        chat_session_id: str,
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[ChatMessage], bool, str | None]:
        """
        Query ChatMessage records by chat_session_id using index
        idx_chatmessage_session_create (chat_session_id, create_ts_ms).
        Cursor is a string representing create_ts_ms as float.
        Returns messages ordered by create_ts_ms DESC.
        """
        try:
            query_stmt = select(ChatMessage).where(ChatMessage.chat_session_id == chat_session_id)

            if cursor and cursor.strip():
                try:
                    cursor_ts_ms = float(cursor.strip())
                    query_stmt = query_stmt.where(ChatMessage.create_ts_ms < cursor_ts_ms)
                except ValueError as e:
                    logger.error(
                        f"Database error - invalid cursor format for chat messages: cursor={cursor}, error={e}"
                    )
                    raise ValueError(f"Invalid cursor format: {cursor}") from e

            query_stmt = query_stmt.order_by(ChatMessage.create_ts_ms.desc()).limit(limit + 1)

            messages = list(self.db.exec(query_stmt).all())

            has_more = len(messages) > limit
            if has_more:
                messages = messages[:limit]
                last_item = messages[-1]
                next_cursor = str(last_item.create_ts_ms)
            else:
                next_cursor = None

            return messages, has_more, next_cursor
        except Exception as e:
            logger.exception(
                f"Database error while listing ChatMessages: chat_session_id={chat_session_id}, error={e}"
            )
            raise e

    def get_chat_session_by_id(
        self,
        chat_session_id: str,
        tenant_id: int,
        user_id: int,
    ) -> ChatSession | None:
        """Query ChatSession by chat_session_id, tenant_id, and user_id."""
        try:
            query_stmt = select(ChatSession).where(
                ChatSession.chat_session_id == chat_session_id,
                ChatSession.tenant_id == tenant_id,
                ChatSession.user_id == user_id,
                ChatSession.status != ChatSessionStatus.INVALID,
            )
            return self.db.exec(query_stmt).first()
        except Exception as e:
            logger.exception(
                f"Database error while querying ChatSession: chat_session_id={chat_session_id}, error={e}"
            )
            raise e

    def get_latest_thread_by_session(self, chat_session_id: str) -> ChatThread | None:
        """
        Query the latest ChatThread record for a session using index
        idx_chatthread_session_create (chat_session_id, create_ts).
        Returns the record ordered by create_ts DESC.
        """
        try:
            query_stmt = (
                select(ChatThread)
                .where(ChatThread.chat_session_id == chat_session_id)
                .order_by(ChatThread.create_ts.desc())
                .limit(1)
            )
            return self.db.exec(query_stmt).first()
        except Exception as e:
            logger.exception(
                f"Database error while querying latest ChatThread: chat_session_id={chat_session_id}, error={e}"
            )
            raise e

    def create_chat_thread(
        self,
        chat_session_id: str,
        tenant_id: int,
        user_id: int,
        thread_id: str,
    ) -> ChatThread:
        """Insert a new ChatThread record into database."""
        now_ts = get_current_ts()
        chat_thread = ChatThread(
            thread_id=thread_id,
            chat_session_id=chat_session_id,
            tenant_id=tenant_id,
            user_id=user_id,
            status=ChatThreadStatus.ACTIVE,
            create_ts=now_ts,
            update_ts=now_ts,
        )
        try:
            self.db.add(chat_thread)
            self.db.commit()
            self.db.refresh(chat_thread)
            logger.info(
                f"Successfully created ChatThread in DB: thread_id={thread_id}, chat_session_id={chat_session_id}"
            )
            return chat_thread
        except Exception as e:
            self.db.rollback()
            logger.exception(
                f"Database error while creating ChatThread: chat_session_id={chat_session_id}, error={e}"
            )
            raise e

    def create_thread_run(
        self,
        run_id: str,
        thread_id: str,
        chat_session_id: str,
    ) -> ThreadRun:
        """Insert a new ThreadRun record into database."""
        now_ts = get_current_ts()
        thread_run = ThreadRun(
            run_id=run_id,
            thread_id=thread_id,
            chat_session_id=chat_session_id,
            create_ts=now_ts,
        )
        try:
            self.db.add(thread_run)
            self.db.commit()
            self.db.refresh(thread_run)
            logger.info(
                f"Successfully created ThreadRun in DB: run_id={run_id}, thread_id={thread_id}"
            )
            return thread_run
        except Exception as e:
            self.db.rollback()
            logger.exception(
                f"Database error while creating ThreadRun: run_id={run_id}, thread_id={thread_id}, error={e}"
            )
            raise e

    def save_chat_message(self, message: ChatMessage) -> ChatMessage:
        """Insert a ChatMessage record into database."""
        try:
            self.db.add(message)
            self.db.commit()
            self.db.refresh(message)
            logger.info(
                f"Successfully saved ChatMessage in DB: event_id={message.event_id}, "
                f"event_kind={message.event_kind}, chat_session_id={message.chat_session_id}"
            )
            return message
        except Exception as e:
            self.db.rollback()
            logger.exception(
                f"Database error while saving ChatMessage: event_id={message.event_id}, error={e}"
            )
            raise e

    def get_latest_interrupt_message(
        self,
        chat_session_id: str,
        thread_id: str,
    ) -> ChatMessage | None:
        """
        Query the latest pending interrupt (HumanInputRequested) message for session and thread.
        """
        try:
            statement = (
                select(ChatMessage)
                .where(ChatMessage.chat_session_id == chat_session_id)
                .where(ChatMessage.thread_id == thread_id)
                .where(ChatMessage.event_kind == "agent.human_input_requested")
                .order_by(ChatMessage.create_ts_ms.desc())
                .limit(1)
            )
            return self.db.exec(statement).first()
        except Exception as e:
            logger.exception(
                f"Database error querying latest interrupt message: chat_session_id={chat_session_id}, "
                f"thread_id={thread_id}, error={e}"
            )
            raise e



