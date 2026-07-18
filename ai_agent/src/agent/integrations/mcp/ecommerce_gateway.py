"""Typed ecommerce operations backed by MCP tools."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import TypeVar

from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel, ValidationError
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

from agent.core.logger import logger
from agent.integrations.mcp.client import MCPClient

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)


class EcommerceToolName(str, Enum):
    """Identify ecommerce tools exposed by the MCP server."""

    GET_USER = "get_ecommerce_user"
    GET_ORDERS = "get_ecommerce_orders"
    GET_ORDER_DETAILS = "get_ecommerce_order_details"
    GET_RETURNS_BY_ORDER = "get_return_requests_by_order"
    GET_RETURNS_BY_CUSTOMER = "get_return_requests_by_customer"
    CREATE_RETURN_REQUEST = "create_ecommerce_return_request"


class EcommerceGateway(ABC):
    """Define ecommerce operations used by agent workflows."""

    @abstractmethod
    async def get_ecommerce_user(
        self,
        request: GetECommerceUserRequest,
    ) -> GetECommerceUserResponse:
        """Return an ecommerce customer by email."""

    @abstractmethod
    async def get_ecommerce_orders(
        self,
        request: GetECommerceOrdersRequest,
    ) -> GetECommerceOrdersResponse:
        """Return orders associated with a customer email."""

    @abstractmethod
    async def get_ecommerce_order_details(
        self,
        request: GetECommerceOrderDetailsRequest,
    ) -> GetECommerceOrderDetailsResponse:
        """Return metadata and items for one order."""

    @abstractmethod
    async def get_return_requests_by_order(
        self,
        request: GetReturnRequestsByOrderRequest,
    ) -> GetReturnRequestsByOrderResponse:
        """Return the return request associated with one order."""

    @abstractmethod
    async def get_return_requests_by_customer(
        self,
        request: GetReturnRequestsByCustomerRequest,
    ) -> GetReturnRequestsByCustomerResponse:
        """Return return-request history for one customer."""

    @abstractmethod
    async def create_ecommerce_return_request(
        self,
        request: CreateReturnRequestInput,
    ) -> CreateReturnRequestResponse:
        """Create an ecommerce return request."""


class MCPEcommerceGateway(EcommerceGateway):
    """Implement typed ecommerce operations through an MCP client."""

    def __init__(self, client: MCPClient) -> None:
        """Initialize the gateway with an injected MCP client."""
        self._client = client

    async def get_ecommerce_user(
        self,
        request: GetECommerceUserRequest,
    ) -> GetECommerceUserResponse:
        """Return an ecommerce customer by email."""
        return await self._call_tool(
            EcommerceToolName.GET_USER,
            request,
            GetECommerceUserResponse,
        )

    async def get_ecommerce_orders(
        self,
        request: GetECommerceOrdersRequest,
    ) -> GetECommerceOrdersResponse:
        """Return orders associated with a customer email."""
        return await self._call_tool(
            EcommerceToolName.GET_ORDERS,
            request,
            GetECommerceOrdersResponse,
        )

    async def get_ecommerce_order_details(
        self,
        request: GetECommerceOrderDetailsRequest,
    ) -> GetECommerceOrderDetailsResponse:
        """Return metadata and items for one order."""
        return await self._call_tool(
            EcommerceToolName.GET_ORDER_DETAILS,
            request,
            GetECommerceOrderDetailsResponse,
        )

    async def get_return_requests_by_order(
        self,
        request: GetReturnRequestsByOrderRequest,
    ) -> GetReturnRequestsByOrderResponse:
        """Return the return request associated with one order."""
        return await self._call_tool(
            EcommerceToolName.GET_RETURNS_BY_ORDER,
            request,
            GetReturnRequestsByOrderResponse,
        )

    async def get_return_requests_by_customer(
        self,
        request: GetReturnRequestsByCustomerRequest,
    ) -> GetReturnRequestsByCustomerResponse:
        """Return return-request history for one customer."""
        return await self._call_tool(
            EcommerceToolName.GET_RETURNS_BY_CUSTOMER,
            request,
            GetReturnRequestsByCustomerResponse,
        )

    async def create_ecommerce_return_request(
        self,
        request: CreateReturnRequestInput,
    ) -> CreateReturnRequestResponse:
        """Create an ecommerce return request."""
        return await self._call_tool(
            EcommerceToolName.CREATE_RETURN_REQUEST,
            request,
            CreateReturnRequestResponse,
        )

    async def _call_tool(
        self,
        tool_name: EcommerceToolName,
        request: BaseModel,
        response_model: type[ResponseModelT],
    ) -> ResponseModelT:
        result = await self._client.call_tool(
            tool_name.value,
            arguments=request.model_dump(mode="json"),
        )
        response_text = self._extract_response_text(tool_name, result)
        try:
            return response_model.model_validate_json(response_text)
        except ValidationError as error:
            logger.error(
                "MCP ecommerce tool returned an invalid response: tool={}, error={}",
                tool_name.value,
                error,
            )
            raise

    @staticmethod
    def _extract_response_text(
        tool_name: EcommerceToolName,
        result: CallToolResult,
    ) -> str:
        if result.isError:
            logger.error("MCP ecommerce tool reported an error: {}", tool_name.value)
            raise RuntimeError(f"MCP tool failed: {tool_name.value}")

        for content in result.content:
            if isinstance(content, TextContent):
                return content.text

        logger.error(
            "MCP ecommerce tool returned no text content: {}",
            tool_name.value,
        )
        raise ValueError(f"MCP tool returned no text content: {tool_name.value}")
