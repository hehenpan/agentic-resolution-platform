"""Configurable ecommerce gateway test double."""

from collections.abc import Callable

from pydantic import BaseModel
from shared_common.schemas.mcp_server.order import (
    GetECommerceOrderDetailsRequest,
    GetECommerceOrderDetailsResponse,
    GetECommerceOrdersRequest,
    GetECommerceOrdersResponse,
)
from shared_common.schemas.mcp_server.returns import (
    CreateReturnRequestInput,
    CreateReturnRequestResponse,
    GetReturnRequestsByCustomerRequest,
    GetReturnRequestsByCustomerResponse,
    GetReturnRequestsByOrderRequest,
    GetReturnRequestsByOrderResponse,
)
from shared_common.schemas.mcp_server.user import (
    GetECommerceUserRequest,
    GetECommerceUserResponse,
)

from agent.integrations.mcp.ecommerce_gateway import EcommerceGateway


class EcommerceGatewayMock(EcommerceGateway):
    """Return configurable responses and record ecommerce gateway calls."""

    def __init__(self) -> None:
        """Initialize default responses and call tracking."""
        self.expected_user: (
            GetECommerceUserResponse
            | Callable[[GetECommerceUserRequest], GetECommerceUserResponse]
        ) = GetECommerceUserResponse(exists=False)
        self.expected_orders: (
            GetECommerceOrdersResponse
            | Callable[[GetECommerceOrdersRequest], GetECommerceOrdersResponse]
        ) = GetECommerceOrdersResponse(orders=[])
        self.expected_order_details: (
            GetECommerceOrderDetailsResponse
            | Callable[
                [GetECommerceOrderDetailsRequest], GetECommerceOrderDetailsResponse
            ]
        ) = GetECommerceOrderDetailsResponse(exists=False)
        self.expected_return_by_order: (
            GetReturnRequestsByOrderResponse
            | Callable[
                [GetReturnRequestsByOrderRequest], GetReturnRequestsByOrderResponse
            ]
        ) = GetReturnRequestsByOrderResponse(returns=None)
        self.expected_returns_by_customer: (
            GetReturnRequestsByCustomerResponse
            | Callable[
                [GetReturnRequestsByCustomerRequest],
                GetReturnRequestsByCustomerResponse,
            ]
        ) = GetReturnRequestsByCustomerResponse(returns=[])
        self.expected_create_return: (
            CreateReturnRequestResponse
            | Callable[[CreateReturnRequestInput], CreateReturnRequestResponse]
        ) = CreateReturnRequestResponse(
            success=False,
            error_message="Mock not configured",
        )
        self.calls: dict[str, list[BaseModel]] = {
            "get_ecommerce_user": [],
            "get_ecommerce_orders": [],
            "get_ecommerce_order_details": [],
            "get_return_requests_by_order": [],
            "get_return_requests_by_customer": [],
            "create_ecommerce_return_request": [],
        }

    async def get_ecommerce_user(
        self,
        request: GetECommerceUserRequest,
    ) -> GetECommerceUserResponse:
        self.calls["get_ecommerce_user"].append(request)
        if callable(self.expected_user):
            return self.expected_user(request)
        return self.expected_user

    async def get_ecommerce_orders(
        self,
        request: GetECommerceOrdersRequest,
    ) -> GetECommerceOrdersResponse:
        self.calls["get_ecommerce_orders"].append(request)
        if callable(self.expected_orders):
            return self.expected_orders(request)
        return self.expected_orders

    async def get_ecommerce_order_details(
        self,
        request: GetECommerceOrderDetailsRequest,
    ) -> GetECommerceOrderDetailsResponse:
        self.calls["get_ecommerce_order_details"].append(request)
        if callable(self.expected_order_details):
            return self.expected_order_details(request)
        return self.expected_order_details

    async def get_return_requests_by_order(
        self,
        request: GetReturnRequestsByOrderRequest,
    ) -> GetReturnRequestsByOrderResponse:
        self.calls["get_return_requests_by_order"].append(request)
        if callable(self.expected_return_by_order):
            return self.expected_return_by_order(request)
        return self.expected_return_by_order

    async def get_return_requests_by_customer(
        self,
        request: GetReturnRequestsByCustomerRequest,
    ) -> GetReturnRequestsByCustomerResponse:
        self.calls["get_return_requests_by_customer"].append(request)
        if callable(self.expected_returns_by_customer):
            return self.expected_returns_by_customer(request)
        return self.expected_returns_by_customer

    async def create_ecommerce_return_request(
        self,
        request: CreateReturnRequestInput,
    ) -> CreateReturnRequestResponse:
        self.calls["create_ecommerce_return_request"].append(request)
        if callable(self.expected_create_return):
            return self.expected_create_return(request)
        return self.expected_create_return
