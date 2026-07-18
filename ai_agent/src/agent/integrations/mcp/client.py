"""Generic MCP client transport abstractions and SSE implementation."""

from abc import ABC, abstractmethod
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.types import CallToolResult

from agent.core.logger import logger


class MCPClient(ABC):
    """Define transport operations required by MCP-backed gateways."""

    @abstractmethod
    async def list_tools(self) -> list[dict[str, Any]]:
        """Return tools exposed by the connected MCP server."""
        ...

    @abstractmethod
    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> CallToolResult:
        """Call one MCP tool and return its raw result."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Close the MCP transport and session."""
        ...


class SSEMCPClient(MCPClient):
    """Implement MCP transport over an SSE client session."""

    def __init__(self, session: ClientSession, exit_stack: AsyncExitStack) -> None:
        """Initialize the client with an active session and resource stack."""
        self._session = session
        self._exit_stack = exit_stack

    @classmethod
    async def connect(cls, server_url: str) -> "SSEMCPClient":
        """Connect to an MCP SSE endpoint and initialize its session."""
        exit_stack = AsyncExitStack()
        try:
            read_stream, write_stream = await exit_stack.enter_async_context(
                sse_client(server_url)
            )
            session = await exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await session.initialize()
        except Exception as error:
            logger.error(
                "Failed to initialize MCP SSE client: {}",
                type(error).__name__,
            )
            await exit_stack.aclose()
            raise
        return cls(session=session, exit_stack=exit_stack)

    async def list_tools(self) -> list[dict[str, Any]]:
        """Return MCP tools in the function-tool representation."""
        response = await self._session.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
            for tool in response.tools
        ]

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> CallToolResult:
        """Call one tool through the active MCP session."""
        return await self._session.call_tool(name, arguments=arguments)

    async def close(self) -> None:
        """Close the MCP session and SSE transport resources."""
        try:
            await self._exit_stack.aclose()
        except Exception as error:
            logger.error(
                "Failed to close MCP SSE client: {}",
                type(error).__name__,
            )
            raise
