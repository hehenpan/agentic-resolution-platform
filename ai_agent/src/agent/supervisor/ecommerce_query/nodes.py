"""Nodes for ecommerce query processing and retrieval."""

from typing import Any, Type, TypeVar

from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.runtime import Runtime
from langgraph.types import interrupt
from pydantic import BaseModel, Field
from shared_common.schemas.ai_agent import (
    AgentOutput,
    AgentOutputPartKind,
    StructuredDataPart,
    TextPart,
)
from shared_common.schemas.ai_agent.human_input import HumanInputRequest
from shared_common.schemas.ai_agent.human_input_schemas import (
    GetOrderDetailsByOrderIdInputModel,
    GetOrdersByEmailInputModel,
    GetReturnsByCustomerIdInputModel,
    GetReturnsByOrderIdInputModel,
    GetUserByEmailInputModel,
)
from shared_common.schemas.ai_agent.outputs import (
    ECommerceOrderDetailsOutput,
    ECommerceOrderItemOutput,
    ECommerceOrderOutput,
    ECommerceOrdersOutput,
    ECommerceReturnRequestOutput,
    ECommerceReturnsByCustomerOutput,
    ECommerceReturnsByOrderOutput,
    ECommerceUserOutput,
)
from shared_common.schemas.ai_agent.schema_ids import (
    AgentOutputSchemaId,
    HumanInputSchemaId,
)
from shared_common.schemas.mcp_server.order import (
    GetECommerceOrderDetailsRequest,
    GetECommerceOrdersRequest,
)
from shared_common.schemas.mcp_server.returns import (
    GetReturnRequestRecord,
    GetReturnRequestsByCustomerRequest,
    GetReturnRequestsByOrderRequest,
)
from shared_common.schemas.mcp_server.user import GetECommerceUserRequest

from agent.core import llm
from agent.core.logger import logger
from agent.core.messages import extract_tool_call
from agent.core.output_identity import AgentOutputKey, build_output_id
from agent.integrations.mcp.gateway_provider import get_ecommerce_gateway
from agent.supervisor.ecommerce_query.prompts import (
    CUSTOMER_ID_EXTRACTION_PROMPT,
    ECOMMERCE_QUERY_SYSTEM_PROMPT,
    ORDER_ID_EXTRACTION_PROMPT,
    PARAMETER_EXTRACTION_PROMPT,
)
from agent.supervisor.ecommerce_query.state import (
    EcommerceQueryState,
    RetrieveOrderDetailsUpdate,
    RetrieveOrdersUpdate,
    RetrieveReturnsByCustomerUpdate,
    RetrieveReturnsByOrderUpdate,
    RetrieveUserUpdate,
)


# Define tool schemas for LLM tool binding
class get_ecommerce_user(BaseModel):
    """Fetch registered customer information by email."""
    email: str | None = Field(default=None, description="Customer email address to lookup.")

class get_ecommerce_orders(BaseModel):
    """Fetch orders associated with a customer email."""
    email: str | None = Field(default=None, description="Customer email address to list orders for.")


class get_ecommerce_order_details(BaseModel):
    """Fetch order details by order ID."""

    order_id: int | None = Field(
        default=None,
        gt=0,
        description="Positive order identifier to retrieve details for.",
    )


class get_return_requests_by_order(BaseModel):
    """Fetch return request details by order ID."""

    order_id: int | None = Field(
        default=None,
        gt=0,
        description="Positive order identifier to retrieve return details for.",
    )


class get_return_requests_by_customer(BaseModel):
    """Fetch return request details by customer ID."""

    customer_id: int | None = Field(
        default=None,
        gt=0,
        description="Positive customer identifier to retrieve return details for.",
    )


T = TypeVar("T", bound=BaseModel)


class ExtractedEmail(BaseModel):
    """Extracted customer email address from raw text."""
    email: str | None = Field(
        default=None,
        description="The customer email address extracted from the input text, or null if none is found."
    )


class ExtractedOrderId(BaseModel):
    """Extracted order identifier from raw text."""

    order_id: int | None = Field(
        default=None,
        gt=0,
        description="The positive order identifier extracted from the input text.",
    )


class ExtractedCustomerId(BaseModel):
    """Extracted customer identifier from raw text."""

    customer_id: int | None = Field(
        default=None,
        gt=0,
        description="The positive customer identifier extracted from the input text.",
    )


