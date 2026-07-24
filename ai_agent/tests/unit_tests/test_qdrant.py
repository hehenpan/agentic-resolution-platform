import pytest
from qdrant_client.models import Distance, PointStruct, VectorParams

from agent.core import qdrant
from agent.core.qdrant import get_async_qdrant_client

pytestmark = pytest.mark.anyio


async def test_qdrant_client_memory_mode():
    client = await get_async_qdrant_client()
    
    # 1. Check client exists
    assert client is not None
    
    # 2. Check collection creation
    collection_name = "test_collection"
    await client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=4, distance=Distance.COSINE),
    )
    
    # 3. Insert a mock point
    await client.upsert(
        collection_name=collection_name,
        points=[
            PointStruct(id=1, vector=[1.0, 0.0, 0.0, 0.0], payload={"meta": "info"})
        ]
    )
    
    # 4. Search
    results = await client.query_points(
        collection_name=collection_name,
        query=[1.0, 0.0, 0.0, 0.0],
        limit=1
    )
    
    assert len(results.points) == 1
    assert results.points[0].id == 1
    assert results.points[0].payload == {"meta": "info"}


async def test_qdrant_client_remote_mode_does_not_use_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = object()
    monkeypatch.setattr(qdrant.settings, "QDRANT_LOCATION", None)
    monkeypatch.setattr(qdrant.settings, "QDRANT_PATH", None)
    monkeypatch.setattr(qdrant.settings, "QDRANT_URL", "http://qdrant:6333")
    monkeypatch.setattr(qdrant, "_create_async_qdrant_client", lambda: sentinel)

    async def fail_to_thread(*args, **kwargs):
        raise AssertionError("remote Qdrant client construction should not use a thread")

    monkeypatch.setattr(qdrant.asyncio, "to_thread", fail_to_thread)

    assert await qdrant.get_async_qdrant_client() is sentinel


async def test_qdrant_client_local_mode_uses_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = object()
    monkeypatch.setattr(qdrant.settings, "QDRANT_LOCATION", None)
    monkeypatch.setattr(qdrant.settings, "QDRANT_PATH", "qdrant_storage")

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(qdrant, "_create_async_qdrant_client", lambda: sentinel)
    monkeypatch.setattr(qdrant.asyncio, "to_thread", fake_to_thread)

    assert await qdrant.get_async_qdrant_client() is sentinel
