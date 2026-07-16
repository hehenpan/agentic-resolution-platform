import json
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agent.core import embedding, llm, vectordb
from agent.supervisor.policy_qa import policy_qa_graph

pytestmark = pytest.mark.anyio

TEST_DATA_DIR = Path(__file__).resolve().parent.parent / "test_data"


def _load_recorded_policy_response() -> dict[str, str]:
    record_path = TEST_DATA_DIR / "policy_qa_real_llm_response.json"
    return json.loads(record_path.read_text(encoding="utf-8"))


class FakePolicyLLM:
    def __init__(self, draft: str) -> None:
        self.draft = draft
        self.inputs: list[Any] = []

    async def ainvoke(self, input: Any, **kwargs: Any) -> AIMessage:
        self.inputs.append(input)
        return AIMessage(content=self.draft)


class FailingPolicyLLM:
    async def ainvoke(self, input: Any, **kwargs: Any) -> AIMessage:
        raise RuntimeError("Mock policy generation failure")


class FakeEmbeddingModel:
    async def aembed_query(self, text: str) -> list[float]:
        return [0.0]


class EmptyVectorDB:
    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int,
    ) -> list[Any]:
        return []


async def test_policy_qa_graph_returns_draft_sources_and_metadata(
    monkeypatch,
    prebuilt_qdrant_env,
) -> None:
    record = _load_recorded_policy_response()
    fake_model = FakePolicyLLM(record["draft"])
    monkeypatch.setattr(llm, "get_llm_model", lambda: fake_model)

    result = await policy_qa_graph.ainvoke(
        {"messages": [HumanMessage(content=record["question"])]}
    )

    response = result["messages"][-1]
    assert isinstance(response, AIMessage)
    assert isinstance(result["messages"][0], HumanMessage)
    assert result["messages"][0].content == record["question"]
    assert record["draft"] in response.content
    assert fake_model.inputs
    assert "North Island" in fake_model.inputs[0].to_string()

    chunks = response.response_metadata["policy_chunks"]
    assert chunks
    assert all(chunk["file_name"] for chunk in chunks)
    assert chunks[0]["file_name"] == (
        "general_ecommerce_delivery_rates_times_options.md"
    )
    assert chunks[0]["text"] in response.content
    assert chunks[0]["payload"]["file_name"] == chunks[0]["file_name"]


async def test_policy_qa_graph_keeps_sources_when_llm_fails(
    monkeypatch,
    prebuilt_qdrant_env,
) -> None:
    record = _load_recorded_policy_response()
    monkeypatch.setattr(llm, "get_llm_model", FailingPolicyLLM)

    result = await policy_qa_graph.ainvoke(
        {"messages": [HumanMessage(content=record["question"])]}
    )

    response = result["messages"][-1]
    chunks = response.response_metadata["policy_chunks"]
    assert chunks
    assert "relevant policy excerpts" in response.content
    assert chunks[0]["text"] in response.content


async def test_policy_qa_graph_skips_llm_when_no_policy_is_found(
    monkeypatch,
) -> None:
    record = _load_recorded_policy_response()
    monkeypatch.setattr(
        embedding,
        "get_embedding_model",
        FakeEmbeddingModel,
    )
    monkeypatch.setattr(vectordb, "get_vector_db", EmptyVectorDB)

    def fail_if_llm_is_requested() -> None:
        raise AssertionError("LLM should not be called without policy chunks")

    monkeypatch.setattr(llm, "get_llm_model", fail_if_llm_is_requested)

    result = await policy_qa_graph.ainvoke(
        {"messages": [HumanMessage(content=record["question"])]}
    )

    response = result["messages"][-1]
    assert response.response_metadata["policy_chunks"] == []
    assert "could not find a relevant policy" in response.content
