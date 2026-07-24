"""Stable identity helpers for public agent outputs."""

from enum import Enum
from uuid import NAMESPACE_URL, uuid5

from agent.core.logger import logger


class AgentOutputKey(str, Enum):
    """Identify stable public outputs independently of graph topology."""

    POLICY_QA_FINAL_RESPONSE = "policy_qa.final_response"
    RAG_FILE_IMPORT_RESULT = "rag_file_import.result"
    ECOMMERCE_USER = "ecommerce.user"
    ECOMMERCE_ORDERS = "ecommerce.orders"
    ECOMMERCE_ORDER_DETAILS = "ecommerce.order_details"
    ECOMMERCE_RETURNS_BY_ORDER = "ecommerce.returns_by_order"
    ECOMMERCE_RETURNS_BY_CUSTOMER = "ecommerce.returns_by_customer"
    ECOMMERCE_CREATE_RETURN = "ecommerce.create_return"
    ECOMMERCE_QUERY_FINAL_RESPONSE = "ecommerce_query.final_response"
    ECOMMERCE_ACTION_FINAL_RESPONSE = "ecommerce_action.final_response"


AGENT_OUTPUT_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "agentic-resolution-platform/agent-output/v1",
)


def build_output_id(
    *,
    identity_scope: str,
    output_key: AgentOutputKey,
    subject_id: str | None = None,
) -> str:
    """Build a deterministic UUID string for one scoped logical agent output."""
    if not isinstance(output_key, AgentOutputKey):
        logger.error("Agent output identity requires an AgentOutputKey")
        raise TypeError("output_key must be an AgentOutputKey")

    identity_parts = [identity_scope, output_key.value]
    if subject_id is not None:
        identity_parts.append(subject_id)
    return str(uuid5(AGENT_OUTPUT_NAMESPACE, ":".join(identity_parts)))
