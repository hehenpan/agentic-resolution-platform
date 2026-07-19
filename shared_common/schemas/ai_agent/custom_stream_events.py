"""Typed events emitted through LangGraph custom streaming."""

from typing import Literal

from pydantic import BaseModel, Field, JsonValue

from shared_common.schemas.ai_agent.enums import (
    AgentCustomStreamEventKind,
    AgentProgressStatus,
)


class AgentCustomStreamEventBase(BaseModel):
    """Define the shared envelope for typed custom stream events."""

    kind: AgentCustomStreamEventKind = Field(
        description="Discriminator identifying the custom stream event payload type."
    )
    schema_version: Literal["1"] = Field(
        default="1",
        description="Version of the custom stream event payload contract.",
    )


class AgentProgressStreamEvent(AgentCustomStreamEventBase):
    """Report progress for a stable business operation through custom streaming."""

    kind: Literal[AgentCustomStreamEventKind.PROGRESS] = Field(
        default=AgentCustomStreamEventKind.PROGRESS,
        description="Discriminator for a progress custom stream event.",
    )
    progress_id: str = Field(
        min_length=1,
        description=(
            "Stable unique identifier for this progress signal, later used as "
            "the projected AgentProgressReported event_id."
        ),
    )
    operation: str = Field(
        min_length=1,
        description="Stable business operation name that is reporting progress.",
    )
    status: AgentProgressStatus = Field(
        description="Current lifecycle status of the reported business operation."
    )
    progress_current: int | None = Field(
        default=None,
        strict=True,
        ge=0,
        description="Current completed-unit count when progress is measurable.",
    )
    progress_total: int | None = Field(
        default=None,
        strict=True,
        ge=0,
        description="Total unit count when progress is measurable and known.",
    )
    details: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Additional lightweight JSON-compatible progress information.",
    )
