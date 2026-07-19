import re
from typing import Any
import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command
from mock_ecommerce_gateway import EcommerceGatewayMock
from shared_common.schemas.ai_agent import AgentReturnReason, AgentItemCondition
from shared_common.schemas.ai_agent.human_input_schemas import CreateReturnRequestInputModel
from shared_common.schemas.ai_agent.outputs import ECommerceCreateReturnOutput
from shared_common.schemas.ai_agent.schema_ids import AgentOutputSchemaId, HumanInputSchemaId
from shared_common.schemas.mcp_server.enums import ReturnStatus, ReturnReasonCode, ItemCondition
from shared_common.schemas.mcp_server.returns import (
    GetReturnRequestRecord,
    CreateReturnRequestResponse,
)

from agent.core import llm
from agent.integrations.mcp.gateway_provider import set_ecommerce_gateway
from agent.supervisor.ecommerce_action.graph import ecommerce_action_graph
from agent.supervisor.ecommerce_action.nodes import ExtractedReturnDetails

pytestmark = pytest.mark.anyio


class FakeActionAgentLLM:
    """Mock LLM that returns pre-configured tool calls or extracted values."""

    def __init__(
        self,
        tool_name: str,
        tool_args: dict[str, Any] | None = None,
        extracted_details: ExtractedReturnDetails | None = None,
    ) -> None:
        self.tool_name = tool_name
        self.tool_args = tool_args or {}
        self.extracted_details = extracted_details

    def bind_tools(self, tools: list[Any]) -> "FakeActionAgentLLM":
        return self

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
        class StructuredInvokable:
            async def ainvoke(self, messages: Any, **kwargs: Any) -> Any:
                if schema.__name__ == "ExtractedReturnDetails":
                    return self.parent.extracted_details or schema()
                return schema()

        StructuredInvokable.parent = self
        return StructuredInvokable()

    async def ainvoke(self, messages: Any, **kwargs: Any) -> AIMessage:
        if isinstance(messages, list) and messages and isinstance(messages[-1], ToolMessage):
            return AIMessage(content="Return request processed successfully.", type="ai")

        tool_call = {
            "name": self.tool_name,
            "args": self.tool_args,
            "id": "call_999",
        }
        return AIMessage(content="", tool_calls=[tool_call], type="ai")


def _mock_return_record(return_id: int = 801, order_id: int = 901, customer_id: int = 101) -> GetReturnRequestRecord:
    return GetReturnRequestRecord(
        id=return_id,
        order_id=order_id,
        customer_id=customer_id,
        status=ReturnStatus.REQUESTED,
        reason_code=ReturnReasonCode.DAMAGED,
        reason_text="Damaged during shipping",
        item_condition=ItemCondition.DAMAGED,
        requested_at=1778900100,
        approved_at=None,
        rejected_at=None,
        received_at=None,
        closed_at=None,
        resolution_type=None,
        created_by=1,
        created_at=1778900100,
        updated_at=1778900200,
    )


async def test_create_return_success_without_interrupt(monkeypatch) -> None:
    # Setup mock LLM & gateway
    fake_llm = FakeActionAgentLLM(
        "create_ecommerce_return_request",
        tool_args={
            "order_id": 901,
            "customer_id": 101,
            "reason_code": AgentReturnReason.DAMAGED.value,
            "item_condition": AgentItemCondition.DAMAGED.value,
            "reason_text": "Damaged during shipping",
            "created_by": 1,
        },
    )
    monkeypatch.setattr(llm, "get_llm_model", lambda: fake_llm)

    mock_gateway = EcommerceGatewayMock()
    mock_gateway.expected_create_return = CreateReturnRequestResponse(
        success=True,
        return_request=_mock_return_record(),
    )
    set_ecommerce_gateway(mock_gateway)

    config = {"configurable": {"thread_id": "test-action-thread-1"}}
    result = await ecommerce_action_graph.ainvoke(
        {"messages": [HumanMessage(content="Return order 901 for customer 101")]},
        config=config,
    )

    # Verify results
    state_values = (await ecommerce_action_graph.aget_state(config)).values
    assert state_values.get("create_return_output") is not None
    assert state_values["create_return_output"].success is True
    assert state_values["create_return_output"].return_request.return_request_id == 801
    assert state_values.get("return_details") is not None
    assert state_values["return_details"].order_id == 901
    assert state_values["return_details"].customer_id == 101
    assert state_values["return_details"].reason_code == AgentReturnReason.DAMAGED
    assert state_values["return_details"].item_condition == AgentItemCondition.DAMAGED
    assert len(result["outputs"]) == 1
    assert result["outputs"][0].parts[0].schema_id == AgentOutputSchemaId.ECOMMERCE_CREATE_RETURN_RESULT_V1.value


