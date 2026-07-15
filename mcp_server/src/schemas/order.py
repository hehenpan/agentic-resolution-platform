from pydantic import BaseModel, Field
from typing import List, Optional
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


class GetECommerceOrderDetailsRequest(BaseModel):
    """
    Pydantic schema representing the request parameters to query ECommerceOrder details.
    """
    order_id: int = Field(..., description="The unique ID of the order to retrieve details for")


class ECommerceOrderItemRecord(BaseModel):
    """
    Pydantic schema representing a single product item in an order.
    """
    item_id: int = Field(..., description="The unique order item ID")
    sku_id: int = Field(..., description="The unique SKU ID")
    sku_code: str = Field(..., description="The unique SKU code")
    name: str = Field(..., description="The name of the product")
    quantity: int = Field(..., description="The quantity purchased")
    price: float = Field(..., description="The price of the item at purchase")


class ECommerceOrderMeta(BaseModel):
    """
    Pydantic schema representing the metadata of an order.
    """
    order_id: int = Field(..., description="The unique order ID")
    user_id: int = Field(..., description="The unique user ID")
    email: str = Field(..., description="The customer email")
    status: OrderStatus = Field(..., description="The status of the order")
    total_amount: float = Field(..., description="The total amount of the order")
    created_ts: int = Field(..., description="The creation timestamp of the order (Unix epoch)")


class GetECommerceOrderDetailsResponse(BaseModel):
    """
    Pydantic schema representing the detailed response containing order metadata and item list.
    """
    exists: bool = Field(..., description="Whether the order exists. Check this field first before accessing other fields.")
    order: Optional[ECommerceOrderMeta] = Field(default=None, description="The order metadata, present if exists=True")
    items: List[ECommerceOrderItemRecord] = Field(default_factory=list, description="The list of product items in the order, present if exists=True")




