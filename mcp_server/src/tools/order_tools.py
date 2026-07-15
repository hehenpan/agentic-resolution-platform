from main import mcp
from core.database import get_session
from schemas.order import (
    GetECommerceOrdersRequest,
    GetECommerceOrdersResponse,
    ECommerceOrderRecord,
    GetECommerceOrderDetailsRequest,
    GetECommerceOrderDetailsResponse,
    ECommerceOrderItemRecord,
    ECommerceOrderMeta
)
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


@mcp.tool()
async def get_ecommerce_order_details(req: GetECommerceOrderDetailsRequest) -> GetECommerceOrderDetailsResponse:
    """
    Queries the database to retrieve metadata and the itemized product list of an order by order_id.
    
    If the order does not exist, returns exists=False. You should check the 'exists'
    field first before describing the order details.
    """
    with get_session() as session:
        service = ECommerceOrderService(session=session)
        order, items = service.get_order_with_items(order_id=req.order_id)
        
        if order is None:
            return GetECommerceOrderDetailsResponse(exists=False)
            
        item_records = [
            ECommerceOrderItemRecord(
                item_id=item.item_id,
                sku_id=item.sku_id,
                sku_code=item.sku_code,
                name=item.name,
                quantity=item.quantity,
                price=item.price
            )
            for item in items
        ]
        
        order_meta = ECommerceOrderMeta(
            order_id=order.order_id,
            user_id=order.user_id,
            email=order.email,
            status=order.status,
            total_amount=order.total_amount,
            created_ts=order.created_ts
        )
        
        return GetECommerceOrderDetailsResponse(
            exists=True,
            order=order_meta,
            items=item_records
        )

