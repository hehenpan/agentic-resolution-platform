"""MCP transport and domain gateway integrations."""

from agent.integrations.mcp.client import MCPClient, SSEMCPClient
from agent.integrations.mcp.ecommerce_gateway import (
    EcommerceGateway,
    MCPEcommerceGateway,
)

__all__ = [
    "EcommerceGateway",
    "MCPClient",
    "MCPEcommerceGateway",
    "SSEMCPClient",
]
