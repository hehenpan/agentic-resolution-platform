"""State models for the Ecommerce Action subgraph."""

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field
from shared_common.schemas.ai_agent import AgentOutput, AgentReturnReason, AgentItemCondition
from shared_common.schemas.ai_agent.outputs import ECommerceCreateReturnOutput

from agent.supervisor.state import SupervisorState


class ReturnRequestDetails(BaseModel):
    """Encapsulate details required to create a return request."""

    order_id: int | None = Field(
        default=None,
        description="The order identifier targeted by the return request.",
    )
    customer_id: int | None = Field(
        default=None,
        description="The customer identifier targeted by the return request.",
    )
    reason_code: AgentReturnReason | None = Field(
        default=None,
        description="The reason code for the return request.",
    )
    reason_text: str | None = Field(
        default=None,
        description="Additional reason explanation text.",
    )
    item_condition: AgentItemCondition | None = Field(
        default=None,
        description="The condition of the product being returned.",
    )
    created_by: int | None = Field(
        default=None,
        description="The user_id of the agent who operates this return request creation.",
    )


class EcommerceActionState(SupervisorState):
    """Represent internal state for the Ecommerce Action subgraph."""

    return_details: ReturnRequestDetails = Field(
        default_factory=ReturnRequestDetails,
        description="The details of the return request being processed.",
    )
    create_return_output: ECommerceCreateReturnOutput | None = Field(
        default=None,
        description="Structured output result for the created return request.",
    )


class ActionAgentUpdate(BaseModel):
    """Represent the state update returned by the action_agent node."""

    messages: list[BaseMessage] = Field(
        description="Agent messages produced during action reasoning."
    )


class ExecuteCreateReturnUpdate(BaseModel):
    """Represent the state update returned by the execute_create_return node."""

    return_details: ReturnRequestDetails = Field(
        description="The details of the return request that was executed."
    )
    create_return_output: ECommerceCreateReturnOutput = Field(
        description="Result of the return request creation."
    )
    outputs: list[AgentOutput] = Field(
        description="Produced structured return request output."
    )
    messages: list[BaseMessage] = Field(
        description="Tool messages produced during execution."
    )


class EcommerceActionOutput(BaseModel):
    """Represent the Ecommerce Action fields returned to the supervisor."""

    messages: list[BaseMessage] = Field(
        description="Conversation messages returned by the Ecommerce Action graph."
    )
    outputs: list[AgentOutput] = Field(
        description="Domain outputs returned by the Ecommerce Action graph."
    )
