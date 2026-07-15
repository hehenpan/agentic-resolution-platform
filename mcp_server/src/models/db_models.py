from sqlmodel import SQLModel, Field, Index
from enum import Enum
from typing import Optional
import time

class ReturnStatus(int, Enum):
    REQUESTED = 0
    APPROVED = 1
    REJECTED = 2
    RECEIVED = 3
    REFUNDED = 4
    CANCELLED = 5


class ReturnReasonCode(int, Enum):
    CHANGE_OF_MIND = 0
    DAMAGED = 1
    WRONG_ITEM = 2
    NOT_AS_DESCRIBED = 3
    LATE_DELIVERY = 4


class ItemCondition(int, Enum):
    UNOPENED = 0
    OPENED = 1
    USED = 2
    DAMAGED = 3


class ReturnResolutionType(int, Enum):
    REFUND = 0
    STORE_CREDIT = 1
    REJECT = 2


class RefundMethod(int, Enum):
    ORIGINAL_PAYMENT = 0
    STORE_CREDIT = 1


class OrderStatus(int, Enum):
    PENDING = 0
    PAID = 1
    SHIPPED = 2
    COMPLETED = 3
    CANCELLED = 4


class UserStatus(int, Enum):
    INACTIVE = 0
    ACTIVE = 1


class ShipmentStatus(int, Enum):
    PENDING = 0
    SHIPPED = 1
    IN_TRANSIT = 2
    DELIVERED = 3
    EXCEPTION = 4



class CalculationHistory(SQLModel, table=True):
    """
    SQLModel database table representing calculation execution history.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    a: float
    b: float
    result: float
    created_ts: int



class ECommerceUser(SQLModel, table=True):
    user_id: int = Field(default=None, primary_key=True)
    user_name: str = Field(default="")
    pwd: str = Field(default="")
    email: str = Field(default="", unique=True)
    status: UserStatus = Field(default=UserStatus.ACTIVE)
    phone: str = Field(default="")
    create_ts: int = Field(default=0)
    
    
# Order System Tables
class ECommerceSKU(SQLModel, table=True):
    sku_id: Optional[int] = Field(default=None, primary_key=True)
    sku_code: str = Field(default="", unique=True)
    name: str = Field(default="")
    price: float = Field(default=0.0)
    stock: int = Field(default=0)
    description: Optional[str] = Field(default="")


class ECommerceOrder(SQLModel, table=True):
    __table_args__ = (
        Index("idx_order_email_created_ts", "email", "created_ts"),
    )
    
    order_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(default=None)
    email: str = Field(default="")
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    total_amount: float = Field(default=0.0)
    #shipping_address: str = Field(default="")
    created_ts: int = Field(default=0)


class ECommerceOrderItem(SQLModel, table=True):
    item_id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(default=None, index=True)
    sku_id: int = Field(default=None)
    sku_code: str = Field(default="")
    name: str = Field(default="")
    quantity: int = Field(default=1)
    price: float = Field(default=0.0)


class ECommerceShipment(SQLModel, table=True):
    shipment_id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(default=None, index=True)
    tracking_number: str = Field(default="", unique=True, index=True)
    carrier: str = Field(default="")
    status: ShipmentStatus = Field(default=ShipmentStatus.PENDING)
    shipping_address: str = Field(default="")
    created_ts: int = Field(default=0)
    updated_ts: int = Field(default=0)


class ECommerceShipmentEvent(SQLModel, table=True):
    event_id: Optional[int] = Field(default=None, primary_key=True)
    shipment_id: int = Field(default=None, index=True)
    order_id: int = Field(default=None, index=True)
    status: ShipmentStatus = Field(default=ShipmentStatus.PENDING)
    location: str = Field(default="")
    description: str = Field(default="")
    event_ts: int = Field(default=0)


class ECommerceReturnPolicy(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    policy_name: str = Field(default="")
    order_type: str = Field(default="general")
    return_window_days: int = Field(default=30)
    allow_change_of_mind: bool = Field(default=True)
    allow_damaged_return: bool = Field(default=True)
    allow_wrong_item_return: bool = Field(default=True)
    requires_unopened: bool = Field(default=False)
    manual_review_if_opened: bool = Field(default=True)
    refund_method: RefundMethod = Field(default=RefundMethod.ORIGINAL_PAYMENT)
    active: bool = Field(default=True)
    policy_text: str = Field(default="")
    created_at: int = Field(default_factory=lambda: int(time.time()))
    updated_at: int = Field(default_factory=lambda: int(time.time()))


class ECommerceReturnRequest(SQLModel, table=True):
    __table_args__ = (
        Index("idx_return_order_created", "order_id", "created_at"),
        Index("idx_return_customer_created", "customer_id", "created_at"),
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(default=None)
    customer_id: int = Field(default=None)
    status: ReturnStatus = Field(default=ReturnStatus.REQUESTED)
    reason_code: ReturnReasonCode = Field(default=ReturnReasonCode.CHANGE_OF_MIND)
    reason_text: str = Field(default="")
    item_condition: ItemCondition = Field(default=ItemCondition.UNOPENED)
    requested_at: int = Field(default_factory=lambda: int(time.time()))
    approved_at: Optional[int] = Field(default=None)
    rejected_at: Optional[int] = Field(default=None)
    received_at: Optional[int] = Field(default=None)
    closed_at: Optional[int] = Field(default=None)
    resolution_type: Optional[ReturnResolutionType] = Field(default=None)
    created_by: Optional[int] = Field(default=None, description="The user_id of the customer service agent operating this return")
    created_at: int = Field(default_factory=lambda: int(time.time()))
    updated_at: int = Field(default_factory=lambda: int(time.time()))