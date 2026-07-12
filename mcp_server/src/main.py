from mcp.server.fastmcp import FastMCP
from core.logger import setup_logging
from core.database import init_db

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
import tools

def run() -> None:
    logger.info("Starting MCP Server...")
    mcp.run()

if __name__ == "__main__":
    run()
