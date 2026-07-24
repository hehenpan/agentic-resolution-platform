import json
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from shared_common.schemas.ai_agent import AgentOutput, SourcesPart, TextPart

from agent.core import llm
from agent.supervisor import supervisor_graph
from agent.supervisor.nodes import route_request
from agent.supervisor.state import (
    SelectRouteRoute,
    SupervisorDecision,
    SupervisorState,
)

pytestmark = pytest.mark.anyio

TEST_DATA_DIR = Path(__file__).resolve().parent.parent / "test_data"


def _load_record(file_name: str) -> dict[str, str]:
    return json.loads((TEST_DATA_DIR / file_name).read_text(encoding="utf-8"))


class FakeStructuredRouter:
    def __init__(self, route: str) -> None:
        self.route = route
        self.inputs: list[Any] = []

    async def ainvoke(self, input: Any, **kwargs: Any) -> dict[str, str]:
        self.inputs.append(input)
        return {"route": self.route}


class FakeSupervisorLLM:
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


async def test_route_request_uses_recorded_llm_route(monkeypatch) -> None:
    route_record = _load_record("supervisor_route_real_llm_response.json")
    fake_model = FakeSupervisorLLM(route_record["route"], "Unused draft")
    monkeypatch.setattr(llm, "get_llm_model", lambda: fake_model)
    state = SupervisorState(messages=[HumanMessage(content=route_record["question"])])

    update = await route_request(state)

    assert update["route"] == SelectRouteRoute.POLICY_QA
    assert fake_model.router.inputs


async def test_route_request_rejects_invalid_llm_route(monkeypatch) -> None:
    route_record = _load_record("supervisor_route_real_llm_response.json")
    fake_model = FakeSupervisorLLM("missing_route", "Unused draft")
    monkeypatch.setattr(llm, "get_llm_model", lambda: fake_model)
    state = SupervisorState(messages=[HumanMessage(content=route_record["question"])])

    with pytest.raises(ValueError):
        await route_request(state)


async def test_supervisor_graph_routes_to_policy_qa_with_mock_llm(
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
            "configurable": {"thread_id": "supervisor-policy-test"},
        },
    )

    assert result["route"] == SelectRouteRoute.POLICY_QA
    response = result["messages"][-1]
    assert isinstance(response, AIMessage)
    assert isinstance(result["messages"][0], HumanMessage)
    assert result["messages"][0].content == route_record["question"]
    assert policy_record["draft"] in response.content
    assert response.response_metadata["policy_chunks"]
    assert response.response_metadata["policy_chunks"][0]["file_name"]
    output = AgentOutput.model_validate(result["outputs"][0])
    assert response.id == output.output_id
    assert isinstance(output.parts[0], TextPart)
    assert output.parts[0].text == policy_record["draft"]
    assert isinstance(output.parts[1], SourcesPart)
    assert output.parts[1].sources
    assert fake_model.router.inputs
    assert fake_model.policy_inputs


async def test_supervisor_graph_does_not_multiply_outputs_across_turns(
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
    config = {
        "configurable": {"thread_id": "supervisor-output-reducer-test"},
    }

    first_result = await supervisor_graph.ainvoke(
        {"messages": [HumanMessage(content=route_record["question"])]},
        config=config,
    )
    second_result = await supervisor_graph.ainvoke(
        {"messages": [HumanMessage(content=route_record["question"])]},
        config=config,
    )

    assert len(first_result["outputs"]) == 1
    assert len(second_result["outputs"]) == 2
    output_ids = [output.output_id for output in second_result["outputs"]]
    assert len(output_ids) == len(set(output_ids))
