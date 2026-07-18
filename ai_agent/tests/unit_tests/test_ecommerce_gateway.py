"""Tests for the typed ecommerce MCP gateway."""

from typing import Any

import pytest
from mcp.types import CallToolResult, TextContent
from shared_common.schemas.mcp_server.enums import ItemCondition, ReturnReasonCode
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

from agent.integrations.mcp.client import MCPClient
from agent.integrations.mcp.ecommerce_gateway import MCPEcommerceGateway

pytestmark = pytest.mark.anyio


class FakeMCPClient(MCPClient):
    def __init__(self, result: CallToolResult) -> None:
        self.result = result
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    async def list_tools(self) -> list[dict[str, Any]]:
        return []

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> CallToolResult:
        self.calls.append((name, arguments))
        return self.result

    async def close(self) -> None:
        return None


@pytest.mark.parametrize(
    ("method_name", "tool_name", "request_model", "expected_response"),
    [
        (
            "get_ecommerce_user",
            "get_ecommerce_user",
            GetECommerceUserRequest(email="customer@example.com"),
            GetECommerceUserResponse(exists=False),
        ),
        (
            "get_ecommerce_orders",
            "get_ecommerce_orders",
            GetECommerceOrdersRequest(email="customer@example.com"),
            GetECommerceOrdersResponse(orders=[]),
        ),
        (
            "get_ecommerce_order_details",
            "get_ecommerce_order_details",
            GetECommerceOrderDetailsRequest(order_id=101),
            GetECommerceOrderDetailsResponse(exists=False),
        ),
        (
            "get_return_requests_by_order",
            "get_return_requests_by_order",
            GetReturnRequestsByOrderRequest(order_id=101),
            GetReturnRequestsByOrderResponse(returns=None),
        ),
        (
            "get_return_requests_by_customer",
            "get_return_requests_by_customer",
            GetReturnRequestsByCustomerRequest(customer_id=7),
            GetReturnRequestsByCustomerResponse(returns=[]),
        ),
        (
            "create_ecommerce_return_request",
            "create_ecommerce_return_request",
            CreateReturnRequestInput(
                order_id=101,
                customer_id=7,
                reason_code=ReturnReasonCode.CHANGE_OF_MIND,
                item_condition=ItemCondition.UNOPENED,
            ),
            CreateReturnRequestResponse(
                success=False,
                error_message="Not configured",
            ),
        ),
    ],
)
async def test_gateway_maps_typed_operations_to_mcp_tools(
    method_name: str,
    tool_name: str,
    request_model: Any,
    expected_response: Any,
) -> None:
    result = CallToolResult(
        content=[
            TextContent(
                type="text",
                text=expected_response.model_dump_json(),
            )
        ]
    )
    client = FakeMCPClient(result)
    gateway = MCPEcommerceGateway(client)

    operation = getattr(gateway, method_name)
    response = await operation(request_model)

    assert response == expected_response
    assert client.calls == [
        (
            tool_name,
            request_model.model_dump(mode="json"),
        )
    ]


async def test_gateway_rejects_response_without_text_content() -> None:
    client = FakeMCPClient(CallToolResult(content=[]))
    gateway = MCPEcommerceGateway(client)

    with pytest.raises(ValueError, match="returned no text content"):
        await gateway.get_ecommerce_user(
            GetECommerceUserRequest(email="customer@example.com")
        )
