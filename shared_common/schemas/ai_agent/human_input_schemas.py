"""Structured input parameters for human interrupt requests and responses."""

from pydantic import BaseModel, Field
from shared_common.schemas.ai_agent.enums import AgentItemCondition, AgentReturnReason


class GetUserByEmailInputModel(BaseModel):
    """Pydantic schema representing the expected user lookup parameter fields."""

    email: str | None = Field(
        default=None,
        description="Structured customer email address used to lookup user details.",
    )
    llm_text: str | None = Field(
        default=None,
        description="Raw natural language text response containing the customer email details.",
    )


class GetOrdersByEmailInputModel(BaseModel):
    """Pydantic schema representing the expected orders lookup parameter fields."""

    email: str | None = Field(
        default=None,
        description="Structured customer email address used to query list of matching orders.",
    )
    llm_text: str | None = Field(
        default=None,
        description="Raw natural language text response containing customer email details.",
    )


class GetOrderDetailsByOrderIdInputModel(BaseModel):
    """Pydantic schema representing the expected order-details parameter fields."""

    order_id: int | None = Field(
        default=None,
        gt=0,
        description="Structured positive order identifier used to lookup order details.",
    )
    llm_text: str | None = Field(
        default=None,
        description="Raw natural language text response containing the order identifier.",
    )


class GetReturnsByOrderIdInputModel(BaseModel):
    """Pydantic schema representing the expected return-by-order parameter fields."""

    order_id: int | None = Field(
        default=None,
        gt=0,
        description="Structured positive order identifier used to lookup return details.",
    )
    llm_text: str | None = Field(
        default=None,
        description="Raw natural language text response containing the order identifier.",
    )


class GetReturnsByCustomerIdInputModel(BaseModel):
    """Pydantic schema representing the expected return-by-customer parameter fields."""

    customer_id: int | None = Field(
        default=None,
        gt=0,
        description="Structured positive customer identifier used to lookup return details.",
    )
    llm_text: str | None = Field(
        default=None,
        description="Raw natural language text response containing the customer identifier.",
    )


class CreateReturnRequestInputModel(BaseModel):
    """Pydantic schema representing the expected parameters to create a return request."""

    order_id: int | None = Field(
        default=None,
        gt=0,
        description="Structured positive order identifier to return.",
    )
    customer_id: int | None = Field(
        default=None,
        gt=0,
        description="Structured positive customer identifier associated with the return.",
    )
    reason_code: AgentReturnReason | None = Field(
        default=None,
        description="Reason code for the return (CHANGE_OF_MIND, DAMAGED, WRONG_ITEM, NOT_AS_DESCRIBED, LATE_DELIVERY).",
    )
    reason_text: str | None = Field(
        default=None,
        description="Additional reason explanation text.",
    )
    item_condition: AgentItemCondition | None = Field(
        default=None,
        description="Condition of the product (UNOPENED, OPENED, USED, DAMAGED).",
    )
    created_by: int | None = Field(
        default=None,
        description="The user_id of the agent who operates this return request creation.",
    )
    llm_text: str | None = Field(
        default=None,
        description="Raw natural language text response containing return details.",
    )

