import re
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command
from mock_ecommerce_gateway import EcommerceGatewayMock
from shared_common.schemas.ai_agent.human_input_schemas import (
    GetOrdersByEmailInputModel,
    GetUserByEmailInputModel,
)
from shared_common.schemas.ai_agent.outputs import ECommerceOrdersOutput
from shared_common.schemas.ai_agent.schema_ids import (
    AgentOutputSchemaId,
    HumanInputSchemaId,
)
from shared_common.schemas.mcp_server.enums import OrderStatus
from shared_common.schemas.mcp_server.order import (
    ECommerceOrderRecord,
    GetECommerceOrdersResponse,
)
from shared_common.schemas.mcp_server.user import GetECommerceUserResponse

from agent.core import llm
from agent.integrations.mcp.gateway_provider import set_ecommerce_gateway
from agent.supervisor.ecommerce_query.graph import ecommerce_query_graph

pytestmark = pytest.mark.anyio


class FakeQueryAgentLLM:
    """Mock LLM that returns pre-configured tool calls or extracted email values."""

    def __init__(self, tool_name: str, email: str | None = None) -> None:
        self.tool_name = tool_name
        self.email = email

    def bind_tools(self, tools: list[Any]) -> "FakeQueryAgentLLM":
        return self

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
        class StructuredInvokable:
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

        return StructuredInvokable()

    async def ainvoke(self, messages: Any, **kwargs: Any) -> AIMessage:
        # If the last message is a ToolMessage, return final response to stop the loop
        if isinstance(messages, list) and messages and isinstance(messages[-1], ToolMessage):
            return AIMessage(content="Here is the retrieved customer information.", type="ai")

        # Otherwise, return tool call
        args = {}
        if self.email:
            args["email"] = self.email

        tool_call = {
            "name": self.tool_name,
            "args": args,
            "id": "call_123",
        }
        return AIMessage(content="", tool_calls=[tool_call], type="ai")


async def test_retrieve_user_success_without_interrupt(monkeypatch) -> None:
    # Setup mock LLM & mock Gateway
    fake_llm = FakeQueryAgentLLM("get_ecommerce_user", "test@example.com")
    monkeypatch.setattr(llm, "get_llm_model", lambda: fake_llm)

    mock_gateway = EcommerceGatewayMock()
    mock_gateway.expected_user = GetECommerceUserResponse(
        exists=True,
        user_id=42,
        email="test@example.com",
        user_name="John Doe",
    )
    set_ecommerce_gateway(mock_gateway)

    # Invoke graph - since email is supplied by LLM tool call argument, no interrupt is raised
    config = {"configurable": {"thread_id": "test-thread-1"}}
    result = await ecommerce_query_graph.ainvoke(
        {"messages": [HumanMessage(content="Query user test@example.com")]},
        config=config,
    )

    # Verify results
    state_values = (await ecommerce_query_graph.aget_state(config)).values
    assert state_values.get("user_output") is not None
    assert state_values["user_output"].exists is True
    assert state_values["user_output"].user_id == 42
    assert state_values["user_output"].email == "test@example.com"
    assert len(result["outputs"]) == 1
    assert result["outputs"][0].parts[0].schema_id == AgentOutputSchemaId.ECOMMERCE_USER_RESULT_V1.value


async def test_retrieve_user_triggers_interrupt_and_resumes_with_structured_data(
    monkeypatch,
) -> None:
    # Setup mock LLM to call tool WITHOUT providing the email argument
    fake_llm = FakeQueryAgentLLM("get_ecommerce_user", email=None)
    monkeypatch.setattr(llm, "get_llm_model", lambda: fake_llm)

    mock_gateway = EcommerceGatewayMock()
    mock_gateway.expected_user = GetECommerceUserResponse(
        exists=True,
        user_id=101,
        email="shopper@example.com",
        user_name="Alice Smith",
    )
    set_ecommerce_gateway(mock_gateway)

    config = {"configurable": {"thread_id": "test-thread-2"}}

    # Execute graph - it must hit interrupt due to missing email
    res1 = await ecommerce_query_graph.ainvoke(
        {"messages": [HumanMessage(content="Retrieve user profile")]},
        config=config,
    )

    # Assert interrupt attributes
    interrupts = res1.get("__interrupt__")
    assert interrupts is not None
    assert len(interrupts) == 1
    val = interrupts[0].value
    assert val["schema_id"] == HumanInputSchemaId.GET_USER_INPUT_V1.value
    assert val["input_schema"] == GetUserByEmailInputModel.model_json_schema()

    # Resume the graph with structured email payload
    resume_payload = GetUserByEmailInputModel(email="shopper@example.com").model_dump(
        mode="json"
    )
    result = await ecommerce_query_graph.ainvoke(
        Command(resume=resume_payload),
        config=config,
    )

    # Verify graph completes and returns retrieved user details
    state_values = (await ecommerce_query_graph.aget_state(config)).values
    assert state_values["user_output"].exists is True
    assert state_values["user_output"].user_id == 101
    assert state_values["user_output"].email == "shopper@example.com"
    assert len(result["outputs"]) == 1
    assert result["outputs"][0].parts[0].schema_id == AgentOutputSchemaId.ECOMMERCE_USER_RESULT_V1.value


