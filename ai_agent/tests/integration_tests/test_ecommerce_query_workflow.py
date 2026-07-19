import re
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command
from mock_ecommerce_gateway import EcommerceGatewayMock
from shared_common.schemas.ai_agent import AgentOutput
from shared_common.schemas.ai_agent.outputs import (
    ECommerceOrderDetailsOutput,
    ECommerceOrdersOutput,
)
from shared_common.schemas.ai_agent.schema_ids import (
    AgentOutputSchemaId,
    HumanInputSchemaId,
)
from shared_common.schemas.mcp_server.enums import OrderStatus
from shared_common.schemas.mcp_server.order import (
    ECommerceOrderItemRecord,
    ECommerceOrderMeta,
    ECommerceOrderRecord,
    GetECommerceOrderDetailsResponse,
    GetECommerceOrdersResponse,
)
from shared_common.schemas.mcp_server.user import GetECommerceUserResponse

from agent.core import llm
from agent.integrations.mcp.gateway_provider import set_ecommerce_gateway
from agent.supervisor import supervisor_graph
from agent.supervisor.state import SelectRouteRoute

pytestmark = pytest.mark.anyio


class FakeSupervisorE2ELLM:
    """Mock LLM to handle routing, agent query reasoning, and parameter extraction."""

    def __init__(
        self,
        route: str,
        tool_name: str,
        email: str | None = None,
        tool_args: dict[str, Any] | None = None,
    ) -> None:
        self.route = route
        self.tool_name = tool_name
        self.email = email
        self.tool_args = tool_args or {}

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
        if schema.__name__ == "ExtractedEmail":
            class StructuredEmailInvokable:
                async def ainvoke(self, messages: Any, **kwargs: Any) -> Any:
                    prompt_text = ""
                    if hasattr(messages, "to_string"):
                        prompt_text = messages.to_string()
                    elif hasattr(messages, "text"):
                        prompt_text = messages.text
                    elif isinstance(messages, str):
                        prompt_text = messages
                    elif isinstance(messages, list):
                        prompt_text = "\n".join(getattr(msg, "content", "") for msg in messages)

                    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", prompt_text)
                    extracted_email = email_match.group(0) if email_match else "mock_extracted@example.com"
                    return schema(email=extracted_email)
            return StructuredEmailInvokable()

        # Structured output router mock for supervisor
        class Router:
            def __init__(self, route: str) -> None:
                self.route = route

            async def ainvoke(self, *args: Any, **kwargs: Any) -> dict[str, str]:
                return {"route": self.route}

        return Router(self.route)

    def bind_tools(self, tools: list[Any]) -> "FakeSupervisorE2ELLM":
        return self

    async def ainvoke(self, messages: Any, **kwargs: Any) -> AIMessage:
        # 1. Tool loop termination check
        if isinstance(messages, list) and messages and isinstance(messages[-1], ToolMessage):
            return AIMessage(content="Here is the retrieved customer information.", type="ai")

        # 2. Main agent query tool calling
        args = dict(self.tool_args)
        if self.email:
            args["email"] = self.email
        tool_call = {
            "name": self.tool_name,
            "args": args,
            "id": "call_e2e_123",
        }
        return AIMessage(content="", tool_calls=[tool_call], type="ai")


async def test_supervisor_e2e_user_query_exists(monkeypatch) -> None:
    # Setup mock LLM & gateway
    fake_llm = FakeSupervisorE2ELLM(
        route="ecommerce_query",
        tool_name="get_ecommerce_user",
        email="shopper@example.com",
    )
    monkeypatch.setattr(llm, "get_llm_model", lambda: fake_llm)

    mock_gateway = EcommerceGatewayMock()
    mock_gateway.expected_user = GetECommerceUserResponse(
        exists=True,
        user_id=88,
        email="shopper@example.com",
        user_name="John Doe",
    )
    set_ecommerce_gateway(mock_gateway)

    config = {"configurable": {"thread_id": "e2e-thread-1"}}

    # Invoke supervisor graph directly
    result = await supervisor_graph.ainvoke(
        {"messages": [HumanMessage(content="Check customer profile shopper@example.com")]},
        config=config,
    )

    # Assert correct routing and output matching
    assert result["route"] == SelectRouteRoute.ECOMMERCE_QUERY
    assert len(result["outputs"]) == 1
    output = AgentOutput.model_validate(result["outputs"][0])
    assert output.parts[0].schema_id == AgentOutputSchemaId.ECOMMERCE_USER_RESULT_V1.value
    assert output.parts[0].data["user_id"] == 88


