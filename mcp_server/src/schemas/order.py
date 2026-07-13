from pydantic import BaseModel, Field
from typing import List
from models.db_models import OrderStatus

class GetECommerceOrdersRequest(BaseModel):
    """
    Pydantic schema representing the request parameters to query ECommerceOrders.
    """
    email: str = Field(..., description="The email address of the customer to query orders for")


class ECommerceOrderRecord(BaseModel):
    """
    Pydantic schema representing a single order record in the query response.
    """
    order_id: int = Field(..., description="The unique order ID")
    user_id: int = Field(..., description="The unique user ID")
    email: str = Field(..., description="The email of the customer")
    status: OrderStatus = Field(..., description="The status of the order (0: PENDING, 1: PAID, 2: SHIPPED, 3: COMPLETED, 4: CANCELLED)")
    total_amount: float = Field(..., description="The total cost of the order")
    created_ts: int = Field(..., description="The creation timestamp of the order (Unix epoch)")


class GetECommerceOrdersResponse(BaseModel):
    """
    Pydantic schema representing the list of orders returned.
    """
    orders: List[ECommerceOrderRecord] = Field(default_factory=list, description="List of order records found, sorted by created_ts descending.")
