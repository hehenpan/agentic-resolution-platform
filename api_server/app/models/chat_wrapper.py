from sqlmodel import Session, select, func, or_, and_
from app.models.models import ChatSession, ChatSessionStatus
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
