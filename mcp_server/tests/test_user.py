import pytest
from schemas.user import GetECommerceUserRequest
from tools.user_tools import get_ecommerce_user

pytestmark = pytest.mark.anyio


async def test_get_ecommerce_user_by_email_success(seed_ecommerce_user) -> None:
    """
    Verifies that querying a user by email returns the correct details.
    """
    # 1. Query via tool
    req = GetECommerceUserRequest(email=seed_ecommerce_user["email"])
    res = await get_ecommerce_user(req)

    # 2. Assert response
    assert res.exists is True
    assert res.user_id == seed_ecommerce_user["user_id"]
    assert res.user_name == seed_ecommerce_user["user_name"]
    assert res.email == seed_ecommerce_user["email"]
    assert res.status == seed_ecommerce_user["status"]
    assert res.create_ts == seed_ecommerce_user["create_ts"]


async def test_get_ecommerce_user_not_found() -> None:
    """
    Verifies that querying a non-existent user returns exists=False.
    """
    req = GetECommerceUserRequest(email="notfound@example.com")
    res = await get_ecommerce_user(req)
    assert res.exists is False
