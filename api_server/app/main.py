from fastapi import FastAPI
from starlette_context.middleware import ContextMiddleware
from app.core.logger import setup_logging
from app.api.v1.router import api_router_v1
from app.middleware.middleware import context_plugins, VerifySessionidMiddleware

# Initialize logging setup (intercept all log outputs)
setup_logging()

app = FastAPI()

# Add session validation middleware
app.add_middleware(VerifySessionidMiddleware)

# Add context middleware with configured plugins (Registered after, so it runs first in the LIFO chain)
app.add_middleware(ContextMiddleware, plugins=context_plugins)

# Include router
app.include_router(api_router_v1, prefix="/api/v1")






