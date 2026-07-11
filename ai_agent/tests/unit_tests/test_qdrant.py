from agent.core.qdrant import get_qdrant_client
from qdrant_client.models import Distance, VectorParams, PointStruct

def test_qdrant_client_memory_mode():
    client = get_qdrant_client()
    
    # 1. Check client exists
    assert client is not None
    
    # 2. Check collection creation
    collection_name = "test_collection"
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=4, distance=Distance.COSINE),
    )
    
    # 3. Insert a mock point
    client.upsert(
        collection_name=collection_name,
        points=[
            PointStruct(id=1, vector=[1.0, 0.0, 0.0, 0.0], payload={"meta": "info"})
        ]
    )
    
    # 4. Search
    results = client.query_points(
        collection_name=collection_name,
        query=[1.0, 0.0, 0.0, 0.0],
        limit=1
    )
    
    assert len(results.points) == 1
    assert results.points[0].id == 1
    assert results.points[0].payload == {"meta": "info"}
