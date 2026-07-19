"""Structured input parameters for human interrupt requests and responses."""

from pydantic import BaseModel, Field


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
