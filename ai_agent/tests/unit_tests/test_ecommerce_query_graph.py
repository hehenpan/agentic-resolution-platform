import re
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command
from mock_ecommerce_gateway import EcommerceGatewayMock
from shared_common.schemas.ai_agent.human_input_schemas import (
    GetOrderDetailsByOrderIdInputModel,
    GetOrdersByEmailInputModel,
    GetReturnsByCustomerIdInputModel,
    GetReturnsByOrderIdInputModel,
    GetUserByEmailInputModel,
)
from shared_common.schemas.ai_agent.outputs import (
    ECommerceOrderDetailsOutput,
    ECommerceOrdersOutput,
    ECommerceReturnsByCustomerOutput,
    ECommerceReturnsByOrderOutput,
)
from shared_common.schemas.ai_agent.schema_ids import (
    AgentOutputSchemaId,
    HumanInputSchemaId,
)
from shared_common.schemas.mcp_server.enums import (
    ItemCondition,
    OrderStatus,
    ReturnReasonCode,
    ReturnStatus,
)
from shared_common.schemas.mcp_server.order import (
    ECommerceOrderItemRecord,
    ECommerceOrderMeta,
    ECommerceOrderRecord,
    GetECommerceOrderDetailsResponse,
    GetECommerceOrdersResponse,
)
from shared_common.schemas.mcp_server.returns import (
    GetReturnRequestRecord,
    GetReturnRequestsByCustomerResponse,
    GetReturnRequestsByOrderResponse,
)
from shared_common.schemas.mcp_server.user import GetECommerceUserResponse

from agent.core import llm
from agent.integrations.mcp.gateway_provider import set_ecommerce_gateway
from agent.supervisor.ecommerce_query.graph import ecommerce_query_graph

pytestmark = pytest.mark.anyio


def _return_record(return_id: int = 701, order_id: int = 901, customer_id: int = 301) -> GetReturnRequestRecord:
    return GetReturnRequestRecord(
        id=return_id,
        order_id=order_id,
        customer_id=customer_id,
        status=ReturnStatus.REQUESTED,
        reason_code=ReturnReasonCode.DAMAGED,
        reason_text="Box arrived damaged",
        item_condition=ItemCondition.DAMAGED,
        requested_at=1778900100,
        approved_at=None,
        rejected_at=None,
        received_at=None,
        closed_at=None,
        resolution_type=None,
        created_by=None,
        created_at=1778900100,
        updated_at=1778900200,
    )


class FakeQueryAgentLLM:
    """Mock LLM that returns pre-configured tool calls or extracted email values."""

    def __init__(
        self,
        tool_name: str,
        email: str | None = None,
        tool_args: dict[str, Any] | None = None,
    ) -> None:
        self.tool_name = tool_name
        self.email = email
        self.tool_args = tool_args or {}

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

                if schema.__name__ == "ExtractedEmail":
                    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", prompt_text)
                    extracted_email = email_match.group(0) if email_match else None
                    return schema(email=extracted_email)

                id_match = re.search(r"\b\d+\b", prompt_text)
                extracted_id = int(id_match.group(0)) if id_match else None
                if schema.__name__ == "ExtractedOrderId":
                    return schema(order_id=extracted_id)
                if schema.__name__ == "ExtractedCustomerId":
                    return schema(customer_id=extracted_id)

                return schema()

        return StructuredInvokable()

    async def ainvoke(self, messages: Any, **kwargs: Any) -> AIMessage:
        # If the last message is a ToolMessage, return final response to stop the loop
        if isinstance(messages, list) and messages and isinstance(messages[-1], ToolMessage):
            return AIMessage(content="Here is the retrieved customer information.", type="ai")

        # Otherwise, return tool call
        args = dict(self.tool_args)
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


