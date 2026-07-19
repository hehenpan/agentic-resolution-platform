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
