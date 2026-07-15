from abc import ABC, abstractmethod
from mcp import ClientSession
from mcp.client.sse import sse_client
from agent.core.config import settings
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

class MCPClientServiceBase(ABC):
    """
    Abstract base class defining the service interface for interacting with MCP server tools.
    """

    @abstractmethod
    async def list_tools(self) -> list[dict]:
        """
        Retrieves the list of negotiated tools and their parameters from the MCP server.
        """
        pass

    @abstractmethod
    async def get_ecommerce_user(self, req: GetECommerceUserRequest) -> GetECommerceUserResponse:
        """
        Queries customer profile and status by email.
        """
        pass

    @abstractmethod
    async def get_ecommerce_orders(self, req: GetECommerceOrdersRequest) -> GetECommerceOrdersResponse:
        """
        Queries all orders associated with a customer email.
        """
        pass

    @abstractmethod
    async def get_ecommerce_order_details(self, req: GetECommerceOrderDetailsRequest) -> GetECommerceOrderDetailsResponse:
        """
        Queries details (metadata and item lines) of a specific order.
        """
        pass

    @abstractmethod
    async def get_return_requests_by_order(self, req: GetReturnRequestsByOrderRequest) -> GetReturnRequestsByOrderResponse:
        """
        Queries return request details for a specific order.
        """
        pass

    @abstractmethod
    async def get_return_requests_by_customer(self, req: GetReturnRequestsByCustomerRequest) -> GetReturnRequestsByCustomerResponse:
        """
        Queries all return request history for a specific customer, sorted by created_at descending.
        """
        pass

    @abstractmethod
    async def create_ecommerce_return_request(self, req: CreateReturnRequestInput) -> CreateReturnRequestResponse:
        """
        Creates a new return request record in the database.
        """
        pass


class MCPClientService(MCPClientServiceBase):
    """
    Concrete implementation of MCPClientServiceBase that uses ClientSession from mcp SDK.
    """
    def __init__(self, session: ClientSession, context_stack):
        self.session = session
        self._context_stack = context_stack

    @classmethod
    async def create(cls) -> "MCPClientService":
        """
        Async factory method to connect and initialize the MCP client service using configured settings.
        """
        server_url = settings.MCP_SERVER_URL
        context_stack = sse_client(server_url)
        read_stream, write_stream = await context_stack.__aenter__()
        session = ClientSession(read_stream, write_stream)
        await session.__aenter__()
        await session.initialize()
        return cls(session=session, context_stack=context_stack)

    async def close(self):
        """
        Closes the session and the underlying SSE transport context.
        """
        if self.session:
            await self.session.__aexit__(None, None, None)
        if self._context_stack:
            await self._context_stack.__aexit__(None, None, None)

    async def list_tools(self) -> list[dict]:
        response = await self.session.list_tools()
        tools = []
        for t in response.tools:
            tools.append({
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.inputSchema
                }
            })
        return tools

    async def get_ecommerce_user(self, req: GetECommerceUserRequest) -> GetECommerceUserResponse:
        res = await self.session.call_tool("get_ecommerce_user", arguments=req.model_dump())
        text = next((c.text for c in res.content if getattr(c, "type", None) == "text"), "{}")
        return GetECommerceUserResponse.model_validate_json(text)

    async def get_ecommerce_orders(self, req: GetECommerceOrdersRequest) -> GetECommerceOrdersResponse:
        res = await self.session.call_tool("get_ecommerce_orders", arguments=req.model_dump())
        text = next((c.text for c in res.content if getattr(c, "type", None) == "text"), "{}")
        return GetECommerceOrdersResponse.model_validate_json(text)

    async def get_ecommerce_order_details(self, req: GetECommerceOrderDetailsRequest) -> GetECommerceOrderDetailsResponse:
        res = await self.session.call_tool("get_ecommerce_order_details", arguments=req.model_dump())
        text = next((c.text for c in res.content if getattr(c, "type", None) == "text"), "{}")
        return GetECommerceOrderDetailsResponse.model_validate_json(text)

    async def get_return_requests_by_order(self, req: GetReturnRequestsByOrderRequest) -> GetReturnRequestsByOrderResponse:
        res = await self.session.call_tool("get_return_requests_by_order", arguments=req.model_dump())
        text = next((c.text for c in res.content if getattr(c, "type", None) == "text"), "{}")
        return GetReturnRequestsByOrderResponse.model_validate_json(text)

    async def get_return_requests_by_customer(self, req: GetReturnRequestsByCustomerRequest) -> GetReturnRequestsByCustomerResponse:
        res = await self.session.call_tool("get_return_requests_by_customer", arguments=req.model_dump())
        text = next((c.text for c in res.content if getattr(c, "type", None) == "text"), "{}")
        return GetReturnRequestsByCustomerResponse.model_validate_json(text)

    async def create_ecommerce_return_request(self, req: CreateReturnRequestInput) -> CreateReturnRequestResponse:
        res = await self.session.call_tool("create_ecommerce_return_request", arguments=req.model_dump())
        text = next((c.text for c in res.content if getattr(c, "type", None) == "text"), "{}")
        return CreateReturnRequestResponse.model_validate_json(text)