async def test_supervisor_e2e_orders_query_interrupt_and_resumes(monkeypatch) -> None:
    # Setup E2E LLM WITHOUT email argument to trigger interrupt
    fake_llm = FakeSupervisorE2ELLM(
        route="ecommerce_query",
        tool_name="get_ecommerce_orders",
        email=None,
    )
    monkeypatch.setattr(llm, "get_llm_model", lambda: fake_llm)

    mock_gateway = EcommerceGatewayMock()
    mock_gateway.expected_orders = GetECommerceOrdersResponse(
        orders=[
            ECommerceOrderRecord(
                order_id=555,
                user_id=12,
                email="buyer@example.com",
                status=OrderStatus.PENDING,
                total_amount=50.0,
                created_ts=1778900000,
            )
        ]
    )
    set_ecommerce_gateway(mock_gateway)

    config = {"configurable": {"thread_id": "e2e-thread-2"}}

    # Turn 1: Starts execution, routes to subgraph, hits interrupt
    res1 = await supervisor_graph.ainvoke(
        {"messages": [HumanMessage(content="Find my order history")]},
        config=config,
    )

    # Verify run is suspended and carries the expected interrupt list
    assert res1.get("__interrupt__") is not None
    assert len(res1["__interrupt__"]) == 1
    val = res1["__interrupt__"][0].value
    assert val["schema_id"] == HumanInputSchemaId.GET_ORDERS_INPUT_V1.value

    # Turn 2: Resume with structured response data
    resume_payload = {"email": "buyer@example.com"}
    res2 = await supervisor_graph.ainvoke(
        Command(resume=resume_payload),
        config=config,
    )

    # Verify graph executes to completion and produces orders list outputs
    assert len(res2["outputs"]) == 1
    output = AgentOutput.model_validate(res2["outputs"][0])
    assert output.parts[0].schema_id == AgentOutputSchemaId.ECOMMERCE_ORDERS_RESULT_V1.value
    orders_output = ECommerceOrdersOutput.model_validate(output.parts[0].data)
    assert orders_output.orders[0].order_id == 555
    assert orders_output.orders[0].status == OrderStatus.PENDING.value


async def test_supervisor_e2e_order_details_query_outputs_public_schema(
    monkeypatch,
) -> None:
    fake_llm = FakeSupervisorE2ELLM(
        route="ecommerce_query",
        tool_name="get_ecommerce_order_details",
        tool_args={"order_id": 808},
    )
    monkeypatch.setattr(llm, "get_llm_model", lambda: fake_llm)

    mock_gateway = EcommerceGatewayMock()
    mock_gateway.expected_order_details = GetECommerceOrderDetailsResponse(
        exists=True,
        order=ECommerceOrderMeta(
            order_id=808,
            user_id=88,
            email="shopper@example.com",
            status=OrderStatus.COMPLETED,
            total_amount=81.5,
            created_ts=1778900000,
        ),
        items=[
            ECommerceOrderItemRecord(
                item_id=80,
                sku_id=81,
                sku_code="SKU-81",
                name="Coffee Mug",
                quantity=1,
                price=81.5,
            )
        ],
    )
    set_ecommerce_gateway(mock_gateway)

    config = {"configurable": {"thread_id": "e2e-thread-order-details-1"}}

    result = await supervisor_graph.ainvoke(
        {"messages": [HumanMessage(content="Show me order 808 details")]},
        config=config,
    )

    assert result["route"] == SelectRouteRoute.ECOMMERCE_QUERY
    output = AgentOutput.model_validate(result["outputs"][0])
    assert (
        output.parts[0].schema_id
        == AgentOutputSchemaId.ECOMMERCE_ORDER_DETAILS_RESULT_V1.value
    )
    order_output = ECommerceOrderDetailsOutput.model_validate(output.parts[0].data)
    assert order_output.exists is True
    assert order_output.order is not None
    assert order_output.order.order_id == 808
    assert order_output.items[0].sku_code == "SKU-81"


async def test_supervisor_e2e_user_query_non_existent(monkeypatch) -> None:
    # Setup mock LLM & gateway
    fake_llm = FakeSupervisorE2ELLM(
        route="ecommerce_query",
        tool_name="get_ecommerce_user",
        email="unknown@example.com",
    )
    monkeypatch.setattr(llm, "get_llm_model", lambda: fake_llm)

    mock_gateway = EcommerceGatewayMock()
    mock_gateway.expected_user = GetECommerceUserResponse(exists=False)
    set_ecommerce_gateway(mock_gateway)

    config = {"configurable": {"thread_id": "e2e-thread-3"}}

    result = await supervisor_graph.ainvoke(
        {"messages": [HumanMessage(content="Query profile unknown@example.com")]},
        config=config,
    )

    # Must return user output indicating not found and complete gracefully
    assert len(result["outputs"]) == 1
    output = AgentOutput.model_validate(result["outputs"][0])
    assert output.parts[0].schema_id == AgentOutputSchemaId.ECOMMERCE_USER_RESULT_V1.value
    assert output.parts[0].data["exists"] is False
    assert output.parts[0].data["user_id"] is None