async def test_retrieve_order_details_success_without_interrupt(monkeypatch) -> None:
    fake_llm = FakeQueryAgentLLM(
        "get_ecommerce_order_details",
        tool_args={"order_id": 901},
    )
    monkeypatch.setattr(llm, "get_llm_model", lambda: fake_llm)

    mock_gateway = EcommerceGatewayMock()
    mock_gateway.expected_order_details = GetECommerceOrderDetailsResponse(
        exists=True,
        order=ECommerceOrderMeta(
            order_id=901,
            user_id=301,
            email="buyer@example.com",
            status=OrderStatus.PAID,
            total_amount=44.5,
            created_ts=1778900000,
        ),
        items=[
            ECommerceOrderItemRecord(
                item_id=11,
                sku_id=22,
                sku_code="SKU-22",
                name="Desk Lamp",
                quantity=2,
                price=22.25,
            )
        ],
    )
    set_ecommerce_gateway(mock_gateway)

    config = {"configurable": {"thread_id": "test-thread-order-details-1"}}
    result = await ecommerce_query_graph.ainvoke(
        {"messages": [HumanMessage(content="Show order 901 details")]},
        config=config,
    )

    assert mock_gateway.calls["get_ecommerce_order_details"][0].order_id == 901
    output = result["outputs"][0]
    assert (
        output.parts[0].schema_id
        == AgentOutputSchemaId.ECOMMERCE_ORDER_DETAILS_RESULT_V1.value
    )
    order_output = ECommerceOrderDetailsOutput.model_validate(output.parts[0].data)
    assert order_output.exists is True
    assert order_output.order is not None
    assert order_output.order.order_id == 901
    assert order_output.items[0].sku_code == "SKU-22"


async def test_retrieve_order_details_interrupt_resumes_with_llm_text(
    monkeypatch,
) -> None:
    fake_llm = FakeQueryAgentLLM("get_ecommerce_order_details")
    monkeypatch.setattr(llm, "get_llm_model", lambda: fake_llm)

    mock_gateway = EcommerceGatewayMock()
    mock_gateway.expected_order_details = GetECommerceOrderDetailsResponse(
        exists=False,
    )
    set_ecommerce_gateway(mock_gateway)

    config = {"configurable": {"thread_id": "test-thread-order-details-2"}}
    res1 = await ecommerce_query_graph.ainvoke(
        {"messages": [HumanMessage(content="Show the order detail")]},
        config=config,
    )

    val = res1["__interrupt__"][0].value
    assert val["schema_id"] == HumanInputSchemaId.GET_ORDER_DETAILS_INPUT_V1.value
    assert val["input_schema"] == GetOrderDetailsByOrderIdInputModel.model_json_schema()

    resume_payload = GetOrderDetailsByOrderIdInputModel(
        llm_text="The order id is 902",
    ).model_dump(mode="json")
    result = await ecommerce_query_graph.ainvoke(
        Command(resume=resume_payload),
        config=config,
    )

    assert mock_gateway.calls["get_ecommerce_order_details"][0].order_id == 902
    order_output = ECommerceOrderDetailsOutput.model_validate(
        result["outputs"][0].parts[0].data,
    )
    assert order_output.exists is False
    assert order_output.order is None


