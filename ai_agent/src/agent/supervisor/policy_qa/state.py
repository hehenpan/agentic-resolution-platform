"""State models for the Policy QA subgraph."""

from typing import Any
from uuid import UUID

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field
from shared_common.schemas.ai_agent import AgentOutput

from agent.supervisor.state import SupervisorState


class PolicyChunk(BaseModel):
    """Represent a policy chunk retrieved from the vector database."""

    point_id: int | str | UUID = Field(
        description="Vector store point ID for the retrieved policy chunk."
    )
    score: float = Field(description="Similarity score for the retrieved chunk.")
    file_name: str = Field(description="Source policy file name for citation.")
    text: str = Field(description="Raw policy text returned from retrieval.")
    payload: dict[str, Any] = Field(
        description="Original vector payload returned for this policy chunk."
    )


class PolicyQAState(SupervisorState):
    """Represent internal state for the Policy QA subgraph."""

    query: str | None = Field(
        default=None,
        description="Policy retrieval query derived from the user message.",
    )
    policy_chunks: list[PolicyChunk] = Field(
        default_factory=list,
        description="Policy chunks retrieved from the vector store.",
    )
    draft: str | None = Field(
        default=None,
        description="LLM-polished draft response for the policy question.",
    )
    generation_error: str | None = Field(
        default=None,
        description="Error message captured when draft generation fails.",
    )


class RetrievePolicyUpdate(BaseModel):
    """Represent the state update returned by retrieve_policy."""

    query: str = Field(description="Policy retrieval query used for vector search.")
    policy_chunks: list[PolicyChunk] = Field(
        description="Policy chunks returned by vector search."
    )


class GenerateDraftUpdate(BaseModel):
    """Represent the state update returned by generate_draft."""

    draft: str | None = Field(
        default=None,
        description="LLM-polished draft policy answer.",
    )
    generation_error: str | None = Field(
        default=None,
        description="Error message captured during draft generation.",
    )


class BuildResponseUpdate(BaseModel):
    """Represent the state update returned by build_response."""

    messages: list[BaseMessage] = Field(
        description="AI messages produced as graph state updates."
    )
    outputs: list[AgentOutput] = Field(
        description="Domain outputs produced from the policy QA response."
    )


class PolicyQAOutput(BaseModel):
    """Represent the Policy QA fields returned to the supervisor."""

    messages: list[BaseMessage] = Field(
        description="AI messages returned by the Policy QA graph."
    )
    outputs: list[AgentOutput] = Field(
        description="Domain outputs returned by the Policy QA graph."
    )
