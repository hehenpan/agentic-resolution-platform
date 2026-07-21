import time
import uuid
from typing import Any, AsyncIterator
from pydantic import BaseModel, Field
from sqlmodel import Session
from app.models.models import ChatSession, ChatMessage, User, ChatMessageSenderType
from app.models.chat_wrapper import ChatDBWrapper
from app.schemas.chat import ChatSSEEvent, ChatSSEEventType
from app.schemas.chat_msg_payload import WebUserEventKind
from app.services.chat_event_projector import ChatEventProjector
from ai_agent_sdk import AgentAssistantId
from microservice_client.ai_agent_client import AIAgentServerInterface
from shared_common.schemas.ai_agent import (
    AgentCreateRunRequest,
    AgentTurnRequest,
    UserMessageInput,
    AgentDomainEventKind,
)
from utils.commons import generate_uuid_hex, get_current_ts
from loguru import logger


class PrepareTurnResult(BaseModel):
    """Internal service result returned by prepare_chat_turn pre-stream operations."""
    is_success: bool = Field(default=False, description="Whether pre-stream preparation succeeded.")
    thread_id: str | None = Field(default=None, description="LangGraph thread ID if preparation succeeded.")
    run_id: str | None = Field(default=None, description="Agent run ID if preparation succeeded.")
    error_message: str | None = Field(default=None, description="Human-readable error explanation if failed.")


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

    def _get_or_create_thread_id(
        self,
        chat_session_id: str,
        tenant_id: int,
        user_id: int,
    ) -> str:
        """
        Internal helper to get existing active thread_id or generate a new one.
        """
        latest_thread = self.wrapper.get_latest_thread_by_session(
            chat_session_id=chat_session_id
        )
        if latest_thread:
            return latest_thread.thread_id

        new_thread_id = f"thread_{generate_uuid_hex()}"
        self.wrapper.create_chat_thread(
            thread_id=new_thread_id,
            chat_session_id=chat_session_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        logger.info(
            f"Created new thread_id={new_thread_id} for chat_session_id={chat_session_id}"
        )
        return new_thread_id

    async def prepare_chat_turn(
        self,
        chat_session_id: str,
        current_user: User,
        message_content: str,
        ai_agent_client: AIAgentServerInterface,
    ) -> PrepareTurnResult:
        """
        Execute pre-stream validation and initialization steps (steps 1-4):
        1. Verify chat session ownership and status.
        2. Resolve or create thread_id.
        3. Create run_id via ai_agent_client and record ThreadRun.
        4. Save user message to ChatMessage table.
        Returns explicit PrepareTurnResult object without raising HTTP exceptions.
        """
        # 1. Verify session exists and belongs to current user
        session_obj = self.wrapper.get_chat_session_by_id(
            chat_session_id=chat_session_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
        )
        if not session_obj:
            logger.error(
                f"ChatSession not found or forbidden: chat_session_id={chat_session_id}, "
                f"user_id={current_user.user_id}"
            )
            return PrepareTurnResult(
                is_success=False,
                error_message="Chat session not found or access denied",
            )

        # 2. Get or create thread_id
        thread_id = self._get_or_create_thread_id(
            chat_session_id=chat_session_id,
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
        )

        # 3. Create run_id using ai_agent_sdk
        try:
            create_run_req = AgentCreateRunRequest(
                thread_id=thread_id,
                assistant_id=AgentAssistantId.SUPERVISOR,
            )
            run_res = await ai_agent_client.create_run(create_run_req)
            run_id = run_res.run_id
        except Exception as e:
            logger.exception(
                f"Failed to create agent run: chat_session_id={chat_session_id}, "
                f"thread_id={thread_id}, error={e}"
            )
            return PrepareTurnResult(
                is_success=False,
                error_message=f"Failed to initialize agent run: {e}",
            )

        # Record ThreadRun into DB
        self.wrapper.create_thread_run(
            run_id=run_id,
            thread_id=thread_id,
            chat_session_id=chat_session_id,
        )

        # 4. Save user message to ChatMessage table
        user_evt_id = f"evt_{generate_uuid_hex()}"
        user_payload = ChatEventProjector.project_user_message(
            content=message_content,
        )
        user_msg = ChatMessage(
            event_id=user_evt_id,
            chat_session_id=chat_session_id,
            thread_id=thread_id,
            run_id=run_id,
            sender_type=ChatMessageSenderType.USER,
            event_kind=WebUserEventKind.USER_MESSAGE.value,
            sequence=0,
            payload_json=user_payload.model_dump_json(),
            create_ts_ms=time.time() * 1000,
        )
        try:
            self.wrapper.save_chat_message(user_msg)
        except Exception as e:
            logger.error(
                f"Failed to save user message: event_id={user_evt_id}, error={e}"
            )

        return PrepareTurnResult(
            is_success=True,
            thread_id=thread_id,
            run_id=run_id,
        )

    async def stream_agent_turn(
        self,
        chat_session_id: str,
        thread_id: str,
        run_id: str,
        message_content: str,
        ai_agent_client: AIAgentServerInterface,
    ) -> AsyncIterator[str]:
        """
        Stream agent execution events as Server-Sent Events (SSE) (step 5).
        """
        turn_req = AgentTurnRequest(
            thread_id=thread_id,
            run_id=run_id,
            message=UserMessageInput(
                content=message_content,
            ),
        )

        try:
            domain_event_stream = ai_agent_client.stream_turn(turn_req)
            async for event in domain_event_stream:
                # Classify sender_type
                sender_type = ChatMessageSenderType.AGENT
                if event.kind in (
                    AgentDomainEventKind.RUN_COMPLETED,
                    AgentDomainEventKind.RUN_INTERRUPTED,
                    AgentDomainEventKind.RUN_FAILED,
                ):
                    sender_type = ChatMessageSenderType.SYSTEM

                # Save raw domain event payload to ChatMessage DB
                raw_event_kind = event.kind.value if hasattr(event.kind, "value") else str(event.kind)
                agent_msg = ChatMessage(
                    event_id=event.event_id,
                    chat_session_id=chat_session_id,
                    thread_id=event.thread_id,
                    run_id=event.run_id,
                    sender_type=sender_type,
                    event_kind=raw_event_kind,
                    sequence=event.sequence,
                    payload_json=event.model_dump_json(),
                    create_ts_ms=time.time() * 1000,
                )
                try:
                    self.wrapper.save_chat_message(agent_msg)
                except Exception as e:
                    logger.error(
                        f"Failed to save agent message to DB: event_id={event.event_id}, "
                        f"event_kind={raw_event_kind}, error={e}"
                    )

                # Project domain event to WebAgentDomainEvent model via ChatEventProjector (ACL) for SSE streaming
                web_event = ChatEventProjector.project_domain_event(event)
                web_event_kind = web_event.kind

                # Format and yield SSE event with projected payload
                try:
                    sse_event_type = ChatSSEEventType(web_event_kind)
                except ValueError:
                    sse_event_type = ChatSSEEventType.OUTPUT_PRODUCED

                sse_event = ChatSSEEvent(
                    event_id=web_event.event_id,
                    event_type=sse_event_type,
                    data=web_event.model_dump(mode="json"),
                )
                yield sse_event.to_sse_format()

        except Exception as e:
            logger.exception(
                f"Error during stream_turn processing: chat_session_id={chat_session_id}, "
                f"run_id={run_id}, error={e}"
            )
            err_event = ChatSSEEvent(
                event_id=f"evt_{generate_uuid_hex()}",
                event_type="error",
                data={"detail": f"Stream error: {e}"},
            )
            yield err_event.to_sse_format()




