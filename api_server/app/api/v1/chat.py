from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.api.deps import get_current_user, get_chat_service
from app.models.models import User
from app.schemas.common import BizCode
from app.schemas.chat import (
    CreateChatSessionRequest,
    CreateChatSessionResponse,
    CreateChatSessionData,
    ChatSessionMeta,
    ChatSessionListResponse,
    ChatSessionListResponseData,
    ChatSessionStatus,
)
from app.services.chat_service import ChatService
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