async def _extract_email_from_text(llm_text: str) -> str | None:
    """Extract email address from raw text using the LLM structured output."""
    try:
        structured_llm = llm.get_llm_model().with_structured_output(ExtractedEmail)
        prompt_value = await PARAMETER_EXTRACTION_PROMPT.ainvoke({"user_text": llm_text})
        result = await structured_llm.ainvoke(prompt_value)
        return result.email if result else None
    except Exception as error:
        logger.exception(
            "Failed to extract email from raw text: input={!r}, error={}",
            llm_text,
            error,
        )
        raise


async def _extract_order_id_from_text(llm_text: str) -> int | None:
    """Extract a positive order identifier from raw text using structured output."""
    try:
        structured_llm = llm.get_llm_model().with_structured_output(ExtractedOrderId)
        prompt_value = await ORDER_ID_EXTRACTION_PROMPT.ainvoke({"user_text": llm_text})
        result = await structured_llm.ainvoke(prompt_value)
        return result.order_id if result else None
    except Exception as error:
        logger.exception(
            "Failed to extract order ID from raw text: input={!r}, error={}",
            llm_text,
            error,
        )
        raise


async def _extract_customer_id_from_text(llm_text: str) -> int | None:
    """Extract a positive customer identifier from raw text using structured output."""
    try:
        structured_llm = llm.get_llm_model().with_structured_output(ExtractedCustomerId)
        prompt_value = await CUSTOMER_ID_EXTRACTION_PROMPT.ainvoke({"user_text": llm_text})
        result = await structured_llm.ainvoke(prompt_value)
        return result.customer_id if result else None
    except Exception as error:
        logger.exception(
            "Failed to extract customer ID from raw text: input={!r}, error={}",
            llm_text,
            error,
        )
        raise


def _resolve_task_id(runtime: Runtime[None] | None) -> str:
    """Resolve the current run task identifier used for stable output IDs."""
    if runtime and runtime.execution_info and runtime.execution_info.task_id:
        return runtime.execution_info.task_id
    return "default-task-id"


def _to_order_output(order: Any) -> ECommerceOrderOutput:
    """Convert an MCP order-like model to the public AI Agent order schema."""
    return ECommerceOrderOutput(
        order_id=order.order_id,
        user_id=order.user_id,
        email=order.email,
        status=int(order.status),
        total_amount=order.total_amount,
        created_ts=order.created_ts,
    )


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
    subject_id: str | None = None,
) -> AgentOutput:
    """Build a stable structured public output for the current graph run."""
    return AgentOutput(
        output_id=build_output_id(
            identity_scope=_resolve_task_id(runtime),
            output_key=output_key,
            subject_id=subject_id,
        ),
        parts=[
            StructuredDataPart(
                schema_id=schema_id.value,
                data=data.model_dump(mode="json"),
            )
        ],
    )


