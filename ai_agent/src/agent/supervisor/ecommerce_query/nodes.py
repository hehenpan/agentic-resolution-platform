"""Nodes for ecommerce query processing and retrieval."""

from typing import Any, Type, TypeVar

from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.runtime import Runtime
from langgraph.types import interrupt
from pydantic import BaseModel, Field
from shared_common.schemas.ai_agent import AgentOutput, StructuredDataPart
from shared_common.schemas.ai_agent.human_input import HumanInputRequest
from shared_common.schemas.ai_agent.human_input_schemas import (
    GetOrdersByEmailInputModel,
    GetUserByEmailInputModel,
)
from shared_common.schemas.ai_agent.outputs import (
    ECommerceOrderOutput,
    ECommerceOrdersOutput,
    ECommerceUserOutput,
)
from shared_common.schemas.ai_agent.schema_ids import (
    AgentOutputSchemaId,
    HumanInputSchemaId,
)
from shared_common.schemas.mcp_server.order import GetECommerceOrdersRequest
from shared_common.schemas.mcp_server.user import GetECommerceUserRequest

from agent.core import llm
from agent.core.logger import logger
from agent.core.output_identity import AgentOutputKey, build_output_id
from agent.integrations.mcp.gateway_provider import get_ecommerce_gateway
from agent.supervisor.ecommerce_query.prompts import (
    ECOMMERCE_QUERY_SYSTEM_PROMPT,
    PARAMETER_EXTRACTION_PROMPT,
)
from agent.supervisor.ecommerce_query.state import (
    EcommerceQueryState,
    RetrieveOrdersUpdate,
    RetrieveUserUpdate,
)


# Define tool schemas for LLM tool binding
class get_ecommerce_user(BaseModel):
    """Fetch registered customer information by email."""
    email: str | None = Field(default=None, description="Customer email address to lookup.")

class get_ecommerce_orders(BaseModel):
    """Fetch orders associated with a customer email."""
    email: str | None = Field(default=None, description="Customer email address to list orders for.")


T = TypeVar("T", bound=BaseModel)


def extract_tool_call(
    message: Any,
    tool_model: Type[T],
) -> tuple[T | None, str | None]:
    """Extract tool call arguments and ID matching the tool model class name."""
    if not hasattr(message, "tool_calls") or not message.tool_calls:
        return None, None
    for tc in message.tool_calls:
        if tc["name"] == tool_model.__name__:
            parsed_args = tool_model.model_validate(tc["args"])
            return parsed_args, tc.get("id")
    return None, None


class ExtractedEmail(BaseModel):
    """Extracted customer email address from raw text."""
    email: str | None = Field(
        default=None,
        description="The customer email address extracted from the input text, or null if none is found."
    )


async def _extract_email_from_text(llm_text: str) -> str | None:
    """Extract email address from raw text using the LLM structured output."""
    structured_llm = llm.get_llm_model().with_structured_output(ExtractedEmail)
    prompt_value = await PARAMETER_EXTRACTION_PROMPT.ainvoke({"user_text": llm_text})
    result = await structured_llm.ainvoke(prompt_value)
    return result.email if result else None


async def query_agent(state: EcommerceQueryState) -> dict[str, Any]:
    """Execute LLM query reasoning with bound tools."""
    model = llm.get_llm_model().bind_tools([get_ecommerce_user, get_ecommerce_orders])
    system_msg = SystemMessage(content=ECOMMERCE_QUERY_SYSTEM_PROMPT.format())
    messages = [system_msg] + state.messages
    response = await model.ainvoke(messages)
    return {"messages": [response]}


