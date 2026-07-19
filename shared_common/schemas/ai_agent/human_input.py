"""Schemas for interrupt-driven human input and run resumption."""

from pydantic import BaseModel, Field, JsonValue


class HumanInputRequest(BaseModel):
    """Describe input required to continue an interrupted agent run."""

    prompt: str = Field(
        description="Human-readable instruction presented to the operator."
    )
    schema_id: str = Field(
        description="Stable versioned identifier describing the structure of input."
    )
    input_schema: dict[str, JsonValue] = Field(
        description="JSON Schema describing the response value expected from the operator."
    )
    context: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Additional JSON-compatible information needed to render the request.",
    )
    allowed_actions: list[str] = Field(
        default_factory=list,
        description="Named actions the operator may choose when responding.",
    )


class AgentResumeCursor(BaseModel):
    """Carry the server-side checkpoint cursor required for a resume."""

    checkpoint_id: str = Field(
        description="LangGraph checkpoint identifier from which execution will resume."
    )
    checkpoint_ns: str = Field(
        default="",
        description="Checkpoint namespace identifying the graph or nested subgraph scope.",
    )
    checkpoint_map: dict[str, str] = Field(
        default_factory=dict,
        description="Namespace-to-checkpoint mapping required to restore nested graphs.",
    )


class HumanInputResponse(BaseModel):
    """Represent validated human input used to resume an agent run."""

    schema_id: str = Field(
        description="Stable versioned identifier describing the structure of response_data. "
        "When answering to the interruption, it should be the same as HumanInputRequest.schema_id."
    )
    response_data: JsonValue = Field(
        description="JSON-compatible value supplied to resolve the targeted interrupt."
    )
