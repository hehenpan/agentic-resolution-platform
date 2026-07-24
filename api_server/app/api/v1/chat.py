from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from fastapi.responses import StreamingResponse
from app.api.deps import get_current_user, get_chat_service, get_ai_agent_client, get_rbac_service
from app.models.models import User
from app.services.rbac_service import RBACServiceBase, Permission
from app.schemas.common import BizCode
from app.schemas.chat import (
    CreateChatSessionRequest,
    CreateChatSessionResponse,
    CreateChatSessionData,
    ChatSessionMeta,
    ChatSessionListResponse,
    ChatSessionListResponseData,
    ChatSessionStatus,
    ChatMessageSenderType,
    ChatMessageItem,
    ChatMessageListResponseData,
    ChatMessageListResponse,
    SendChatMessageRequest,
    ResumeChatMessageRequest,
)
from app.services.chat_service import ChatService
from microservice_client.ai_agent_client import AIAgentServerInterface
from loguru import logger



chat_router = APIRouter(prefix="/chat", tags=["chat"])


@chat_router.post(
    "/sessions",
    response_model=CreateChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Chat Session"
)
async def create_chat_session(
    request: CreateChatSessionRequest,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    1. Extract user_id and tenant_id directly from authenticated current_user context.
    2. Create a ChatSession database record only.
    3. Return response immediately upon success without interacting with ai_agent.
    """
    try:
        session_obj = chat_service.create_chat_session(
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
            title=request.title,
        )
        meta = ChatSessionMeta(
            id=session_obj.id,
            chat_session_id=session_obj.chat_session_id,
            tenant_id=session_obj.tenant_id,
            user_id=session_obj.user_id,
            title=session_obj.title,
            status=ChatSessionStatus(session_obj.status),
            create_ts=session_obj.create_ts,
            update_ts=session_obj.update_ts,
        )
        return CreateChatSessionResponse(
            code=BizCode.SUCCESS,
            message="Chat session created successfully",
            data=CreateChatSessionData(
                chat_session_id=session_obj.chat_session_id,
                session_info=meta,
            ),
        )
    except Exception as e:
        logger.exception(f"Error creating chat session: user_id={current_user.user_id}, error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create chat session",
        )


@chat_router.get(
    "/sessions",
    response_model=ChatSessionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Chat Sessions for Authenticated User"
)
async def list_chat_sessions(
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of items to return."),
    cursor: str | None = Query(default=None, description="Composite cursor string in '{create_ts}_{id}' format. Returns sessions created before this position."),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    1. Query chat session metadata list strictly for the logged-in user using cursor-based pagination.
    2. Does not accept user_id parameter from request to prevent privilege escalation.
    3. ABAC permission checks bypassed for now.
    """
    try:
        sessions, has_more, next_cursor = chat_service.list_chat_sessions_by_user(
            tenant_id=current_user.tenant_id,
            user_id=current_user.user_id,
            limit=limit,
            cursor=cursor,
        )
        items = [
            ChatSessionMeta(
                id=s.id,
                chat_session_id=s.chat_session_id,
                tenant_id=s.tenant_id,
                user_id=s.user_id,
                title=s.title,
                status=ChatSessionStatus(s.status),
                create_ts=s.create_ts,
                update_ts=s.update_ts,
            )
            for s in sessions
        ]
        return ChatSessionListResponse(
            code=BizCode.SUCCESS,
            message="Chat sessions retrieved successfully",
            data=ChatSessionListResponseData(
                has_more=has_more,
                next_cursor=next_cursor,
                items=items,
            ),
        )
    except Exception as e:
        logger.exception(f"Error querying chat sessions: user_id={current_user.user_id}, error={e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query chat sessions",
        )


@chat_router.get(
    "/sessions/{chat_session_id}/messages",
    response_model=ChatMessageListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Chat History Messages for Session"
)
async def list_chat_messages(
    chat_session_id: str = Path(..., description="Unique business chat session string ID."),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of items to return."),
    cursor: str | None = Query(default=None, description="Cursor string representing create_ts_ms timestamp."),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    rbac_service: RBACServiceBase = Depends(get_rbac_service),
):
    """
    Query chat message history for a given session using cursor-based pagination on create_ts_ms.
    Returns messages ordered by create_ts_ms descending.
    """
    # Enforce RBAC permission check
    if not rbac_service.has_permission(
        user=current_user,
        permission=Permission.USER_READ,
        resource_tenant_id=current_user.tenant_id
    ):
        logger.error(
            f"Chat history query permission denied: user_id={current_user.user_id}, "
            f"tenant_id={current_user.tenant_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )

    # Verify chat session ownership and status
    session_obj = chat_service.wrapper.get_chat_session_by_id(
        chat_session_id=chat_session_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.user_id,
    )
    if not session_obj:
        logger.error(
            f"ChatSession not found or forbidden: chat_session_id={chat_session_id}, "
            f"user_id={current_user.user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )

    # Enforce tenant isolation / cross-tenant check via RBAC
    if not rbac_service.has_permission(
        user=current_user,
        permission=Permission.USER_READ,
        resource_tenant_id=session_obj.tenant_id
    ):
        logger.error(
            f"Cross-tenant chat history query permission denied: chat_session_id={chat_session_id}, "
            f"user_id={current_user.user_id}, "
            f"user_tenant_id={current_user.tenant_id}, "
            f"session_tenant_id={session_obj.tenant_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )

    try:
        messages, has_more, next_cursor = chat_service.list_chat_messages_by_session(
            chat_session_id=chat_session_id,
            limit=limit,
            cursor=cursor,
        )
        items = [
            ChatMessageItem(
                id=m.id,
                event_id=m.event_id,
                chat_session_id=m.chat_session_id,
                thread_id=m.thread_id,
                run_id=m.run_id,
                sender_type=ChatMessageSenderType(m.sender_type),
                event_kind=m.event_kind,
                sequence=m.sequence,
                payload_json=m.payload_json,
                create_ts_ms=m.create_ts_ms,
            )
            for m in messages
        ]
        return ChatMessageListResponse(
            code=BizCode.SUCCESS,
            message="Chat history messages retrieved successfully",
            data=ChatMessageListResponseData(
                has_more=has_more,
                next_cursor=next_cursor,
                items=items,
            ),
        )
    except ValueError as val_err:
        logger.error(
            f"Invalid cursor parameter for querying chat messages: chat_session_id={chat_session_id}, "
            f"cursor={cursor}, error={val_err}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as e:
        logger.exception(
            f"Error querying chat messages: chat_session_id={chat_session_id}, "
            f"user_id={current_user.user_id}, error={e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to query chat history messages",
        )


@chat_router.post(
    "/sessions/{chat_session_id}/messages",
    status_code=status.HTTP_200_OK,
    summary="Send Message in Chat Session and Stream Response via SSE"
)
async def send_chat_message(
    chat_session_id: str = Path(..., description="Unique business chat session string ID."),
    request: SendChatMessageRequest = ...,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    ai_agent_client: AIAgentServerInterface = Depends(get_ai_agent_client),
    rbac_service: RBACServiceBase = Depends(get_rbac_service),
):
    """
    1. Receive user message content and metadata.
    2. Call chat_service.prepare_chat_turn to perform pre-stream initialization (steps 1-4).
    3. Check result: If failed, Router raises appropriate HTTP exception (404/500).
    4. If success, start step 5 SSE stream and return StreamingResponse.
    """
    # Enforce RBAC permission check
    if not rbac_service.has_permission(
        user=current_user,
        permission=Permission.USER_READ,
        resource_tenant_id=current_user.tenant_id
    ):
        logger.error(
            f"Send chat message permission denied: user_id={current_user.user_id}, "
            f"tenant_id={current_user.tenant_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )

    prep_result = await chat_service.prepare_chat_turn(
        chat_session_id=chat_session_id,
        current_user=current_user,
        message_content=request.content,
        ai_agent_client=ai_agent_client,
    )
    if not prep_result.is_success:
        logger.error(
            f"Failed to prepare chat turn: chat_session_id={chat_session_id}, "
            f"user_id={current_user.user_id}, error={prep_result.error_message}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=prep_result.error_message,
        )

    event_generator = chat_service.stream_agent_turn(
        chat_session_id=chat_session_id,
        thread_id=prep_result.thread_id,
        run_id=prep_result.run_id,
        ai_agent_client=ai_agent_client,
    )
    return StreamingResponse(
        event_generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@chat_router.post(
    "/sessions/{chat_session_id}/resume",
    status_code=status.HTTP_200_OK,
    summary="Resume Interrupted Chat Session Turn and Stream Response via SSE"
)
async def resume_chat_message(
    chat_session_id: str = Path(..., description="Unique business chat session string ID."),
    request: ResumeChatMessageRequest = ...,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    ai_agent_client: AIAgentServerInterface = Depends(get_ai_agent_client),
    rbac_service: RBACServiceBase = Depends(get_rbac_service),
):
    """
    1. Validate resume payload and schema_id.
    2. Extract latest interrupt_id and resume_cursor from DB.
    3. Save user resume input message to chat_message table.
    4. Call ai_agent_sdk resume_turn and stream response events via SSE.
    """
    # Enforce RBAC permission check
    if not rbac_service.has_permission(
        user=current_user,
        permission=Permission.USER_READ,
        resource_tenant_id=current_user.tenant_id
    ):
        logger.error(
            f"Resume chat message permission denied: user_id={current_user.user_id}, "
            f"tenant_id={current_user.tenant_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )

    if request.chat_session_id != chat_session_id:
        logger.error(
            f"Path parameter chat_session_id '{chat_session_id}' mismatch with body chat_session_id '{request.chat_session_id}'"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chat_session_id in path does not match request body",
        )

    prep_result = await chat_service.prepare_resume_turn(
        chat_session_id=chat_session_id,
        thread_id=request.thread_id,
        schema_id=request.schema_id,
        resume_payload=request.resume_payload,
        current_user=current_user,
        ai_agent_client=ai_agent_client,
        explicit_interrupt_id=request.interrupt_id,
    )
    if not prep_result.is_success:
        logger.error(
            f"Failed to prepare resume turn: chat_session_id={chat_session_id}, "
            f"user_id={current_user.user_id}, error={prep_result.error_message}"
        )
        err_msg = (prep_result.error_message or "").lower()
        status_code = (
            status.HTTP_400_BAD_REQUEST
            if "not found" in err_msg or "no pending interrupt" in err_msg or "invalid" in err_msg or "unsupported" in err_msg
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        raise HTTPException(
            status_code=status_code,
            detail=prep_result.error_message,
        )

    event_generator = chat_service.stream_resume_agent_turn(
        chat_session_id=chat_session_id,
        thread_id=prep_result.thread_id,
        run_id=prep_result.run_id,
        interrupt_id=prep_result.interrupt_id,
        resume_cursor=prep_result.resume_cursor,
        schema_id=request.schema_id,
        validated_input=prep_result.validated_input,
        ai_agent_client=ai_agent_client,
    )
    return StreamingResponse(
        event_generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )



