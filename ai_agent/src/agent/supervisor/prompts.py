"""Prompt templates for supervisor routing."""

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ConfigDict, Field


class SupervisorRoutingPromptInput(BaseModel):
    """Validate input variables for the supervisor routing prompt."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )

    question: str = Field(
        min_length=1,
        description="Customer request text used for supervisor routing.",
    )


SUPERVISOR_ROUTING_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You route customer-service requests to the most appropriate "
            "specialist graph. Select policy_qa for questions about company "
            "policies, including delivery, returns, refunds, warranties, "
            "payments, privacy, or other documented customer policies. "
            "Select ecommerce_query for queries asking to retrieve, check, or lookup "
            "customer details, user profiles, customer accounts, or order lists. "
            "Select ecommerce_action for write actions, changes, mutations, or initiating new "
            "operations, such as creating or initiating a return request. "
            "Return only the structured route requested by the schema.",
        ),
        ("human", "Customer request: {question}"),
    ]
)
