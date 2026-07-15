import pytest
from shared_common.schemas.mcp_server.user import GetECommerceUserRequest
from tools.user_tools import get_ecommerce_user

pytestmark = pytest.mark.anyio


async def test_get_ecommerce_user_by_email_success(seed_users_catalog) -> None:
    """
    Verifies that querying a user by email returns the correct details.
    """
    # 1. Query via tool
    req = GetECommerceUserRequest(email="john@example.com")
    res = await get_ecommerce_user(req)

    # 2. Assert response
    assert res.exists is True
    assert res.user_id == 1001
    assert res.user_name == "John Doe"
    assert res.email == "john@example.com"
    assert res.status == 1
    assert res.phone == "123-456-7890"
    assert res.create_ts == 1700000000


async def test_get_ecommerce_user_not_found() -> None:
    """
    Verifies that querying a non-existent user returns exists=False.
    """
    req = GetECommerceUserRequest(email="notfound@example.com")
    res = await get_ecommerce_user(req)
    assert res.exists is False
