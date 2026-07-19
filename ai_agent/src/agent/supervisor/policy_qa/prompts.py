"""Prompt templates for policy response generation."""

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, ConfigDict, Field


class PolicyDraftPromptInput(BaseModel):
    """Validate input variables for the policy draft prompt."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )

    question: str = Field(
        min_length=1,
        description="Customer policy question to answer.",
    )
    context: str = Field(
        min_length=1,
        description="Retrieved policy excerpts supplied to the draft LLM.",
    )


POLICY_DRAFT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a customer-service policy specialist. Write a concise, "
            "helpful answer using only the supplied policy excerpts. Do not "
            "invent details or cite source files. The application will append "
            "the exact source excerpts separately. Reply in the same language "
            "as the customer request.",
        ),
        (
            "human",
            "Customer request:\n{question}\n\nPolicy excerpts:\n{context}",
        ),
    ]
)
