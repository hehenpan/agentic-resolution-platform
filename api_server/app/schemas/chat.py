from enum import Enum
from pydantic import BaseModel, Field
from app.schemas.common import ResponseBase, BizCode


class ChatSessionStatus(int, Enum):
    """Represent the lifecycle status of a chat session in API contracts."""
    INVALID = 0
    ACTIVE = 1
    CLOSED = 2


class CreateChatSessionRequest(BaseModel):
    """Request payload for creating a new chat session."""
    title: str | None = Field(
        default="New Chat",
        description="Optional display title for the chat session.",
        max_length=255,
    )


class ChatSessionMeta(BaseModel):
    """Metadata representing a chat session."""
    id: int | None = Field(default=None, description="Primary key integer ID.")
    chat_session_id: str = Field(description="Unique business session string ID.")
    tenant_id: int = Field(description="Tenant ID owning this session.")
    user_id: int = Field(description="User ID owning this session.")
    title: str = Field(description="Display title of the chat session.")
    status: ChatSessionStatus = Field(description="Lifecycle status of session (1=ACTIVE, 0=INVALID, 2=CLOSED).")
    create_ts: int = Field(description="Creation Unix timestamp in seconds.")
    update_ts: int = Field(description="Last update Unix timestamp in seconds.")


class CreateChatSessionData(BaseModel):
    """Data payload returned after creating a chat session."""
    chat_session_id: str = Field(description="Newly generated chat session string ID.")
    session_info: ChatSessionMeta = Field(description="Complete metadata of the created chat session.")


class CreateChatSessionResponse(ResponseBase):
    """HTTP Response model for chat session creation."""
    data: CreateChatSessionData = Field(description="Creation result payload.")


class ChatSessionListResponseData(BaseModel):
    """Data payload returned for chat session list query using cursor pagination."""
    has_more: bool = Field(description="Indicates whether more items are available in subsequent pages.")
    next_cursor: str | None = Field(default=None, description="Composite cursor string in '{create_ts}_{id}' format to pass for fetching the next page.")
    items: list[ChatSessionMeta] = Field(description="List of chat session metadata objects.")


class ChatSessionListResponse(ResponseBase):
    """HTTP Response model for listing chat sessions."""
    data: ChatSessionListResponseData = Field(description="Query result payload containing session list.")
