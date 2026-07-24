"""Qdrant client factory helpers."""

import asyncio
from functools import cache

from qdrant_client import AsyncQdrantClient

from agent.core.config import settings


@cache
def _create_async_qdrant_client() -> AsyncQdrantClient:
    """Initialize and return AsyncQdrantClient based on settings."""
    if getattr(settings, "QDRANT_LOCATION", None) == ":memory:":
        return AsyncQdrantClient(location=":memory:")
    elif getattr(settings, "QDRANT_PATH", None):
        return AsyncQdrantClient(
            path=settings.QDRANT_PATH,
            force_disable_check_same_thread=True,
        )
    else:
        return AsyncQdrantClient(url=settings.QDRANT_URL)


def _uses_local_qdrant_storage() -> bool:
    """Return whether client construction opens local Qdrant storage."""
    return bool(
        getattr(settings, "QDRANT_LOCATION", None) == ":memory:"
        or getattr(settings, "QDRANT_PATH", None)
    )


async def get_async_qdrant_client() -> AsyncQdrantClient:
    """Return the configured async Qdrant client without blocking the event loop.

    Remote Qdrant URL mode is constructed directly. Local path and memory modes
    open local storage synchronously, so construction is delegated to a worker
    thread only for those modes.
    """
    if _uses_local_qdrant_storage():
        return await asyncio.to_thread(_create_async_qdrant_client)
    return _create_async_qdrant_client()


def clear_qdrant_client_cache() -> None:
    """Clear the cached Qdrant client, primarily for tests that override settings."""
    _create_async_qdrant_client.cache_clear()


get_async_qdrant_client.cache_clear = clear_qdrant_client_cache  # type: ignore[attr-defined]
get_qdrant_client = get_async_qdrant_client
