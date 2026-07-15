import json
from pathlib import Path
from agent.mcp.mcp_client import MCPClientServiceBase
from shared_common.schemas.mcp_server.user import GetECommerceUserRequest, GetECommerceUserResponse
from shared_common.schemas.mcp_server.order import (
    GetECommerceOrdersRequest,
    GetECommerceOrdersResponse,
    GetECommerceOrderDetailsRequest,
    GetECommerceOrderDetailsResponse,
)
from shared_common.schemas.mcp_server.returns import (
    GetReturnRequestsByOrderRequest,
    GetReturnRequestsByOrderResponse,
    GetReturnRequestsByCustomerRequest,
    GetReturnRequestsByCustomerResponse,
    CreateReturnRequestInput,
    CreateReturnRequestResponse,
)

class MCPClientServiceMock(MCPClientServiceBase):
    """
    Mock implementation of MCPClientServiceBase for unit testing.
    Allows test cases to configure expected responses or inspect call args.
    """
    def __init__(self):
        # Resolve path to tools_metadata.json
        tools_path = Path(__file__).resolve().parent.parent.parent / "shared_common" / "schemas" / "mcp_server" / "tools_metadata.json"
        if tools_path.exists():
            with open(tools_path, "r", encoding="utf-8") as f:
                self.expected_tools = json.load(f)
        else:
            self.expected_tools = []
        self.expected_user: GetECommerceUserResponse = GetECommerceUserResponse(exists=False)
        self.expected_orders: GetECommerceOrdersResponse = GetECommerceOrdersResponse(orders=[])
        self.expected_order_details: GetECommerceOrderDetailsResponse = GetECommerceOrderDetailsResponse(exists=False)
        self.expected_return_by_order: GetReturnRequestsByOrderResponse = GetReturnRequestsByOrderResponse(returns=None)
        self.expected_returns_by_customer: GetReturnRequestsByCustomerResponse = GetReturnRequestsByCustomerResponse(returns=[])
        self.expected_create_return: CreateReturnRequestResponse = CreateReturnRequestResponse(success=False, error_message="Mock not configured")

        # Call tracking
        self.calls = {
            "list_tools": 0,
            "get_ecommerce_user": [],
            "get_ecommerce_orders": [],
            "get_ecommerce_order_details": [],
            "get_return_requests_by_order": [],
            "get_return_requests_by_customer": [],
            "create_ecommerce_return_request": [],
        }

    async def list_tools(self) -> list[dict]:
        self.calls["list_tools"] += 1
        return self.expected_tools

    async def get_ecommerce_user(self, req: GetECommerceUserRequest) -> GetECommerceUserResponse:
        self.calls["get_ecommerce_user"].append(req)
        if callable(self.expected_user):
            return self.expected_user(req)
        return self.expected_user

    async def get_ecommerce_orders(self, req: GetECommerceOrdersRequest) -> GetECommerceOrdersResponse:
        self.calls["get_ecommerce_orders"].append(req)
        if callable(self.expected_orders):
            return self.expected_orders(req)
        return self.expected_orders

    async def get_ecommerce_order_details(self, req: GetECommerceOrderDetailsRequest) -> GetECommerceOrderDetailsResponse:
        self.calls["get_ecommerce_order_details"].append(req)
        if callable(self.expected_order_details):
            return self.expected_order_details(req)
        return self.expected_order_details

    async def get_return_requests_by_order(self, req: GetReturnRequestsByOrderRequest) -> GetReturnRequestsByOrderResponse:
        self.calls["get_return_requests_by_order"].append(req)
        if callable(self.expected_return_by_order):
            return self.expected_return_by_order(req)
        return self.expected_return_by_order

    async def get_return_requests_by_customer(self, req: GetReturnRequestsByCustomerRequest) -> GetReturnRequestsByCustomerResponse:
        self.calls["get_return_requests_by_customer"].append(req)
        if callable(self.expected_returns_by_customer):
            return self.expected_returns_by_customer(req)
        return self.expected_returns_by_customer

    async def create_ecommerce_return_request(self, req: CreateReturnRequestInput) -> CreateReturnRequestResponse:
        self.calls["create_ecommerce_return_request"].append(req)
        if callable(self.expected_create_return):
            return self.expected_create_return(req)
        return self.expected_create_return
