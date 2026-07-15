from main import mcp
from core.database import get_session
from shared_common.schemas.mcp_server.user import GetECommerceUserRequest, GetECommerceUserResponse
from services.user_service import ECommerceUserService

@mcp.tool()
async def get_ecommerce_user(req: GetECommerceUserRequest) -> GetECommerceUserResponse:
    """
    Queries the ECommerceUser database table to search for user metadata by email.
    
    If the user exists, returns user profile, status, and creation time.
    If the user does not exist, returns exists=False. You should check the 'exists' 
    field first before describing the user status to the customer.
    """
    with get_session() as session:
        service = ECommerceUserService(session=session)
        user = service.get_user(email=req.email)
        
        if user is None:
            return GetECommerceUserResponse(exists=False)
            
        # Map values to the response object inside the session context to prevent DetachedInstanceError
        return GetECommerceUserResponse(
            exists=True,
            user_id=user.user_id,
            user_name=user.user_name,
            email=user.email,
            status=user.status,
            phone=user.phone,
            create_ts=user.create_ts
        )
