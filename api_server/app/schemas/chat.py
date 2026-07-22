import json
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
from app.schemas.chat_msg_payload import WebHumanInputSchemaId
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


class ChatMessageSenderType(int, Enum):
    """Sender type for chat messages in API contracts (1=USER, 2=AGENT, 3=SYSTEM)."""
    USER = 1
    AGENT = 2
    SYSTEM = 3


class ChatMessageItem(BaseModel):
    """Schema representing an individual chat message or event record."""
    id: int | None = Field(default=None, description="Primary key integer ID of message record.")
    event_id: str = Field(description="Domain event ID or unique message string ID.")
    chat_session_id: str = Field(description="Unique business chat session string ID.")
    thread_id: str = Field(description="Logic link to agent execution thread ID.")
    run_id: str = Field(description="Logic link to agent run ID.")
    sender_type: ChatMessageSenderType = Field(description="Sender type (1=USER, 2=AGENT, 3=SYSTEM).")
    event_kind: str = Field(description="Kind or type of the message event.")
    sequence: int = Field(default=0, description="Sequence order within the run execution.")
    payload_json: str = Field(description="Raw JSON string serialized payload of the event/message.")
    create_ts_ms: float = Field(description="Floating-point Unix millisecond timestamp when message was created.")


class ChatMessageListResponseData(BaseModel):
    """Data payload returned for chat history messages query using cursor pagination."""
    has_more: bool = Field(description="Indicates whether more messages are available in subsequent pages.")
    next_cursor: str | None = Field(
        default=None,
        description="Cursor string representing create_ts_ms to pass for fetching next page."
    )
    items: list[ChatMessageItem] = Field(description="List of chat message items ordered by create_ts_ms descending.")


class ChatMessageListResponse(ResponseBase):
    """HTTP Response model for querying chat history messages."""
    data: ChatMessageListResponseData = Field(description="Query result payload containing message items.")


class SendChatMessageRequest(BaseModel):
    """Request payload for sending a user chat message."""
    content: str = Field(..., description="Message text content sent by the user.", min_length=1)


class ResumeChatMessageRequest(BaseModel):
    """Request payload for resuming an interrupted chat session turn."""
    schema_id: WebHumanInputSchemaId = Field(
        ...,
        description="Schema identifier defining the structure of resume_payload. e.g. human_input.get_orders.v1",
    )
    resume_payload: dict[str, Any] = Field(
        ...,
        description="User input payload dictionary to resolve the interrupt.",
    )
    chat_session_id: str = Field(
        ...,
        description="Unique business chat session identifier.",
    )
    thread_id: str = Field(
        ...,
        description="LangGraph thread identifier bound to the session.",
    )
    interrupt_id: str | None = Field(
        default=None,
        description="Optional explicit interrupt ID. If omitted, server automatically fetches the latest interrupt from DB.",
    )



class ChatSSEEventType(str, Enum):
    """Discriminator enum identifying Server-Sent Event (SSE) wire event types."""
    USER_MESSAGE = "user_message"
    OUTPUT_PRODUCED = "agent.output_produced"
    PROGRESS_REPORTED = "agent.progress_reported"
    HUMAN_INPUT_REQUESTED = "agent.human_input_requested"
    RUN_COMPLETED = "agent.run_completed"
    RUN_INTERRUPTED = "agent.run_interrupted"
    RUN_FAILED = "agent.run_failed"


class ChatSSEEvent(BaseModel):
    """Envelope representing a Server-Sent Event (SSE) pushed to client."""
    event_id: str = Field(..., description="Unique event identifier for deduplication/tracking.")
    event_type: ChatSSEEventType = Field(..., description="Domain event discriminator enum.")
    data: dict[str, Any] = Field(..., description="Event payload dictionary.")

    def to_sse_format(self) -> str:
        """Serialize event to standard SSE wire format string."""
        payload_str = json.dumps(self.data, ensure_ascii=False)
        event_type_str = self.event_type.value if isinstance(self.event_type, Enum) else str(self.event_type)
        return f"event: {event_type_str}\ndata: {payload_str}\n\n"
