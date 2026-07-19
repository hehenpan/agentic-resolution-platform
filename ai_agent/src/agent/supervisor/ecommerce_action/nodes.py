"""Nodes for ecommerce action processing and execution."""

from typing import Any, Type

from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.runtime import Runtime
from langgraph.types import interrupt
from pydantic import BaseModel, Field
from shared_common.schemas.ai_agent import AgentOutput, StructuredDataPart, AgentReturnReason, AgentItemCondition, AgentOutputPartKind
from shared_common.schemas.ai_agent.human_input import HumanInputRequest
from shared_common.schemas.ai_agent.human_input_schemas import CreateReturnRequestInputModel
from shared_common.schemas.ai_agent.outputs import (
    ECommerceCreateReturnOutput,
    ECommerceReturnRequestOutput,
)
from shared_common.schemas.ai_agent.schema_ids import (
    AgentOutputSchemaId,
    HumanInputSchemaId,
)
from shared_common.schemas.mcp_server.returns import (
    CreateReturnRequestInput,
    GetReturnRequestRecord,
)
from shared_common.schemas.mcp_server.enums import ReturnReasonCode, ItemCondition

from agent.core import llm
from agent.core.logger import logger
from agent.core.messages import extract_tool_call
from agent.core.output_identity import AgentOutputKey, build_output_id
from agent.integrations.mcp.gateway_provider import get_ecommerce_gateway
from agent.supervisor.ecommerce_action.prompts import (
    ECOMMERCE_ACTION_SYSTEM_PROMPT,
    RETURN_DETAILS_EXTRACTION_PROMPT,
)
from agent.supervisor.ecommerce_action.state import (
    EcommerceActionState,
    ExecuteCreateReturnUpdate,
    ActionAgentUpdate,
    ReturnRequestDetails,
)


class create_ecommerce_return_request(BaseModel):
    """Initiate/create a return request for a customer order."""

    order_id: int | None = Field(
        default=None,
        gt=0,
        description="The positive unique ID of the order to return.",
    )
    customer_id: int | None = Field(
        default=None,
        gt=0,
        description="The positive ID of the customer associated with the return.",
    )
    reason_code: AgentReturnReason | None = Field(
        default=None,
        description="The reason code for the return (change_of_mind, damaged, wrong_item, not_as_described, late_delivery).",
    )
    reason_text: str | None = Field(
        default="",
        description="Additional reason explanation text.",
    )
    item_condition: AgentItemCondition | None = Field(
        default=None,
        description="The condition of the product being returned (unopened, opened, used, damaged).",
    )
    created_by: int | None = Field(
        default=None,
        description="The user_id of the agent who operates this return request creation.",
    )





class ExtractedReturnDetails(BaseModel):
    """Extracted return request details from raw text."""

    order_id: int | None = Field(default=None, description="The positive order ID.")
    customer_id: int | None = Field(default=None, description="The positive customer ID.")
    reason_code: AgentReturnReason | None = Field(default=None, description="The reason code for the return.")
    reason_text: str | None = Field(default=None, description="Additional reason explanation text.")
    item_condition: AgentItemCondition | None = Field(default=None, description="Condition of the product being returned.")


async def _extract_return_details_from_text(llm_text: str) -> ExtractedReturnDetails:
    """Extract return request parameters from raw text using the LLM structured output."""
    try:
        structured_llm = llm.get_llm_model().with_structured_output(ExtractedReturnDetails)
        prompt_value = await RETURN_DETAILS_EXTRACTION_PROMPT.ainvoke({"user_text": llm_text})
        result = await structured_llm.ainvoke(prompt_value)
        return result or ExtractedReturnDetails()
    except Exception as error:
        logger.exception(
            "Failed to extract return details from raw text: input={!r}, error={}",
            llm_text,
            error,
        )
        raise


