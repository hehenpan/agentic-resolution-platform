"""Tests for public ecommerce output contracts exposed by AI Agent."""

from shared_common.schemas.ai_agent.outputs import (
    ECommerceReturnRequestOutput,
    ECommerceReturnsByOrderOutput,
)
from shared_common.schemas.ai_agent.schema_ids import AgentOutputSchemaId


def test_returns_by_order_public_schema_round_trips_without_mcp_field_names() -> None:
    output = ECommerceReturnsByOrderOutput(
        order_id=9001,
        return_request=ECommerceReturnRequestOutput(
            return_request_id=7001,
            order_id=9001,
            customer_id=3001,
            status=0,
            reason_code=1,
            reason_text="Damaged package",
            item_condition=3,
            requested_at=1778900100,
            created_at=1778900100,
            updated_at=1778900200,
        ),
    )

    payload = output.model_dump(mode="json")

    assert (
        AgentOutputSchemaId.ECOMMERCE_RETURNS_BY_ORDER_RESULT_V1.value
        == "ecommerce.returns_by_order_result.v1"
    )
    assert payload["return_request"]["return_request_id"] == 7001
    assert "id" not in payload["return_request"]
    assert ECommerceReturnsByOrderOutput.model_validate(payload) == output
