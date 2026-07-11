from functools import cache
from qdrant_client import QdrantClient
from agent.core.config import settings

@cache
def get_qdrant_client() -> QdrantClient:
    """
    Initialize and return QdrantClient based on settings.
    Handles memory, path, or url parameters with singleton caching.
    """
    if getattr(settings, "QDRANT_LOCATION", None) == ":memory:":
        return QdrantClient(location=":memory:")
    elif getattr(settings, "QDRANT_PATH", None):
        return QdrantClient(path=settings.QDRANT_PATH)
    else:
        return QdrantClient(url=settings.QDRANT_URL)