async def test_retrieve_user_triggers_interrupt_and_resumes_with_llm_text(
    monkeypatch,
) -> None:
    # Setup mock LLM
    fake_llm = FakeQueryAgentLLM("get_ecommerce_user", email=None)
    monkeypatch.setattr(llm, "get_llm_model", lambda: fake_llm)

    mock_gateway = EcommerceGatewayMock()
    mock_gateway.expected_user = GetECommerceUserResponse(
        exists=True,
        user_id=202,
        email="natural@example.com",
        user_name="Bob Johnson",
    )
    set_ecommerce_gateway(mock_gateway)

    config = {"configurable": {"thread_id": "test-thread-3"}}

    res1 = await ecommerce_query_graph.ainvoke(
        {"messages": [HumanMessage(content="Lookup user details")]},
        config=config,
    )
    assert res1.get("__interrupt__") is not None

    # Resume the graph with unstructured llm_text response
    resume_payload = GetUserByEmailInputModel(
        llm_text="The email is natural@example.com"
    ).model_dump(mode="json")
    await ecommerce_query_graph.ainvoke(
        Command(resume=resume_payload),
        config=config,
    )

    # Verify parameter extraction worked and graph completed
    state_values = (await ecommerce_query_graph.aget_state(config)).values
    assert state_values["user_output"].exists is True
    assert state_values["user_output"].user_id == 202
    assert state_values["user_output"].email == "natural@example.com"


async def test_retrieve_orders_triggers_interrupt_and_resumes(monkeypatch) -> None:
    # Setup mock LLM
    fake_llm = FakeQueryAgentLLM("get_ecommerce_orders", email=None)
    monkeypatch.setattr(llm, "get_llm_model", lambda: fake_llm)

    mock_gateway = EcommerceGatewayMock()
    mock_gateway.expected_orders = GetECommerceOrdersResponse(
        orders=[
            ECommerceOrderRecord(
                order_id=999,
                user_id=123,
                email="orders@example.com",
                status=OrderStatus.SHIPPED,
                total_amount=120.50,
                created_ts=1778900000,
            )
        ]
    )
    set_ecommerce_gateway(mock_gateway)

    config = {"configurable": {"thread_id": "test-thread-4"}}

    res1 = await ecommerce_query_graph.ainvoke(
        {"messages": [HumanMessage(content="Find my order history")]},
        config=config,
    )

    # Assert interrupt attributes
    interrupts = res1.get("__interrupt__")
    assert interrupts is not None
    assert len(interrupts) == 1
    val = interrupts[0].value
    assert val["schema_id"] == HumanInputSchemaId.GET_ORDERS_INPUT_V1.value

    # Resume the graph
    resume_payload = GetOrdersByEmailInputModel(email="orders@example.com").model_dump(
        mode="json"
    )
    result = await ecommerce_query_graph.ainvoke(
        Command(resume=resume_payload),
        config=config,
    )

    # Verify orders list retrieved
    state_values = (await ecommerce_query_graph.aget_state(config)).values
    assert state_values["orders_output"].customer_email == "orders@example.com"
    assert len(state_values["orders_output"].orders) == 1
    assert state_values["orders_output"].orders[0].order_id == 999
    assert state_values["orders_output"].orders[0].status == OrderStatus.SHIPPED.value
    assert result["outputs"][0].parts[0].schema_id == AgentOutputSchemaId.ECOMMERCE_ORDERS_RESULT_V1.value
    orders_output = ECommerceOrdersOutput.model_validate(result["outputs"][0].parts[0].data)
    assert orders_output.orders[0].order_id == 999


async def test_retrieve_user_non_existent_graceful(monkeypatch) -> None:
    fake_llm = FakeQueryAgentLLM("get_ecommerce_user", "notfound@example.com")
    monkeypatch.setattr(llm, "get_llm_model", lambda: fake_llm)

    mock_gateway = EcommerceGatewayMock()
    mock_gateway.expected_user = GetECommerceUserResponse(exists=False)
    set_ecommerce_gateway(mock_gateway)

    config = {"configurable": {"thread_id": "test-thread-5"}}
    await ecommerce_query_graph.ainvoke(
        {"messages": [HumanMessage(content="Query profile notfound@example.com")]},
        config=config,
    )

    # Must return user details with exists=False and not crash
    state_values = (await ecommerce_query_graph.aget_state(config)).values
    assert state_values["user_output"].exists is False
    assert state_values["user_output"].user_id is None
    assert state_values["user_output"].email == "notfound@example.com"
    assert state_values["user_output"].user_name is None
