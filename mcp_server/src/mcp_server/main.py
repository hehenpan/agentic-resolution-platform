from mcp.server.fastmcp import FastMCP
from mcp_server.core.logger import setup_logging
from mcp_server.core.database import init_db

# Initialize Logging
logger = setup_logging()

# Instantiate FastMCP server
mcp = FastMCP(
    name="mcp-server"
)

# Initialize database schema/tables
logger.info("Initializing isolated database tables...")
init_db()

# Import tools package after defining mcp to register decorators
import mcp_server.tools

def run() -> None:
    logger.info("Starting MCP Server...")
    mcp.run()

if __name__ == "__main__":
    run()
