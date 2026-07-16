import pytest

from agent.core.constants import QDRANT_COLLECTION_RAG
from agent.core.embedding import get_embedding_model
from agent.core.vectordb import get_vector_db

pytestmark = pytest.mark.anyio

POLICY_QUESTION = (
    "how many working days for products typically arrive for North Island?"
)


async def test_vector_db_search_uses_prebuilt_policy_data(
    prebuilt_qdrant_env,
) -> None:
    query_vector = await get_embedding_model().aembed_query(POLICY_QUESTION)

    results = get_vector_db().search(
        collection_name=QDRANT_COLLECTION_RAG,
        query_vector=query_vector,
        limit=1,
    )

    assert len(results) == 1
    assert results[0].score > 0
    assert results[0].payload["file_name"] == (
        "general_ecommerce_delivery_rates_times_options.md"
    )
    assert "North Island" in results[0].payload["text"]
