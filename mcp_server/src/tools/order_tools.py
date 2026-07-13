from main import mcp
from core.database import get_session
from schemas.order import GetECommerceOrdersRequest, GetECommerceOrdersResponse, ECommerceOrderRecord
from services.order_service import ECommerceOrderService

@mcp.tool()
async def get_ecommerce_orders(req: GetECommerceOrdersRequest) -> GetECommerceOrdersResponse:
    """
    Queries the ECommerceOrder database table to search for all orders by customer email.
    
    Returns a list of order records sorted by creation timestamp descending.
    If no orders are found, returns an empty list.
    """
    with get_session() as session:
        service = ECommerceOrderService(session=session)
        orders = service.get_user_orders(email=req.email)
        
        # Convert SQLModel instances to Pydantic ECommerceOrderRecord representations
        # inside the active session block to avoid DetachedInstanceError.
        records = [
            ECommerceOrderRecord(
                order_id=o.order_id,
                user_id=o.user_id,
                email=o.email,
                status=o.status,
                total_amount=o.total_amount,
                created_ts=o.created_ts
            )
            for o in orders
        ]
        return GetECommerceOrdersResponse(orders=records)
