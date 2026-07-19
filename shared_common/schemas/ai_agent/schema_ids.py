"""Stable schema identifiers for structured AI Agent outputs."""

from enum import Enum


class HumanInputSchemaId(str, Enum):
    """Identify versioned human input schemas for interrupts."""

    GET_USER_INPUT_V1 = "human_input.get_user.v1"
    GET_ORDERS_INPUT_V1 = "human_input.get_orders.v1"
    GET_ORDER_DETAILS_INPUT_V1 = "human_input.get_order_details.v1"
    GET_RETURNS_BY_ORDER_INPUT_V1 = "human_input.get_returns_by_order.v1"
    GET_RETURNS_BY_CUSTOMER_INPUT_V1 = "human_input.get_returns_by_customer.v1"
    CREATE_RETURN_REQUEST_INPUT_V1 = "human_input.create_return_request.v1"


class AgentOutputSchemaId(str, Enum):
    """Identify versioned structured agent output schemas."""

    RAG_FILE_IMPORT_RESULT_V1 = "rag.file_import.result.v1"
    ECOMMERCE_USER_RESULT_V1 = "ecommerce.user_result.v1"
    ECOMMERCE_ORDERS_RESULT_V1 = "ecommerce.orders_result.v1"
    ECOMMERCE_ORDER_DETAILS_RESULT_V1 = "ecommerce.order_details_result.v1"
    ECOMMERCE_RETURNS_BY_ORDER_RESULT_V1 = "ecommerce.returns_by_order_result.v1"
    ECOMMERCE_RETURNS_BY_CUSTOMER_RESULT_V1 = (
        "ecommerce.returns_by_customer_result.v1"
    )
    ECOMMERCE_CREATE_RETURN_RESULT_V1 = "ecommerce.create_return_result.v1"