async def test_create_return_triggers_interrupt_and_resumes_with_structured_data(
    monkeypatch,
) -> None:
    # Setup mock LLM & gateway
    fake_llm = FakeActionAgentLLM("create_ecommerce_return_request")
    monkeypatch.setattr(llm, "get_llm_model", lambda: fake_llm)

    mock_gateway = EcommerceGatewayMock()
    mock_gateway.expected_create_return = CreateReturnRequestResponse(
        success=True,
        return_request=_mock_return_record(return_id=802, order_id=902, customer_id=102),
    )
    set_ecommerce_gateway(mock_gateway)

    config = {"configurable": {"thread_id": "test-action-thread-2"}}

    # Execute graph - it must hit interrupt due to missing arguments
    res = await ecommerce_action_graph.ainvoke(
        {"messages": [HumanMessage(content="Initiate a return request")]},
        config=config,
    )

    interrupts = res.get("__interrupt__")
    assert interrupts is not None
    assert len(interrupts) == 1
    val = interrupts[0].value
    assert val["schema_id"] == HumanInputSchemaId.CREATE_RETURN_REQUEST_INPUT_V1.value
    assert val["input_schema"] == CreateReturnRequestInputModel.model_json_schema()

    # Resume the graph with structured payload
    resume_payload = CreateReturnRequestInputModel(
        order_id=902,
        customer_id=102,
        reason_code=AgentReturnReason.DAMAGED,
        reason_text="Damaged during shipping",
        item_condition=AgentItemCondition.DAMAGED,
        created_by=1,
    ).model_dump(mode="json")

    result = await ecommerce_action_graph.ainvoke(
        Command(resume=resume_payload),
        config=config,
    )

    # Verify state updates and output
    state_values = (await ecommerce_action_graph.aget_state(config)).values
    assert state_values["create_return_output"].success is True
    assert state_values["create_return_output"].return_request.return_request_id == 802
    assert state_values["create_return_output"].return_request.order_id == 902
    assert state_values.get("return_details") is not None
    assert state_values["return_details"].order_id == 902
    assert state_values["return_details"].customer_id == 102
    assert result["outputs"][0].parts[0].schema_id == AgentOutputSchemaId.ECOMMERCE_CREATE_RETURN_RESULT_V1.value


async def test_create_return_triggers_interrupt_and_resumes_with_llm_text(
    monkeypatch,
) -> None:
    # Setup mock LLM & gateway
    extracted = ExtractedReturnDetails(
        order_id=903,
        customer_id=103,
        reason_code=AgentReturnReason.WRONG_ITEM,
        reason_text="Shipped wrong item",
        item_condition=AgentItemCondition.UNOPENED,
    )
    fake_llm = FakeActionAgentLLM("create_ecommerce_return_request", extracted_details=extracted)
    monkeypatch.setattr(llm, "get_llm_model", lambda: fake_llm)

    mock_gateway = EcommerceGatewayMock()
    mock_gateway.expected_create_return = CreateReturnRequestResponse(
        success=True,
        return_request=GetReturnRequestRecord(
            id=803,
            order_id=903,
            customer_id=103,
            status=ReturnStatus.REQUESTED,
            reason_code=ReturnReasonCode.WRONG_ITEM,
            reason_text="Shipped wrong item",
            item_condition=ItemCondition.UNOPENED,
            requested_at=1778900100,
            approved_at=None,
            rejected_at=None,
            received_at=None,
            closed_at=None,
            resolution_type=None,
            created_by=1,
            created_at=1778900100,
            updated_at=1778900200,
        ),
    )
    set_ecommerce_gateway(mock_gateway)

    config = {"configurable": {"thread_id": "test-action-thread-3"}}

    # Execute graph - it must hit interrupt
    await ecommerce_action_graph.ainvoke(
        {"messages": [HumanMessage(content="Return request")]},
        config=config,
    )

    # Resume the graph with unstructured llm_text response
    resume_payload = CreateReturnRequestInputModel(
        llm_text="I want to return order 903 for customer 103 because it was the wrong item, it is unopened."
    ).model_dump(mode="json")

    result = await ecommerce_action_graph.ainvoke(
        Command(resume=resume_payload),
        config=config,
    )

    # Verify structured state updates
    state_values = (await ecommerce_action_graph.aget_state(config)).values
    assert state_values["create_return_output"].success is True
    assert state_values["create_return_output"].return_request.return_request_id == 803
    assert state_values["create_return_output"].return_request.reason_code == 2  # ReturnReasonCode.WRONG_ITEM
    assert state_values["create_return_output"].return_request.item_condition == 0  # ItemCondition.UNOPENED
    assert state_values.get("return_details") is not None
    assert state_values["return_details"].order_id == 903
    assert state_values["return_details"].customer_id == 103
    assert state_values["return_details"].reason_code == AgentReturnReason.WRONG_ITEM
    assert state_values["return_details"].item_condition == AgentItemCondition.UNOPENED
    assert result["outputs"][0].parts[0].schema_id == AgentOutputSchemaId.ECOMMERCE_CREATE_RETURN_RESULT_V1.value


async def test_create_return_resume_with_unextractable_text_fails(
    monkeypatch,
) -> None:
    # Setup mock LLM (returns empty details extraction)
    fake_llm = FakeActionAgentLLM("create_ecommerce_return_request", extracted_details=ExtractedReturnDetails())
    monkeypatch.setattr(llm, "get_llm_model", lambda: fake_llm)

    mock_gateway = EcommerceGatewayMock()
    set_ecommerce_gateway(mock_gateway)

    config = {"configurable": {"thread_id": "test-action-thread-4"}}

    await ecommerce_action_graph.ainvoke(
        {"messages": [HumanMessage(content="Return request")]},
        config=config,
    )

    # Resume with text that cannot extract any required info
    resume_payload = CreateReturnRequestInputModel(
        llm_text="Please do something but no details are here."
    ).model_dump(mode="json")

    with pytest.raises(ValueError, match="Missing required return request details"):
        await ecommerce_action_graph.ainvoke(
            Command(resume=resume_payload),
            config=config,
        )

    assert mock_gateway.calls["create_ecommerce_return_request"] == []
