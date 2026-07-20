from sqlmodel import SQLModel, Field, Index
import enum 
from enum import Enum
import time
from utils.commons import get_current_ts, generate_user_id, generate_random_id
from app.core.constants import (
    DB_CHAR_FIELD_SHORT_MAX_LEN, 
    DB_CHAR_FIELD_MEDIUM_MAX_LEN, 
    DB_CHAR_FIELD_LONG_MAX_LEN,
    SESSION_EXPIRE_SECONDS
)




class UserStatus(int, Enum):
    INACTIVE = 0
    ACTIVE = 1

class UserType(int, Enum):
    ADMIN = 0
    USER = 1
    TENANT_ADMIN = 2
    

#user table
class User(SQLModel, table = True):
    email: str = Field(primary_key=True,max_length=DB_CHAR_FIELD_MEDIUM_MAX_LEN)
    user_id: int = Field(default_factory=generate_user_id, unique=True)
    pwd_md5: str = Field(max_length=DB_CHAR_FIELD_SHORT_MAX_LEN)
    create_ts: int = Field(default_factory=get_current_ts)
    status: UserStatus = Field(default=UserStatus.ACTIVE)
    user_type: UserType = Field(default=UserType.USER)
    tenant_id: int = Field(default=1)


class SessionStatus(int, Enum):
    ACTIVE = 1
    INVALID = 0

class SessionInfo(SQLModel, table = True):
    sessionid: str = Field(primary_key=True)
    user_id: int = Field()
    tenant_id: int = Field()
    email: str = Field(max_length=DB_CHAR_FIELD_SHORT_MAX_LEN)
    create_ts: int = Field(default_factory=get_current_ts)
    expire_ts: int = Field(default_factory=lambda: get_current_ts() + SESSION_EXPIRE_SECONDS)
    status: SessionStatus = Field(default=SessionStatus.ACTIVE)


class FileStorageType(int, Enum):
    LOCAL = 0
    S3 = 1

class FileStatus(int, Enum):
    ACTIVE = 1
    INVALID = 0

class FileSyncStatus(int, Enum):
    PENDING = 0
    SYNCED = 1
    FAILED = 2

class FileInfo(SQLModel, table = True):
    __table_args__ = (
        Index("idx_fileinfo_tenant_create_file", "tenant_id", "create_ts", "file_id"),
    )
    file_id: int = Field(primary_key=True, default_factory=generate_random_id)
    tenant_id: int = Field()
    owner_user_id: int = Field()
    owner_email: str = Field(max_length=DB_CHAR_FIELD_MEDIUM_MAX_LEN)
    file_name: str = Field(max_length=DB_CHAR_FIELD_MEDIUM_MAX_LEN)
    file_type: str = Field(max_length=DB_CHAR_FIELD_SHORT_MAX_LEN)  #file_type in html, pdf, txt, doc, docx, etc
    file_md5_hash: str = Field(max_length=DB_CHAR_FIELD_MEDIUM_MAX_LEN)
    file_storage_location: str = Field(max_length=DB_CHAR_FIELD_MEDIUM_MAX_LEN)
    file_storage_type: FileStorageType = Field(default=FileStorageType.S3)
    file_size: int = Field()
    create_ts: int = Field(default_factory=get_current_ts)
    status: FileStatus = Field(default=FileStatus.ACTIVE)
    vector_db_sync_status: FileSyncStatus = Field(default=FileSyncStatus.PENDING) 


class ChatSessionStatus(int, Enum):
    """Represent the lifecycle status of a chat session."""
    INVALID = 0
    ACTIVE = 1
    CLOSED = 2


class ChatThreadStatus(int, Enum):
    """Represent the active or archived status of a chat thread."""
    ARCHIVED = 0
    ACTIVE = 1


class ChatMessageSenderType(int, Enum):
    """Represent the sender type of a chat message."""
    USER = 1
    AGENT = 2
    SYSTEM = 3


class ChatSession(SQLModel, table=True):
    """Maintain a customer service session context."""
    __tablename__ = "chat_session"
    __table_args__ = (
        Index("idx_chatsession_user_create", "user_id", "create_ts"),
    )

    id: int | None = Field(default=None, primary_key=True)
    chat_session_id: str = Field(unique=True, index=True, description="Unique business session ID.")
    tenant_id: int = Field(description="Tenant ID owning this session.")
    user_id: int = Field(description="Customer service user ID owning this session.")
    title: str = Field(max_length=DB_CHAR_FIELD_LONG_MAX_LEN, default="新对话", description="Session title.")
    status: ChatSessionStatus = Field(default=ChatSessionStatus.ACTIVE, description="Session status.")
    create_ts: int = Field(default_factory=get_current_ts, description="Session creation Unix timestamp.")
    update_ts: int = Field(default_factory=get_current_ts, description="Session update Unix timestamp.")


class ChatThread(SQLModel, table=True):
    """Map a chat session to a LangGraph thread."""
    __tablename__ = "chat_thread"
    __table_args__ = (
        Index("idx_chatthread_session_create", "chat_session_id", "create_ts"),
    )

    id: int | None = Field(default=None, primary_key=True)
    thread_id: str = Field(unique=True, index=True, description="LangGraph thread ID.")
    chat_session_id: str = Field(description="Logic link to chat session ID.")
    tenant_id: int = Field(index=True, description="Tenant ID.")
    user_id: int = Field(description="Customer service user ID.")
    status: ChatThreadStatus = Field(default=ChatThreadStatus.ACTIVE, description="Thread status.")
    create_ts: int = Field(default_factory=get_current_ts, description="Thread creation Unix timestamp.")
    update_ts: int = Field(default_factory=get_current_ts, description="Thread update Unix timestamp.")


class ThreadRun(SQLModel, table=True):
    """Record runs triggered on a thread."""
    __tablename__ = "thread_run"
    __table_args__ = (
        Index("idx_threadrun_thread_create", "thread_id", "create_ts"),
    )

    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(unique=True, index=True, description="LangGraph run ID.")
    thread_id: str = Field(description="Logic link to thread ID.")
    chat_session_id: str = Field(description="Logic link to chat session ID.")
    create_ts: int = Field(default_factory=get_current_ts, description="Run creation Unix timestamp.")


class ChatMessage(SQLModel, table=True):
    """Record individual messages and events in a chat session."""
    __tablename__ = "chat_message"
    __table_args__ = (
        Index("idx_chatmessage_session_create", "chat_session_id", "create_ts_ms"),
    )

    id: int | None = Field(default=None, primary_key=True)
    event_id: str = Field(unique=True, description="Domain event ID or unique message ID.")
    chat_session_id: str = Field(description="Logic link to chat session ID.")
    thread_id: str = Field(index=True, description="Logic link to thread ID.")
    run_id: str = Field(index=True, description="Logic link to run ID.")
    sender_type: ChatMessageSenderType = Field(description="Sender type (1=USER, 2=AGENT, 3=SYSTEM).")
    event_kind: str = Field(description="Kind of event/message.")
    sequence: int = Field(default=0, description="Sequence order within the run execution.")
    payload_json: str = Field(description="JSON serialized payload of the event/message.")
    create_ts_ms: float = Field(
        default_factory=lambda: time.time() * 1000,
        description="Floating-point Unix millisecond timestamp."
    )