from sqlmodel import SQLModel, Field, Index
from typing import Optional
from enum import Enum

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
    order_id: int = Field(default=None)
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
    status: ShipmentStatus = Field(default=ShipmentStatus.PENDING)
    location: str = Field(default="")
    description: str = Field(default="")
    event_ts: int = Field(default=0)