"""Public output schemas produced by AI Agent runs."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, JsonValue

from shared_common.schemas.ai_agent.enums import (
    AgentOutputPartKind,
    AgentSourceType,
)


class TextPart(BaseModel):
    """Represent a textual part of a public agent output."""

    kind: Literal[AgentOutputPartKind.TEXT] = Field(
        default=AgentOutputPartKind.TEXT,
        description="Discriminator identifying a human-readable text output part.",
    )
    text: str = Field(
        description="Human-readable response text presented to the consumer."
    )


class StructuredDataPart(BaseModel):
    """Represent versioned JSON data in a public agent output."""

    kind: Literal[AgentOutputPartKind.STRUCTURED_DATA] = Field(
        default=AgentOutputPartKind.STRUCTURED_DATA,
        description="Discriminator identifying a versioned structured-data output part.",
    )
    schema_id: str = Field(
        description="Stable versioned identifier describing the structure of data."
    )
    data: JsonValue = Field(
        description="JSON-compatible payload conforming to the identified schema."
    )


class SourceReference(BaseModel):
    """Represent a source used to produce an agent output."""

    source_id: str = Field(
        description="Stable provider-specific identifier for the referenced source."
    )
    source_type: AgentSourceType = Field(
        description="Category of system that supplied the source."
    )
    title: str | None = Field(
        default=None,
        description="Optional human-readable label for the source.",
    )
    uri: str | None = Field(
        default=None,
        description="Optional resolvable location of the source.",
    )
    attributes: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Additional JSON-compatible source metadata and evidence.",
    )


class SourcesPart(BaseModel):
    """Represent source references embedded in an agent output."""

    kind: Literal[AgentOutputPartKind.SOURCES] = Field(
        default=AgentOutputPartKind.SOURCES,
        description="Discriminator identifying a collection of source references.",
    )
    sources: list[SourceReference] = Field(
        description="Sources used to produce or support the agent output."
    )


class ECommerceUserOutput(BaseModel):
    """Represent the structured data output for a retrieved ecommerce user."""

    exists: bool = Field(
        description="Whether the customer was successfully found in the database."
    )
    user_id: int | None = Field(
        default=None,
        description="The unique database identifier of the customer, or null if not found."
    )
    email: str = Field(
        description="The registered email address of the customer."
    )
    user_name: str | None = Field(
        default=None,
        description="The username or full name of the customer."
    )


class ECommerceOrderOutput(BaseModel):
    """Represent a single ecommerce order in public agent output."""

    order_id: int = Field(
        description="The unique order identifier."
    )
    user_id: int = Field(
        description="The unique customer identifier that owns the order."
    )
    email: str = Field(
        description="The customer email address associated with the order."
    )
    status: int = Field(
        ge=0,
        le=4,
        description=(
            "Order status code exposed by the agent contract "
            "(0: PENDING, 1: PAID, 2: SHIPPED, 3: COMPLETED, 4: CANCELLED)."
        ),
    )
    total_amount: float = Field(
        ge=0,
        description="The total monetary amount of the order."
    )
    created_ts: int = Field(
        description="The order creation timestamp as a Unix epoch integer."
    )


class ECommerceOrdersOutput(BaseModel):
    """Represent the structured data output for a list of retrieved ecommerce orders."""

    customer_email: str = Field(
        description="The email address of the customer that owns the orders."
    )
    orders: list[ECommerceOrderOutput] = Field(
        default_factory=list,
        description="The list of orders belonging to the customer.",
    )


class ECommerceOrderItemOutput(BaseModel):
    """Represent a single order item in public agent output."""

    item_id: int = Field(
        gt=0,
        description="The unique identifier for the item row within an order.",
    )
    sku_id: int = Field(
        gt=0,
        description="The unique stock keeping unit identifier for the purchased product.",
    )
    sku_code: str = Field(
        description="The merchant-visible stock keeping unit code for the item.",
    )
    name: str = Field(
        description="The product name recorded on the order item at purchase time.",
    )
    quantity: int = Field(
        gt=0,
        description="The positive quantity of this product purchased in the order.",
    )
    price: float = Field(
        ge=0,
        description="The non-negative unit price recorded for this item at purchase time.",
    )


class ECommerceOrderDetailsOutput(BaseModel):
    """Represent the structured data output for a retrieved ecommerce order."""

    exists: bool = Field(
        description="Whether the requested order was successfully found."
    )
    order: ECommerceOrderOutput | None = Field(
        default=None,
        description="The retrieved order metadata, or null when the order was not found.",
    )
    items: list[ECommerceOrderItemOutput] = Field(
        default_factory=list,
        description="The product items belonging to the order when the order exists.",
    )


class ECommerceReturnRequestOutput(BaseModel):
    """Represent one ecommerce return request in public agent output."""

    return_request_id: int = Field(
        gt=0,
        description="The unique identifier of the return request in the ecommerce system.",
    )
    order_id: int = Field(
        gt=0,
        description="The positive order identifier associated with the return request.",
    )
    customer_id: int = Field(
        gt=0,
        description="The positive customer identifier associated with the return request.",
    )
    status: int = Field(
        ge=0,
        le=5,
        description=(
            "Return status code exposed by the agent contract "
            "(0: REQUESTED, 1: APPROVED, 2: REJECTED, 3: RECEIVED, "
            "4: REFUNDED, 5: CANCELLED)."
        ),
    )
    reason_code: int = Field(
        ge=0,
        le=4,
        description=(
            "Return reason code exposed by the agent contract "
            "(0: CHANGE_OF_MIND, 1: DAMAGED, 2: WRONG_ITEM, "
            "3: NOT_AS_DESCRIBED, 4: LATE_DELIVERY)."
        ),
    )
    reason_text: str = Field(
        description="Free-form customer explanation supplied with the return request."
    )
    item_condition: int = Field(
        ge=0,
        le=3,
        description=(
            "Returned item condition code exposed by the agent contract "
            "(0: UNOPENED, 1: OPENED, 2: USED, 3: DAMAGED)."
        ),
    )
    requested_at: int = Field(
        description="Unix timestamp when the return request was submitted."
    )
    approved_at: int | None = Field(
        default=None,
        description="Unix timestamp when the return request was approved, if applicable.",
    )
    rejected_at: int | None = Field(
        default=None,
        description="Unix timestamp when the return request was rejected, if applicable.",
    )
    received_at: int | None = Field(
        default=None,
        description="Unix timestamp when the returned items were received, if applicable.",
    )
    closed_at: int | None = Field(
        default=None,
        description="Unix timestamp when the return process was closed, if applicable.",
    )
    resolution_type: int | None = Field(
        default=None,
        ge=0,
        le=2,
        description=(
            "Return resolution type code when decided "
            "(0: REFUND, 1: STORE_CREDIT, 2: REJECT), or null if undecided."
        ),
    )
    created_by: int | None = Field(
        default=None,
        description="Identifier of the agent or user who handled the return, if known.",
    )
    created_at: int = Field(
        description="Unix timestamp when the return request record was created."
    )
    updated_at: int = Field(
        description="Unix timestamp when the return request record was last updated."
    )


class ECommerceReturnsByOrderOutput(BaseModel):
    """Represent the structured return details output for one order."""

    order_id: int = Field(
        gt=0,
        description="The positive order identifier used to query return details.",
    )
    return_request: ECommerceReturnRequestOutput | None = Field(
        default=None,
        description="The return request associated with the order, or null if none exists.",
    )


class ECommerceReturnsByCustomerOutput(BaseModel):
    """Represent the structured return details output for one customer."""

    customer_id: int = Field(
        gt=0,
        description="The positive customer identifier used to query return details.",
    )
    returns: list[ECommerceReturnRequestOutput] = Field(
        default_factory=list,
        description="Return requests associated with the customer.",
    )


class ECommerceCreateReturnOutput(BaseModel):
    """Represent the structured data output for a created return request."""

    success: bool = Field(
        description="Whether the return request was successfully created."
    )
    return_request: ECommerceReturnRequestOutput | None = Field(
        default=None,
        description="The created return request details, if successful."
    )
    error_message: str | None = Field(
        default=None,
        description="An error explanation if success is False."
    )



AgentOutputPart = Annotated[
    TextPart | StructuredDataPart | SourcesPart,
    Field(discriminator="kind"),
]


class AgentOutput(BaseModel):
    """Represent one stable public result produced by an agent run."""

    output_id: str = Field(
        min_length=1,
        description="Globally unique identifier used to correlate and deduplicate the output."
    )
    parts: list[AgentOutputPart] = Field(
        description="Ordered heterogeneous content parts comprising the public output."
    )
