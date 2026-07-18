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
