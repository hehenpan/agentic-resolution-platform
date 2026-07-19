"""Dependency injection provider for the EcommerceGateway."""

from agent.core.config import settings
from agent.integrations.mcp.client import SSEMCPClient
from agent.integrations.mcp.ecommerce_gateway import EcommerceGateway, MCPEcommerceGateway

_gateway: EcommerceGateway | None = None


async def get_ecommerce_gateway() -> EcommerceGateway:
    """Return the active EcommerceGateway implementation."""
    global _gateway
    if _gateway is None:
        client = await SSEMCPClient.connect(settings.MCP_SERVER_URL)
        _gateway = MCPEcommerceGateway(client)
    return _gateway


def set_ecommerce_gateway(gateway: EcommerceGateway) -> None:
    """Inject a mock or custom EcommerceGateway implementation for testing."""
    global _gateway
    _gateway = gateway