async def query_agent(state: EcommerceQueryState) -> dict[str, Any]:
    """Execute LLM query reasoning with bound tools."""
    model = llm.get_llm_model().bind_tools(
        [
            get_ecommerce_user,
            get_ecommerce_orders,
            get_ecommerce_order_details,
            get_return_requests_by_order,
            get_return_requests_by_customer,
        ]
    )
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

    agent_output = _build_structured_output(
        runtime=runtime,
        output_key=AgentOutputKey.ECOMMERCE_USER,
        schema_id=AgentOutputSchemaId.ECOMMERCE_USER_RESULT_V1,
        data=user_out,
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
                _to_order_output(order) for order in orders_res.orders
            ],
        )
        tool_content = f"Retrieved {len(orders_out.orders)} orders for customer: {email}."

    agent_output = _build_structured_output(
        runtime=runtime,
        output_key=AgentOutputKey.ECOMMERCE_ORDERS,
        schema_id=AgentOutputSchemaId.ECOMMERCE_ORDERS_RESULT_V1,
        data=orders_out,
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


async def retrieve_order_details(
    state: EcommerceQueryState,
    runtime: Runtime[None] | None = None,
) -> dict[str, Any]:
    """Retrieve ecommerce order details, triggering interrupts if arguments are missing."""
    last_message = state.messages[-1]
    args, tool_call_id = extract_tool_call(last_message, get_ecommerce_order_details)
    order_id = args.order_id if args else None

    if not order_id:
        order_id = state.order_id

    if not order_id:
        request = HumanInputRequest(
            schema_id=HumanInputSchemaId.GET_ORDER_DETAILS_INPUT_V1.value,
            prompt="Please provide the order ID to fetch order details.",
            input_schema=GetOrderDetailsByOrderIdInputModel.model_json_schema(),
        )
        user_response = interrupt(value=request.model_dump(mode="json"))

        input_model = GetOrderDetailsByOrderIdInputModel.model_validate(user_response)
        if input_model.llm_text:
            order_id = await _extract_order_id_from_text(input_model.llm_text)
            if not order_id:
                logger.error(
                    "Failed to extract order ID from raw text: {}",
                    input_model.llm_text,
                )
                raise ValueError(
                    f"Could not extract order ID from text: {input_model.llm_text}"
                )
        else:
            order_id = input_model.order_id

    if not order_id:
        logger.error("No order ID determined for order details lookup.")
        raise ValueError("Order ID is required for order details lookup.")

    gateway = await get_ecommerce_gateway()
    order_res = await gateway.get_ecommerce_order_details(
        GetECommerceOrderDetailsRequest(order_id=order_id)
    )

    if not order_res.exists or order_res.order is None:
        tool_content = f"No order found with order ID: {order_id}"
        order_details_out = ECommerceOrderDetailsOutput(
            exists=False,
            order=None,
            items=[],
        )
    else:
        order_details_out = ECommerceOrderDetailsOutput(
            exists=True,
            order=_to_order_output(order_res.order),
            items=[
                ECommerceOrderItemOutput(
                    item_id=item.item_id,
                    sku_id=item.sku_id,
                    sku_code=item.sku_code,
                    name=item.name,
                    quantity=item.quantity,
                    price=item.price,
                )
                for item in order_res.items
            ],
        )
        tool_content = (
            f"Retrieved order details for order ID {order_id} "
            f"with {len(order_details_out.items)} items."
        )

    agent_output = _build_structured_output(
        runtime=runtime,
        output_key=AgentOutputKey.ECOMMERCE_ORDER_DETAILS,
        schema_id=AgentOutputSchemaId.ECOMMERCE_ORDER_DETAILS_RESULT_V1,
        data=order_details_out,
        subject_id=str(order_id),
    )

    tool_msg = ToolMessage(
        content=tool_content,
        name="get_ecommerce_order_details",
        tool_call_id=tool_call_id or "dummy_call_id",
    )

    update = RetrieveOrderDetailsUpdate(
        order_id=order_id,
        order_details_output=order_details_out,
        outputs=[agent_output],
        messages=[tool_msg],
    )
    return {k: v for k, v in update if k in update.model_fields_set}


async def retrieve_returns_by_order(
    state: EcommerceQueryState,
    runtime: Runtime[None] | None = None,
) -> dict[str, Any]:
    """Retrieve return details for one order, interrupting if order ID is missing."""
    last_message = state.messages[-1]
    args, tool_call_id = extract_tool_call(last_message, get_return_requests_by_order)
    order_id = args.order_id if args else None

    if not order_id:
        order_id = state.order_id

    if not order_id:
        request = HumanInputRequest(
            schema_id=HumanInputSchemaId.GET_RETURNS_BY_ORDER_INPUT_V1.value,
            prompt="Please provide the order ID to fetch return details.",
            input_schema=GetReturnsByOrderIdInputModel.model_json_schema(),
        )
        user_response = interrupt(value=request.model_dump(mode="json"))

        input_model = GetReturnsByOrderIdInputModel.model_validate(user_response)
        if input_model.llm_text:
            order_id = await _extract_order_id_from_text(input_model.llm_text)
            if not order_id:
                logger.error(
                    "Failed to extract order ID from raw text: {}",
                    input_model.llm_text,
                )
                raise ValueError(
                    f"Could not extract order ID from text: {input_model.llm_text}"
                )
        else:
            order_id = input_model.order_id

    if not order_id:
        logger.error("No order ID determined for return-by-order lookup.")
        raise ValueError("Order ID is required for return-by-order lookup.")

    gateway = await get_ecommerce_gateway()
    returns_res = await gateway.get_return_requests_by_order(
        GetReturnRequestsByOrderRequest(order_id=order_id)
    )

    if returns_res.returns is None:
        tool_content = f"No return request found for order ID: {order_id}"
        returns_out = ECommerceReturnsByOrderOutput(
            order_id=order_id,
            return_request=None,
        )
    else:
        return_request = _to_return_request_output(returns_res.returns)
        returns_out = ECommerceReturnsByOrderOutput(
            order_id=order_id,
            return_request=return_request,
        )
        tool_content = f"Retrieved return request {return_request.return_request_id} for order ID {order_id}."

    agent_output = _build_structured_output(
        runtime=runtime,
        output_key=AgentOutputKey.ECOMMERCE_RETURNS_BY_ORDER,
        schema_id=AgentOutputSchemaId.ECOMMERCE_RETURNS_BY_ORDER_RESULT_V1,
        data=returns_out,
        subject_id=str(order_id),
    )

    tool_msg = ToolMessage(
        content=tool_content,
        name="get_return_requests_by_order",
        tool_call_id=tool_call_id or "dummy_call_id",
    )

    update = RetrieveReturnsByOrderUpdate(
        order_id=order_id,
        returns_by_order_output=returns_out,
        outputs=[agent_output],
        messages=[tool_msg],
    )
    return {k: v for k, v in update if k in update.model_fields_set}


async def retrieve_returns_by_customer(
    state: EcommerceQueryState,
    runtime: Runtime[None] | None = None,
) -> dict[str, Any]:
    """Retrieve return details for one customer, interrupting if customer ID is missing."""
    last_message = state.messages[-1]
    args, tool_call_id = extract_tool_call(
        last_message,
        get_return_requests_by_customer,
    )
    customer_id = args.customer_id if args else None

    if not customer_id:
        customer_id = state.customer_id

    if not customer_id:
        request = HumanInputRequest(
            schema_id=HumanInputSchemaId.GET_RETURNS_BY_CUSTOMER_INPUT_V1.value,
            prompt="Please provide the customer ID to fetch return details.",
            input_schema=GetReturnsByCustomerIdInputModel.model_json_schema(),
        )
        user_response = interrupt(value=request.model_dump(mode="json"))

        input_model = GetReturnsByCustomerIdInputModel.model_validate(user_response)
        if input_model.llm_text:
            customer_id = await _extract_customer_id_from_text(input_model.llm_text)
            if not customer_id:
                logger.error(
                    "Failed to extract customer ID from raw text: {}",
                    input_model.llm_text,
                )
                raise ValueError(
                    f"Could not extract customer ID from text: {input_model.llm_text}"
                )
        else:
            customer_id = input_model.customer_id

    if not customer_id:
        logger.error("No customer ID determined for return-by-customer lookup.")
        raise ValueError("Customer ID is required for return-by-customer lookup.")

    gateway = await get_ecommerce_gateway()
    returns_res = await gateway.get_return_requests_by_customer(
        GetReturnRequestsByCustomerRequest(customer_id=customer_id)
    )
    returns_out = ECommerceReturnsByCustomerOutput(
        customer_id=customer_id,
        returns=[_to_return_request_output(record) for record in returns_res.returns],
    )

    if returns_out.returns:
        tool_content = (
            f"Retrieved {len(returns_out.returns)} return requests "
            f"for customer ID {customer_id}."
        )
    else:
        tool_content = f"No return requests found for customer ID: {customer_id}"

    agent_output = _build_structured_output(
        runtime=runtime,
        output_key=AgentOutputKey.ECOMMERCE_RETURNS_BY_CUSTOMER,
        schema_id=AgentOutputSchemaId.ECOMMERCE_RETURNS_BY_CUSTOMER_RESULT_V1,
        data=returns_out,
        subject_id=str(customer_id),
    )

    tool_msg = ToolMessage(
        content=tool_content,
        name="get_return_requests_by_customer",
        tool_call_id=tool_call_id or "dummy_call_id",
    )

    update = RetrieveReturnsByCustomerUpdate(
        customer_id=customer_id,
        returns_by_customer_output=returns_out,
        outputs=[agent_output],
        messages=[tool_msg],
    )
    return {k: v for k, v in update if k in update.model_fields_set}


async def build_query_response(
    state: EcommerceQueryState,
    runtime: Runtime[None] | None = None,
) -> dict[str, Any]:
    """Extract final text response from the latest LLM message and publish it as AgentOutput."""
    execution_info = runtime.execution_info if runtime else None
    task_id = execution_info.task_id if execution_info else "default-task-id"

    latest_ai_msg = None
    for msg in reversed(state.messages):
        if msg.type == "ai":
            latest_ai_msg = msg
            break

    response_text = ""
    if latest_ai_msg:
        if isinstance(latest_ai_msg.content, list):
            response_text = "".join(
                part.get("text", "")
                for part in latest_ai_msg.content
                if isinstance(part, dict) and "text" in part
            )
        else:
            response_text = str(latest_ai_msg.content)

    if not response_text:
        response_text = "Turn completed."

    agent_output = AgentOutput(
        output_id=build_output_id(
            identity_scope=task_id,
            output_key=AgentOutputKey.ECOMMERCE_QUERY_FINAL_RESPONSE,
        ),
        parts=[
            TextPart(
                kind=AgentOutputPartKind.TEXT,
                text=response_text,
            )
        ],
    )

    return {
        "outputs": [agent_output]
    }

