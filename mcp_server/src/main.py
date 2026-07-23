import uvicorn
from mcp.server.fastmcp import FastMCP
from core.logger import setup_logging
from core.database import init_db
from config import settings, BASE_DIR

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

# Expose the Starlette ASGI application at the module level
# This is required by Uvicorn when running with multiple workers via import string
app = mcp.sse_app()


def run() -> None:
    logger.info(f"Starting MCP Server on http://{settings.SERVER_HOST}:{settings.SERVER_PORT} with {settings.SERVER_WORKERS} workers...")
    
    # We use uvicorn.run directly instead of mcp.run to support custom ASGI settings
    # like multi-process workers in production environments.
    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        workers=settings.SERVER_WORKERS,
        log_level=settings.LOG_LEVEL.lower(),
        app_dir=str(BASE_DIR / "src")
    )


if __name__ == "__main__":
    run()