async def retrieve_user(
    state: EcommerceQueryState,
    runtime: Runtime[None] | None = None,
) -> dict[str, Any]:
    """Retrieve ecommerce user details, triggering interrupts if arguments are missing."""
    last_message = state.messages[-1]
    args, tool_call_id = extract_tool_call(last_message, get_ecommerce_user)
    email = args.email if args else None

    if not email:
        email = state.email

    # Trigger human input interrupt if email is not provided
    if not email:
        request = HumanInputRequest(
            schema_id=HumanInputSchemaId.GET_USER_INPUT_V1.value,
            prompt="Please provide the customer email address to fetch user details.",
            input_schema=GetUserByEmailInputModel.model_json_schema(),
        )
        user_response = interrupt(value=request.model_dump(mode="json"))

        # Process the operator response
        input_model = GetUserByEmailInputModel.model_validate(user_response)
        if input_model.llm_text:
            email = await _extract_email_from_text(input_model.llm_text)
            if not email:
                logger.error(
                    "Failed to extract email from raw text: {}",
                    input_model.llm_text,
                )
                raise ValueError(
                    f"Could not extract email from text: {input_model.llm_text}"
                )
        else:
            email = input_model.email

    if not email:
        logger.error("No customer email determined for user lookup.")
        raise ValueError("Customer email is required for user lookup.")

    gateway = await get_ecommerce_gateway()
    user_res = await gateway.get_ecommerce_user(GetECommerceUserRequest(email=email))

    if not user_res.exists or user_res.user_id is None:
        tool_content = f"No customer found with email: {email}"
        user_out = ECommerceUserOutput(
            exists=False,
            user_id=None,
            email=email,
            user_name=None,
        )
    else:
        user_out = ECommerceUserOutput(
            exists=True,
            user_id=user_res.user_id,
            email=user_res.email or email,
            user_name=user_res.user_name,
        )
        tool_content = f"Retrieved customer details for email {email} (User ID: {user_out.user_id})."

    task_id = "default-task-id"
    if runtime and runtime.execution_info and runtime.execution_info.task_id:
        task_id = runtime.execution_info.task_id

    agent_output = AgentOutput(
        output_id=build_output_id(
            identity_scope=task_id,
            output_key=AgentOutputKey.ECOMMERCE_USER,
        ),
        parts=[
            StructuredDataPart(
                schema_id=AgentOutputSchemaId.ECOMMERCE_USER_RESULT_V1.value,
                data=user_out.model_dump(mode="json"),
            )
        ],
    )

    # ToolMessage is required to resolve the LLM's Tool Call and 
    # avoid API sequencing errors or infinite loops.
    tool_msg = ToolMessage(
        content=tool_content,
        name="get_ecommerce_user",
        tool_call_id=tool_call_id or "dummy_call_id",
    )

    update = RetrieveUserUpdate(
        user_output=user_out,
        outputs=[agent_output],
        messages=[tool_msg],
    )
    return {k: v for k, v in update if k in update.model_fields_set}


async def retrieve_orders(
    state: EcommerceQueryState,
    runtime: Runtime[None] | None = None,
) -> dict[str, Any]:
    """Retrieve ecommerce order details, triggering interrupts if arguments are missing."""
    last_message = state.messages[-1]
    args, tool_call_id = extract_tool_call(last_message, get_ecommerce_orders)
    email = args.email if args else None

    if not email:
        email = state.email

    # Trigger human input interrupt if email is not provided
    if not email:
        request = HumanInputRequest(
            schema_id=HumanInputSchemaId.GET_ORDERS_INPUT_V1.value,
            prompt="Please provide the customer email address to query orders list.",
            input_schema=GetOrdersByEmailInputModel.model_json_schema(),
        )
        user_response = interrupt(value=request.model_dump(mode="json"))

        # Process the operator response
        input_model = GetOrdersByEmailInputModel.model_validate(user_response)
        if input_model.llm_text:
            email = await _extract_email_from_text(input_model.llm_text)
            if not email:
                logger.error(
                    "Failed to extract email from raw text: {}",
                    input_model.llm_text,
                )
                raise ValueError(
                    f"Could not extract email from text: {input_model.llm_text}"
                )
        else:
            email = input_model.email

    if not email:
        logger.error("No customer email determined for orders lookup.")
        raise ValueError("Customer email is required for orders lookup.")

    gateway = await get_ecommerce_gateway()
    orders_res = await gateway.get_ecommerce_orders(GetECommerceOrdersRequest(email=email))

    if not orders_res.orders:
        tool_content = f"No orders found for customer: {email}"
        orders_out = ECommerceOrdersOutput(
            customer_email=email,
            orders=[],
        )
    else:
        orders_out = ECommerceOrdersOutput(
            customer_email=email,
            orders=[
                ECommerceOrderOutput(
                    order_id=order.order_id,
                    user_id=order.user_id,
                    email=order.email,
                    status=int(order.status),
                    total_amount=order.total_amount,
                    created_ts=order.created_ts,
                )
                for order in orders_res.orders
            ],
        )
        tool_content = f"Retrieved {len(orders_out.orders)} orders for customer: {email}."

    task_id = "default-task-id"
    if runtime and runtime.execution_info and runtime.execution_info.task_id:
        task_id = runtime.execution_info.task_id

    agent_output = AgentOutput(
        output_id=build_output_id(
            identity_scope=task_id,
            output_key=AgentOutputKey.ECOMMERCE_ORDERS,
        ),
        parts=[
            StructuredDataPart(
                schema_id=AgentOutputSchemaId.ECOMMERCE_ORDERS_RESULT_V1.value,
                data=orders_out.model_dump(mode="json"),
            )
        ],
    )

    # ToolMessage is required to resolve the LLM's Tool Call and 
    # avoid API sequencing errors or infinite loops.
    tool_msg = ToolMessage(
        content=tool_content,
        name="get_ecommerce_orders",
        tool_call_id=tool_call_id or "dummy_call_id",
    )

    update = RetrieveOrdersUpdate(
        orders_output=orders_out,
        outputs=[agent_output],
        messages=[tool_msg],
    )
    return {k: v for k, v in update if k in update.model_fields_set}
