"""Integration tests for the supervisor graph workflow."""

import json
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agent.core import llm
from agent.supervisor import supervisor_graph
from agent.supervisor.state import (
    SelectRouteRoute,
    SupervisorDecision,
)

pytestmark = pytest.mark.anyio

TEST_DATA_DIR = Path(__file__).resolve().parent.parent / "test_data"


def _load_record(file_name: str) -> dict[str, str]:
    return json.loads(
        (TEST_DATA_DIR / file_name).read_text(encoding="utf-8")
    )


class FakeStructuredRouter:
    """Return the route captured from the real supervisor LLM."""

    def __init__(self, route: str) -> None:
        self.route = route
        self.inputs: list[Any] = []

    async def ainvoke(self, input: Any, **kwargs: Any) -> dict[str, str]:
        self.inputs.append(input)
        return {"route": self.route}


class FakeSupervisorLLM:
    """Replay recorded routing and policy-generation responses."""

    def __init__(self, route: str, draft: str) -> None:
        self.router = FakeStructuredRouter(route)
        self.draft = draft
        self.policy_inputs: list[Any] = []

    def with_structured_output(
        self,
        schema: type[SupervisorDecision],
        **kwargs: Any,
    ) -> FakeStructuredRouter:
        assert schema is SupervisorDecision
        return self.router

    async def ainvoke(self, input: Any, **kwargs: Any) -> AIMessage:
        self.policy_inputs.append(input)
        return AIMessage(content=self.draft)


async def test_supervisor_graph_runs_policy_workflow_from_public_entry(
    monkeypatch,
    prebuilt_qdrant_env,
) -> None:
    route_record = _load_record("supervisor_route_real_llm_response.json")
    policy_record = _load_record("policy_qa_real_llm_response.json")
    fake_model = FakeSupervisorLLM(
        route=route_record["route"],
        draft=policy_record["draft"],
    )
    monkeypatch.setattr(llm, "get_llm_model", lambda: fake_model)

    result = await supervisor_graph.ainvoke(
        {"messages": [HumanMessage(content=route_record["question"])]},
        config={
            "configurable": {
                "thread_id": "integration-supervisor-policy-workflow",
            }
        },
    )

    assert result["route"] == SelectRouteRoute.POLICY_QA
    assert isinstance(result["messages"][0], HumanMessage)

    response = result["messages"][-1]
    assert isinstance(response, AIMessage)
    assert policy_record["draft"] in response.content

    chunks = response.response_metadata["policy_chunks"]
    assert chunks
    assert chunks[0]["file_name"] == (
        "general_ecommerce_delivery_rates_times_options.md"
    )
    assert chunks[0]["text"] in response.content
    assert chunks[0]["payload"]["file_name"] == chunks[0]["file_name"]
    assert fake_model.router.inputs
    assert fake_model.policy_inputs