async def test_retrieve_returns_by_order_interrupt_and_resumes(monkeypatch) -> None:
    fake_llm = FakeQueryAgentLLM("get_return_requests_by_order")
    monkeypatch.setattr(llm, "get_llm_model", lambda: fake_llm)

    mock_gateway = EcommerceGatewayMock()
    mock_gateway.expected_return_by_order = GetReturnRequestsByOrderResponse(
        returns=_return_record(return_id=702, order_id=903, customer_id=302),
    )
    set_ecommerce_gateway(mock_gateway)

    config = {"configurable": {"thread_id": "test-thread-return-order-1"}}
    res1 = await ecommerce_query_graph.ainvoke(
        {"messages": [HumanMessage(content="Find return for this order")]},
        config=config,
    )

    val = res1["__interrupt__"][0].value
    assert val["schema_id"] == HumanInputSchemaId.GET_RETURNS_BY_ORDER_INPUT_V1.value
    assert val["input_schema"] == GetReturnsByOrderIdInputModel.model_json_schema()

    resume_payload = GetReturnsByOrderIdInputModel(order_id=903).model_dump(mode="json")
    result = await ecommerce_query_graph.ainvoke(
        Command(resume=resume_payload),
        config=config,
    )

    assert mock_gateway.calls["get_return_requests_by_order"][0].order_id == 903
    output = result["outputs"][0]
    assert (
        output.parts[0].schema_id
        == AgentOutputSchemaId.ECOMMERCE_RETURNS_BY_ORDER_RESULT_V1.value
    )
    returns_output = ECommerceReturnsByOrderOutput.model_validate(
        output.parts[0].data,
    )
    assert returns_output.return_request is not None
    assert returns_output.return_request.return_request_id == 702
    assert returns_output.return_request.status == ReturnStatus.REQUESTED.value


async def test_retrieve_returns_by_customer_interrupt_resumes_with_llm_text(
    monkeypatch,
) -> None:
    fake_llm = FakeQueryAgentLLM("get_return_requests_by_customer")
    monkeypatch.setattr(llm, "get_llm_model", lambda: fake_llm)

    mock_gateway = EcommerceGatewayMock()
    mock_gateway.expected_returns_by_customer = GetReturnRequestsByCustomerResponse(
        returns=[
            _return_record(return_id=703, order_id=904, customer_id=303),
            _return_record(return_id=704, order_id=905, customer_id=303),
        ],
    )
    set_ecommerce_gateway(mock_gateway)

    config = {"configurable": {"thread_id": "test-thread-return-customer-1"}}
    res1 = await ecommerce_query_graph.ainvoke(
        {"messages": [HumanMessage(content="Find returns for a customer")]},
        config=config,
    )

    val = res1["__interrupt__"][0].value
    assert (
        val["schema_id"]
        == HumanInputSchemaId.GET_RETURNS_BY_CUSTOMER_INPUT_V1.value
    )
    assert (
        val["input_schema"]
        == GetReturnsByCustomerIdInputModel.model_json_schema()
    )

    resume_payload = GetReturnsByCustomerIdInputModel(
        llm_text="customer id 303 please",
    ).model_dump(mode="json")
    result = await ecommerce_query_graph.ainvoke(
        Command(resume=resume_payload),
        config=config,
    )

    assert mock_gateway.calls["get_return_requests_by_customer"][0].customer_id == 303
    output = result["outputs"][0]
    assert (
        output.parts[0].schema_id
        == AgentOutputSchemaId.ECOMMERCE_RETURNS_BY_CUSTOMER_RESULT_V1.value
    )
    returns_output = ECommerceReturnsByCustomerOutput.model_validate(
        output.parts[0].data,
    )
    assert [item.return_request_id for item in returns_output.returns] == [703, 704]


async def test_retrieve_returns_by_customer_resume_with_unextractable_text_fails(
    monkeypatch,
) -> None:
    fake_llm = FakeQueryAgentLLM("get_return_requests_by_customer")
    monkeypatch.setattr(llm, "get_llm_model", lambda: fake_llm)

    mock_gateway = EcommerceGatewayMock()
    set_ecommerce_gateway(mock_gateway)

    config = {"configurable": {"thread_id": "test-thread-return-customer-2"}}
    await ecommerce_query_graph.ainvoke(
        {"messages": [HumanMessage(content="Find returns for a customer")]},
        config=config,
    )

    resume_payload = GetReturnsByCustomerIdInputModel(
        llm_text="I do not know the customer identifier",
    ).model_dump(mode="json")
    with pytest.raises(ValueError, match="Could not extract customer ID"):
        await ecommerce_query_graph.ainvoke(
            Command(resume=resume_payload),
            config=config,
        )

    assert mock_gateway.calls["get_return_requests_by_customer"] == []


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
