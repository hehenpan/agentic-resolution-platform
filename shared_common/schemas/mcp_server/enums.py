from enum import Enum

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
