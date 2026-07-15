from main import mcp
from core.database import get_session
from schemas.returns import (
    GetReturnRequestsByOrderRequest,
    GetReturnRequestsByOrderResponse,
    GetReturnRequestsByCustomerRequest,
    GetReturnRequestsByCustomerResponse,
    GetReturnRequestRecord,
)
from services.return_service import ECommerceReturnService

@mcp.tool()
async def get_return_requests_by_order(req: GetReturnRequestsByOrderRequest) -> GetReturnRequestsByOrderResponse:
    """
    Queries return requests associated with a specific order_id.
    
    Returns the matching return request record if found.
    """
    with get_session() as session:
        service = ECommerceReturnService(session=session)
        r = service.get_return_by_order(order_id=req.order_id)
        if r is None:
            return GetReturnRequestsByOrderResponse(returns=None)
            
        record = GetReturnRequestRecord(
            id=r.id,
            order_id=r.order_id,
            customer_id=r.customer_id,
            status=r.status,
            reason_code=r.reason_code,
            reason_text=r.reason_text,
            item_condition=r.item_condition,
            requested_at=r.requested_at,
            approved_at=r.approved_at,
            rejected_at=r.rejected_at,
            received_at=r.received_at,
            closed_at=r.closed_at,
            resolution_type=r.resolution_type,
            created_by=r.created_by,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        return GetReturnRequestsByOrderResponse(returns=record)


@mcp.tool()
async def get_return_requests_by_customer(req: GetReturnRequestsByCustomerRequest) -> GetReturnRequestsByCustomerResponse:
    """
    Queries return requests associated with a specific customer_id (user_id).
    
    Returns a list of matching return request records, sorted by creation time descending.
    """
    with get_session() as session:
        service = ECommerceReturnService(session=session)
        returns = service.get_returns_by_customer(customer_id=req.customer_id)
        records = [
            GetReturnRequestRecord(
                id=r.id,
                order_id=r.order_id,
                customer_id=r.customer_id,
                status=r.status,
                reason_code=r.reason_code,
                reason_text=r.reason_text,
                item_condition=r.item_condition,
                requested_at=r.requested_at,
                approved_at=r.approved_at,
                rejected_at=r.rejected_at,
                received_at=r.received_at,
                closed_at=r.closed_at,
                resolution_type=r.resolution_type,
                created_by=r.created_by,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in returns
        ]
        return GetReturnRequestsByCustomerResponse(returns=records)
