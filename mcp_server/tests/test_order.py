import pytest
from schemas.order import GetECommerceOrdersRequest
from tools.order_tools import get_ecommerce_orders

pytestmark = pytest.mark.anyio


async def test_get_ecommerce_orders_by_email_success(seed_orders_catalog) -> None:
    """
    Verifies that querying orders by email returns all order records sorted by created_ts descending.
    """
    # 1. Query orders for john@example.com (which has 2 orders)
    req = GetECommerceOrdersRequest(email="john@example.com")
    res = await get_ecommerce_orders(req)

    # 2. Assert responses
    assert len(res.orders) == 2
    
    # Assert they are sorted in descending order of created_ts
    # Order 2005 has created_ts = 1783049000 (later order should be first)
    # Order 2001 has created_ts = 1783048000 (earlier order should be second)
    first_order = res.orders[0]
    second_order = res.orders[1]

    assert first_order.order_id == 2005
    assert first_order.user_id == 1001
    assert first_order.email == "john@example.com"
    assert first_order.status == 0  # OrderStatus.PENDING
    assert first_order.total_amount == 5.99
    assert first_order.created_ts == 1783049000

    assert second_order.order_id == 2001
    assert second_order.user_id == 1001
    assert second_order.email == "john@example.com"
    assert second_order.status == 3  # OrderStatus.COMPLETED
    assert second_order.total_amount == 26.45
    assert second_order.created_ts == 1783048000


async def test_get_ecommerce_orders_not_found(seed_orders_catalog) -> None:
    """
    Verifies that querying orders for a user with no orders returns an empty list.
    """
    req = GetECommerceOrdersRequest(email="notfound@example.com")
    res = await get_ecommerce_orders(req)
    assert len(res.orders) == 0
