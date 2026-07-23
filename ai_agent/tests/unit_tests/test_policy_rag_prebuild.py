import pytest
from agent.core.qdrant import get_async_qdrant_client
from agent.core.embedding import get_embedding_model
from agent.core.constants import QDRANT_COLLECTION_RAG

pytestmark = pytest.mark.anyio

@pytest.mark.parametrize(
    "query_text",
    [
        # Query 1: The original policy text paragraph
        (
            "Each product page shows an estimated dispatch timeframe near the listed price. "
            "From when your items ship, products typically arrive within 1-2 working days for North Island deliveries "
            "and 2-3 working days for South Island deliveries. Rural deliveries may take an extra working day. "
            "Bulk & hazard deliveries may take an extra 2-7 working days and tracking links for these deliveries "
            "can take a few days to generate."
        ),
        # Query 2: The direct customer question
        "how many working days for products typically arrive for North Island?"
    ]
)
async def test_policy_retrieval_offline(prebuilt_qdrant_env, query_text: str) -> None:
    """
    Unit test using the prebuilt local database and query embedding cache.
    Verifies that the RAG retrieval matches the correct shipping policy chunk offline
    for both query representations.
    """
    # 1. Retrieve the pre-configured qdrant client pointing to prebuilt path
    client = await get_async_qdrant_client()
    
    # 2. Verify the collection exists
    collection_name = QDRANT_COLLECTION_RAG
    assert await client.collection_exists(collection_name)
    
    # 3. Retrieve the embedding model (which is mocked session-wide to load query cache)
    embedding_model = get_embedding_model()
    
    # This should hit the mock cache instantly without calling the online Gemini API
    query_vector = await embedding_model.aembed_query(query_text)
    
    # 4. Search in local Qdrant collection
    results = await client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=1
    )
    
    # 5. Assert the matched document details are correct
    assert len(results.points) > 0
    payload = results.points[0].payload
    
    assert "file_name" in payload
    assert "text" in payload
    
    # Verify we retrieved the correct shipping chunk containing North Island delivery info
    assert "North Island" in payload["text"]
    assert "general_ecommerce_delivery_rates_times_options.md" == payload["file_name"]