def _to_return_request_output(record: GetReturnRequestRecord) -> ECommerceReturnRequestOutput:
    """Convert an MCP return request model to the public AI Agent return schema."""
    return ECommerceReturnRequestOutput(
        return_request_id=record.id,
        order_id=record.order_id,
        customer_id=record.customer_id,
        status=int(record.status),
        reason_code=int(record.reason_code),
        reason_text=record.reason_text,
        item_condition=int(record.item_condition),
        requested_at=record.requested_at,
        approved_at=record.approved_at,
        rejected_at=record.rejected_at,
        received_at=record.received_at,
        closed_at=record.closed_at,
        resolution_type=int(record.resolution_type) if record.resolution_type is not None else None,
        created_by=record.created_by,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _build_structured_output(
    *,
    runtime: Runtime[None] | None,
    output_key: AgentOutputKey,
    schema_id: AgentOutputSchemaId,
    data: BaseModel,
) -> AgentOutput:
    """Build a versioned agent output payload."""
    scope = (
        runtime.execution_info.task_id
        if runtime and runtime.execution_info and runtime.execution_info.task_id
        else "default-thread"
    )
    output_id = build_output_id(
        identity_scope=scope,
        output_key=output_key,
    )
    part = StructuredDataPart(
        kind=AgentOutputPartKind.STRUCTURED_DATA,
        schema_id=schema_id.value,
        data=data.model_dump(mode="json"),
    )
    return AgentOutput(
        output_id=output_id,
        parts=[part],
    )


REASON_MAP = {
    AgentReturnReason.CHANGE_OF_MIND: ReturnReasonCode.CHANGE_OF_MIND,
    AgentReturnReason.DAMAGED: ReturnReasonCode.DAMAGED,
    AgentReturnReason.WRONG_ITEM: ReturnReasonCode.WRONG_ITEM,
    AgentReturnReason.NOT_AS_DESCRIBED: ReturnReasonCode.NOT_AS_DESCRIBED,
    AgentReturnReason.LATE_DELIVERY: ReturnReasonCode.LATE_DELIVERY,
}

CONDITION_MAP = {
    AgentItemCondition.UNOPENED: ItemCondition.UNOPENED,
    AgentItemCondition.OPENED: ItemCondition.OPENED,
    AgentItemCondition.USED: ItemCondition.USED,
    AgentItemCondition.DAMAGED: ItemCondition.DAMAGED,
}


async def action_agent(
    state: EcommerceActionState,
) -> dict[str, Any]:
    """Execute the Ecommerce Action LLM node."""
    messages = [
        SystemMessage(content=ECOMMERCE_ACTION_SYSTEM_PROMPT.template)
    ] + state.messages

    model = llm.get_llm_model().bind_tools([create_ecommerce_return_request])
    response = await model.ainvoke(messages)

    return {"messages": [response]}


async def execute_create_return(
    state: EcommerceActionState,
    runtime: Runtime[None] | None = None,
) -> dict[str, Any]:
    """Execute return request creation, triggering interrupts if arguments are missing."""
    last_message = state.messages[-1]
    args, tool_call_id = extract_tool_call(last_message, create_ecommerce_return_request)

    order_id = args.order_id if args else None
    customer_id = args.customer_id if args else None
    reason_code = args.reason_code if args else None
    reason_text = args.reason_text if args else None
    item_condition = args.item_condition if args else None
    created_by = args.created_by if args else None

    # Fallback to state values if not in tool call args
    if order_id is None:
        order_id = state.return_details.order_id
    if customer_id is None:
        customer_id = state.return_details.customer_id
    if reason_code is None:
        reason_code = state.return_details.reason_code
    if reason_text is None:
        reason_text = state.return_details.reason_text
    if item_condition is None:
        item_condition = state.return_details.item_condition
    if created_by is None:
        created_by = state.return_details.created_by

    # Trigger human input interrupt if any required information is missing
    if order_id is None or customer_id is None or reason_code is None or item_condition is None:
        request = HumanInputRequest(
            schema_id=HumanInputSchemaId.CREATE_RETURN_REQUEST_INPUT_V1.value,
            prompt="Please provide the required return details: order_id, customer_id, reason_code, item_condition.",
            input_schema=CreateReturnRequestInputModel.model_json_schema(),
        )
        user_response = interrupt(value=request.model_dump(mode="json"))

        # Process operator response
        input_model = CreateReturnRequestInputModel.model_validate(user_response)
        if input_model.llm_text:
            extracted = await _extract_return_details_from_text(input_model.llm_text)
            if extracted.order_id is not None:
                order_id = extracted.order_id
            if extracted.customer_id is not None:
                customer_id = extracted.customer_id
            if extracted.reason_code is not None:
                reason_code = extracted.reason_code
            if extracted.reason_text is not None:
                reason_text = extracted.reason_text
            if extracted.item_condition is not None:
                item_condition = extracted.item_condition
        else:
            if input_model.order_id is not None:
                order_id = input_model.order_id
            if input_model.customer_id is not None:
                customer_id = input_model.customer_id
            if input_model.reason_code is not None:
                reason_code = input_model.reason_code
            if input_model.reason_text is not None:
                reason_text = input_model.reason_text
            if input_model.item_condition is not None:
                item_condition = input_model.item_condition
            if input_model.created_by is not None:
                created_by = input_model.created_by

    # Ensure all required inputs are present now
    if order_id is None or customer_id is None or reason_code is None or item_condition is None:
        logger.error(
            "Missing return details: order_id={}, customer_id={}, reason_code={}, item_condition={}",
            order_id,
            customer_id,
            reason_code,
            item_condition,
        )
        raise ValueError("Missing required return request details.")

    # Call the MCP server create return request tool after mapping enums
    gateway = await get_ecommerce_gateway()
    mcp_input = CreateReturnRequestInput(
        order_id=order_id,
        customer_id=customer_id,
        reason_code=REASON_MAP[reason_code],
        reason_text=reason_text or "",
        item_condition=CONDITION_MAP[item_condition],
        created_by=created_by,
    )
    res = await gateway.create_ecommerce_return_request(mcp_input)

    if not res.success or res.return_request is None:
        tool_content = f"Failed to create return request: {res.error_message}"
        create_out = ECommerceCreateReturnOutput(
            success=False,
            return_request=None,
            error_message=res.error_message or "Unknown failure",
        )
    else:
        create_out = ECommerceCreateReturnOutput(
            success=True,
            return_request=_to_return_request_output(res.return_request),
            error_message=None,
        )
        tool_content = (
            f"Successfully created return request (Return ID: {res.return_request.id}) "
            f"for order {order_id}."
        )

    agent_output = _build_structured_output(
        runtime=runtime,
        output_key=AgentOutputKey.ECOMMERCE_CREATE_RETURN,
        schema_id=AgentOutputSchemaId.ECOMMERCE_CREATE_RETURN_RESULT_V1,
        data=create_out,
    )

    tool_msg = ToolMessage(
        content=tool_content,
        name="create_ecommerce_return_request",
        tool_call_id=tool_call_id or "dummy_call_id",
    )

    updated_details = ReturnRequestDetails(
        order_id=order_id,
        customer_id=customer_id,
        reason_code=reason_code,
        reason_text=reason_text or "",
        item_condition=item_condition,
        created_by=created_by,
    )

    update = ExecuteCreateReturnUpdate(
        return_details=updated_details,
        create_return_output=create_out,
        outputs=[agent_output],
        messages=[tool_msg],
    )
    return {k: v for k, v in update if k in update.model_fields_set}
