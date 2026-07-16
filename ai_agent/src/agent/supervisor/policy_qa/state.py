"""State models for the Policy QA subgraph."""

from typing import Any
from uuid import UUID

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

from agent.supervisor.state import SupervisorState


class PolicyChunk(BaseModel):
    """Represent a policy chunk retrieved from the vector database."""

    point_id: int | str | UUID
    score: float
    file_name: str
    text: str
    payload: dict[str, Any]


class PolicyQAState(SupervisorState):
    """Represent internal state for the Policy QA subgraph."""

    query: str | None = None
    policy_chunks: list[PolicyChunk] = Field(default_factory=list)
    draft: str | None = None
    generation_error: str | None = None


class RetrievePolicyUpdate(BaseModel):
    """Represent the state update returned by retrieve_policy."""

    query: str
    policy_chunks: list[PolicyChunk]


class GenerateDraftUpdate(BaseModel):
    """Represent the state update returned by generate_draft."""

    draft: str | None = None
    generation_error: str | None = None


class BuildResponseUpdate(BaseModel):
    """Represent the state update returned by build_response."""

    messages: list[BaseMessage]


class PolicyQAOutput(BaseModel):
    """Represent the Policy QA fields returned to the supervisor."""

    messages: list[BaseMessage]
