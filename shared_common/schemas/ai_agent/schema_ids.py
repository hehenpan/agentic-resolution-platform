"""Stable schema identifiers for structured AI Agent outputs."""

from enum import Enum


class HumanInputSchemaId(str, Enum):
    """Identify versioned human input schemas for interrupts."""

    GET_USER_INPUT_V1 = "human_input.get_user.v1"
    GET_ORDERS_INPUT_V1 = "human_input.get_orders.v1"


class AgentOutputSchemaId(str, Enum):
    """Identify versioned structured agent output schemas."""

    RAG_FILE_IMPORT_RESULT_V1 = "rag.file_import.result.v1"
    ECOMMERCE_USER_RESULT_V1 = "ecommerce.user_result.v1"
    ECOMMERCE_ORDERS_RESULT_V1 = "ecommerce.orders_result.v1"
