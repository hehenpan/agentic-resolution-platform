"""State models for the Ecommerce Query subgraph."""

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field
from shared_common.schemas.ai_agent import AgentOutput
from shared_common.schemas.ai_agent.outputs import (
    ECommerceOrderDetailsOutput,
    ECommerceOrdersOutput,
    ECommerceReturnsByCustomerOutput,
    ECommerceReturnsByOrderOutput,
    ECommerceUserOutput,
)

from agent.supervisor.state import SupervisorState


class EcommerceQueryState(SupervisorState):
    """Represent internal state for the Ecommerce Query subgraph."""

    email: str | None = Field(
        default=None,
        description="The customer email address targeted by the query.",
    )
    order_id: int | None = Field(
        default=None,
        description="The order identifier targeted by the query.",
    )
    customer_id: int | None = Field(
        default=None,
        description="The customer identifier targeted by the query.",
    )
    user_output: ECommerceUserOutput | None = Field(
        default=None,
        description="Structured query result for the customer details.",
    )
    orders_output: ECommerceOrdersOutput | None = Field(
        default=None,
        description="Structured query result for the customer orders list.",
    )
    order_details_output: ECommerceOrderDetailsOutput | None = Field(
        default=None,
        description="Structured query result for one order's details.",
    )
    returns_by_order_output: ECommerceReturnsByOrderOutput | None = Field(
        default=None,
        description="Structured query result for return details associated with one order.",
    )
    returns_by_customer_output: ECommerceReturnsByCustomerOutput | None = Field(
        default=None,
        description="Structured query result for return details associated with one customer.",
    )


class QueryAgentUpdate(BaseModel):
    """Represent the state update returned by the query_agent node."""

    messages: list[BaseMessage] = Field(
        description="Agent messages produced during query reasoning."
    )




class RetrieveUserUpdate(BaseModel):
    """Represent the state update returned by the retrieve_user node."""

    user_output: ECommerceUserOutput = Field(
        description="Retrieved ecommerce user details."
    )
    outputs: list[AgentOutput] = Field(
        description="Produced structured user details output."
    )
    messages: list[BaseMessage] = Field(
        description="Tool messages produced during retrieval."
    )


class RetrieveOrdersUpdate(BaseModel):
    """Represent the state update returned by the retrieve_orders node."""

    orders_output: ECommerceOrdersOutput = Field(
        description="Retrieved ecommerce customer orders list."
    )
    outputs: list[AgentOutput] = Field(
        description="Produced structured customer orders output."
    )
    messages: list[BaseMessage] = Field(
        description="Tool messages produced during retrieval."
    )


class RetrieveOrderDetailsUpdate(BaseModel):
    """Represent the state update returned by the retrieve_order_details node."""

    order_id: int = Field(
        description="Order identifier used for the order details retrieval."
    )
    order_details_output: ECommerceOrderDetailsOutput = Field(
        description="Retrieved ecommerce order details."
    )
    outputs: list[AgentOutput] = Field(
        description="Produced structured order details output."
    )
    messages: list[BaseMessage] = Field(
        description="Tool messages produced during retrieval."
    )


class RetrieveReturnsByOrderUpdate(BaseModel):
    """Represent the state update returned by the retrieve_returns_by_order node."""

    order_id: int = Field(
        description="Order identifier used for the return details retrieval."
    )
    returns_by_order_output: ECommerceReturnsByOrderOutput = Field(
        description="Retrieved ecommerce return details for one order."
    )
    outputs: list[AgentOutput] = Field(
        description="Produced structured return details output for one order."
    )
    messages: list[BaseMessage] = Field(
        description="Tool messages produced during retrieval."
    )


class RetrieveReturnsByCustomerUpdate(BaseModel):
    """Represent the state update returned by the retrieve_returns_by_customer node."""

    customer_id: int = Field(
        description="Customer identifier used for the return details retrieval."
    )
    returns_by_customer_output: ECommerceReturnsByCustomerOutput = Field(
        description="Retrieved ecommerce return details for one customer."
    )
    outputs: list[AgentOutput] = Field(
        description="Produced structured return details output for one customer."
    )
    messages: list[BaseMessage] = Field(
        description="Tool messages produced during retrieval."
    )


class EcommerceQueryOutput(BaseModel):
    """Represent the Ecommerce Query fields returned to the supervisor."""

    messages: list[BaseMessage] = Field(
        description="Conversation messages returned by the Ecommerce Query graph."
    )
    outputs: list[AgentOutput] = Field(
        description="Domain outputs returned by the Ecommerce Query graph."
    )
