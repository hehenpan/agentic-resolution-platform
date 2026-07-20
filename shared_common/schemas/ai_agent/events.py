"""Stable domain events emitted by AI Agent runs."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, JsonValue

from shared_common.schemas.ai_agent.enums import (
    AgentDomainEventKind,
    AgentProgressStatus,
)
from shared_common.schemas.ai_agent.human_input import (
    AgentResumeCursor,
    HumanInputRequest,
)
from shared_common.schemas.ai_agent.outputs import AgentOutput

UnixTimestamp = Annotated[int, Field(strict=True, ge=0)]


class AgentDomainEventBase(BaseModel):
    """Define the shared envelope for agent domain events."""

    event_id: str = Field(
        min_length=1,
        description="Globally unique identifier used to deduplicate this domain event."
    )
    kind: AgentDomainEventKind = Field(
        description="Discriminator identifying the domain event payload type."
    )
    schema_version: Literal["1"] = Field(
        default="1",
        description="Version of the domain event envelope and payload contract.",
    )
    thread_id: str = Field(
        description="LangGraph thread that owns the conversation and event."
    )
    run_id: str = Field(
        min_length=1,
        description="Unique identifier of the specific agent run that produced this event.",
    )

    sequence: int = Field(
        strict=True,
        ge=0,
        description="Zero-based emission order assigned within one projected operation.",
    )
    source_sequences: list[Annotated[int, Field(strict=True, ge=0)]] = Field(
        default_factory=list,
        description=(
            "Raw stream event sequence numbers that contributed to this domain event."
        ),
    )
    created_at: UnixTimestamp = Field(
        description="Unix timestamp in seconds when the domain event was created."
    )


class AgentOutputProduced(AgentDomainEventBase):
    """Report one formal output produced by an agent run."""

    kind: Literal[AgentDomainEventKind.OUTPUT_PRODUCED] = Field(
        default=AgentDomainEventKind.OUTPUT_PRODUCED,
        description="Discriminator for an agent output event.",
    )
    output: AgentOutput = Field(
        description="Stable public output produced for downstream consumers."
    )


class AgentProgressReported(AgentDomainEventBase):
    """Report optional progress for a stable business operation."""

    kind: Literal[AgentDomainEventKind.PROGRESS_REPORTED] = Field(
        default=AgentDomainEventKind.PROGRESS_REPORTED,
        description="Discriminator for an agent progress event.",
    )
    operation: str = Field(
        description="Stable name of the business operation reporting progress."
    )
    status: AgentProgressStatus = Field(
        description="Current lifecycle status of the reported operation."
    )
    current: int | None = Field(
        default=None,
        strict=True,
        ge=0,
        description="Current completed-unit count when measurable.",
    )
    total: int | None = Field(
        default=None,
        strict=True,
        ge=0,
        description="Total unit count when known.",
    )
    details: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Additional JSON-compatible progress information.",
    )


class HumanInputRequested(AgentDomainEventBase):
    """Report that an agent run is waiting for human input."""

    kind: Literal[AgentDomainEventKind.HUMAN_INPUT_REQUESTED] = Field(
        default=AgentDomainEventKind.HUMAN_INPUT_REQUESTED,
        description="Discriminator for a human-input request event.",
    )
    interrupt_id: str = Field(
        description="LangGraph interrupt identifier targeted by the resume command."
    )
    request: HumanInputRequest = Field(
        description="Prompt, schema, and actions presented to the human operator."
    )
    resume_cursor: AgentResumeCursor = Field(
        description="Checkpoint cursor required to resume the interrupted execution."
    )


class AgentRunCompleted(AgentDomainEventBase):
    """Report successful completion of one agent execution stage."""

    kind: Literal[AgentDomainEventKind.RUN_COMPLETED] = Field(
        default=AgentDomainEventKind.RUN_COMPLETED,
        description="Discriminator for a successful terminal event.",
    )
    output_ids: list[str] = Field(
        default_factory=list,
        description="Identifiers of public outputs produced before completion.",
    )


class AgentRunInterrupted(AgentDomainEventBase):
    """Report that one agent execution stage has paused."""

    kind: Literal[AgentDomainEventKind.RUN_INTERRUPTED] = Field(
        default=AgentDomainEventKind.RUN_INTERRUPTED,
        description="Discriminator for an interrupted terminal event.",
    )
    interrupt_ids: list[str] = Field(
        description="Outstanding LangGraph interrupt identifiers awaiting responses."
    )


class AgentError(BaseModel):
    """Represent a safe public error produced by an agent run."""

    code: str = Field(
        description="Stable machine-readable code identifying the error category."
    )
    message: str = Field(
        description="Safe human-readable error message suitable for API consumers."
    )
    retryable: bool = Field(
        default=False,
        description="Whether retrying the failed operation may succeed safely.",
    )
    details: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Additional safe JSON-compatible diagnostic information.",
    )


class AgentRunFailed(AgentDomainEventBase):
    """Report terminal failure of one agent execution stage."""

    kind: Literal[AgentDomainEventKind.RUN_FAILED] = Field(
        default=AgentDomainEventKind.RUN_FAILED,
        description="Discriminator for a failed terminal event.",
    )
    error: AgentError = Field(
        description="Sanitized error information exposed to downstream consumers."
    )


AgentDomainEvent = Annotated[
    AgentOutputProduced
    | AgentProgressReported
    | HumanInputRequested
    | AgentRunCompleted
    | AgentRunInterrupted
    | AgentRunFailed,
    Field(discriminator="kind"),
]
