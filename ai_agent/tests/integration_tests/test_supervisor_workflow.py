"""Integration tests for the supervisor graph workflow."""

import json
from pathlib import Path
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import StreamMode
from shared_common.schemas.ai_agent import AgentOutput, SourcesPart, TextPart

from agent.core import llm
from agent.core.logger import logger
from agent.supervisor import supervisor_graph
from agent.supervisor.policy_qa.nodes import PolicyQANodes
from agent.supervisor.state import (
    SelectRouteRoute,
    SupervisorDecision,
    SupervisorNodeNames,
    SupervisorState,
)

pytestmark = pytest.mark.anyio

TEST_DATA_DIR = Path(__file__).resolve().parent.parent / "test_data"


def _load_record(file_name: str) -> dict[str, str]:
    return json.loads((TEST_DATA_DIR / file_name).read_text(encoding="utf-8"))


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

    graph_input = SupervisorState(
        messages=[HumanMessage(content=route_record["question"])]
    )
    graph_config: RunnableConfig = {
        "configurable": {
            "thread_id": "integration-supervisor-policy-workflow",
        },
    }
    result = await supervisor_graph.ainvoke(
        graph_input,
        config=graph_config,
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

    output = AgentOutput.model_validate(result["outputs"][-1])
    assert response.id == output.output_id
    assert isinstance(output.parts[0], TextPart)
    assert output.parts[0].text == policy_record["draft"]
    assert isinstance(output.parts[1], SourcesPart)
    assert output.parts[1].sources[0].title == chunks[0]["file_name"]

    assert fake_model.router.inputs
    assert fake_model.policy_inputs


async def test_supervisor_graph_streams_policy_workflow_updates(
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
    logger.info("Ready to call supervisor graph with astream")

    graph_input = SupervisorState(
        messages=[HumanMessage(content=route_record["question"])]
    )
    graph_config: RunnableConfig = {
        "configurable": {
            "thread_id": "integration-supervisor-policy-stream",
        },
    }
    stream_modes: tuple[StreamMode, ...] = (
        "values",
        "updates",
        "checkpoints",
        "tasks",
        "debug",
        "messages",
        "custom",
    )
    events = [
        event
        async for event in supervisor_graph.astream(
            graph_input,
            config=graph_config,
            stream_mode=stream_modes,
            subgraphs=True,
            version="v2",
        )
    ]
    for event in events:
        logger.info(f"event: {event}")

    assert any(event["type"] == "checkpoints" for event in events)

    updates = [event["data"] for event in events if event["type"] == "updates"]
    assert any(SupervisorNodeNames.ROUTE_REQUEST in update for update in updates)
    assert any(PolicyQANodes.RETRIEVE_POLICY in update for update in updates)
    assert any(PolicyQANodes.GENERATE_DRAFT in update for update in updates)

    build_response_update = next(
        update[PolicyQANodes.BUILD_RESPONSE]
        for update in updates
        if PolicyQANodes.BUILD_RESPONSE in update
    )
    response = AIMessage.model_validate(build_response_update["messages"][-1])
    output = AgentOutput.model_validate(build_response_update["outputs"][-1])
    assert policy_record["draft"] in response.content
    assert response.response_metadata["policy_chunks"]
    assert response.id == output.output_id
    assert isinstance(output.parts[0], TextPart)
    assert output.parts[0].text == policy_record["draft"]
    assert isinstance(output.parts[1], SourcesPart)
    assert output.parts[1].sources
    assert fake_model.router.inputs
    assert fake_model.policy_inputs
