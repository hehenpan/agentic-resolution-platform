import pytest
import time
from core import database
from models.db_models import (
    ECommerceReturnRequest,
    ECommerceReturnPolicy,
    ReturnStatus,
    ReturnReasonCode,
    ItemCondition,
    ReturnResolutionType,
    RefundMethod,
)
from schemas.returns import (
    GetReturnRequestsByOrderRequest,
    GetReturnRequestsByCustomerRequest,
)
from tools.returns_tools import (
    get_return_requests_by_order,
    get_return_requests_by_customer,
)

pytestmark = pytest.mark.anyio


@pytest.fixture
def seed_returns_data():
    """
    Seed ECommerceReturnRequest records for testing query tools.
    """
    now = int(time.time())
    
    # We will seed 3 return requests:
    # 1. order_id=2001, customer_id=1001, created_at=now - 100
    # 2. order_id=2002, customer_id=1001, created_at=now - 50
    # 3. order_id=2003, customer_id=1002, created_at=now - 10
    
    r1 = ECommerceReturnRequest(
        id=40001,
        order_id=2001,
        customer_id=1001,
        status=ReturnStatus.REQUESTED,
        reason_code=ReturnReasonCode.CHANGE_OF_MIND,
        reason_text="Too large",
        item_condition=ItemCondition.UNOPENED,
        requested_at=now - 100,
        created_at=now - 100,
        updated_at=now - 100,
    )
    r2 = ECommerceReturnRequest(
        id=40002,
        order_id=2002,
        customer_id=1001,
        status=ReturnStatus.APPROVED,
        reason_code=ReturnReasonCode.DAMAGED,
        reason_text="Broken screen",
        item_condition=ItemCondition.OPENED,
        requested_at=now - 50,
        created_at=now - 50,
        updated_at=now - 50,
    )
    r3 = ECommerceReturnRequest(
        id=40003,
        order_id=2003,
        customer_id=1002,
        status=ReturnStatus.RECEIVED,
        reason_code=ReturnReasonCode.WRONG_ITEM,
        reason_text="Sent red instead of blue",
        item_condition=ItemCondition.USED,
        requested_at=now - 10,
        created_at=now - 10,
        updated_at=now - 10,
    )

    with database.get_session() as session:
        session.add(r1)
        session.add(r2)
        session.add(r3)
        session.commit()


async def test_get_return_requests_by_order_success(seed_returns_data) -> None:
    req = GetReturnRequestsByOrderRequest(order_id=2002)
    res = await get_return_requests_by_order(req)
    
    assert res.returns is not None
    assert res.returns.id == 40002
    assert res.returns.order_id == 2002
    assert res.returns.customer_id == 1001
    assert res.returns.status == ReturnStatus.APPROVED
    assert res.returns.reason_code == ReturnReasonCode.DAMAGED
    assert res.returns.reason_text == "Broken screen"
    assert res.returns.item_condition == ItemCondition.OPENED


async def test_get_return_requests_by_order_not_found(seed_returns_data) -> None:
    req = GetReturnRequestsByOrderRequest(order_id=99999)
    res = await get_return_requests_by_order(req)
    assert res.returns is None


async def test_get_return_requests_by_customer_success(seed_returns_data) -> None:
    req = GetReturnRequestsByCustomerRequest(customer_id=1001)
    res = await get_return_requests_by_customer(req)
    
    # Customer 1001 has 2 return requests:
    # r1: created_at = now - 100
    # r2: created_at = now - 50
    # Output must be sorted by created_at descending (latest first -> r2, then r1)
    assert len(res.returns) == 2
    
    first_record = res.returns[0]
    second_record = res.returns[1]
    
    assert first_record.id == 40002
    assert first_record.order_id == 2002
    assert first_record.created_at > second_record.created_at
    
    assert second_record.id == 40001
    assert second_record.order_id == 2001


async def test_get_return_requests_by_customer_not_found(seed_returns_data) -> None:
    req = GetReturnRequestsByCustomerRequest(customer_id=99999)
    res = await get_return_requests_by_customer(req)
    assert len(res.returns) == 0


def test_create_return_policy_success() -> None:
    """
    Verifies that ECommerceReturnPolicy can be inserted and queried successfully.
    """
    policy = ECommerceReturnPolicy(
        policy_name="General 30-Day Policy",
        order_type="general",
        return_window_days=30,
        allow_change_of_mind=True,
        allow_damaged_return=True,
        allow_wrong_item_return=True,
        requires_unopened=False,
        manual_review_if_opened=True,
        refund_method=RefundMethod.ORIGINAL_PAYMENT,
        active=True,
        policy_text="Allow refunds within 30 days.",
    )

    with database.get_session() as session:
        session.add(policy)
        session.commit()
        session.refresh(policy)

        assert policy.id is not None
        assert policy.policy_name == "General 30-Day Policy"
        assert policy.order_type == "general"
        assert policy.return_window_days == 30
        assert policy.allow_change_of_mind is True
        assert policy.allow_damaged_return is True
        assert policy.allow_wrong_item_return is True
        assert policy.requires_unopened is False
        assert policy.manual_review_if_opened is True
        assert policy.refund_method == RefundMethod.ORIGINAL_PAYMENT
        assert policy.active is True
        assert policy.policy_text == "Allow refunds within 30 days."
        assert policy.created_at > 0
        assert policy.updated_at > 0


def test_create_return_request_success() -> None:
    """
    Verifies that ECommerceReturnRequest can be inserted and queried successfully with timestamp defaults.
    """
    now = int(time.time())
    request = ECommerceReturnRequest(
        order_id=2001,
        customer_id=1001,
        status=ReturnStatus.REQUESTED,
        reason_code=ReturnReasonCode.CHANGE_OF_MIND,
        reason_text="Changed mind",
        item_condition=ItemCondition.UNOPENED,
        created_by=1002,  # Operating customer service user_id
    )

    with database.get_session() as session:
        session.add(request)
        session.commit()
        session.refresh(request)

        assert request.id is not None
        assert request.order_id == 2001
        assert request.customer_id == 1001
        assert request.status == ReturnStatus.REQUESTED
        assert request.reason_code == ReturnReasonCode.CHANGE_OF_MIND
        assert request.reason_text == "Changed mind"
        assert request.item_condition == ItemCondition.UNOPENED
        assert request.created_by == 1002
        assert abs(request.requested_at - now) <= 5
        assert abs(request.created_at - now) <= 5
        assert abs(request.updated_at - now) <= 5
        assert request.approved_at is None
        assert request.rejected_at is None
        assert request.received_at is None
        assert request.closed_at is None
        assert request.resolution_type is None
