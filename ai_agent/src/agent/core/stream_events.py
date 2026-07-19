"""Helpers for publishing typed LangGraph custom stream events."""

from uuid import NAMESPACE_URL, uuid5

from langgraph.types import StreamWriter
from shared_common.schemas.ai_agent import (
    AgentCustomStreamEventBase,
    AgentCustomStreamEventKind,
)

from agent.core.logger import logger

AGENT_CUSTOM_STREAM_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "agentic-resolution-platform/agent-custom-stream/v1",
)


def build_custom_stream_progress_id(
    *,
    identity_scope: str,
    event_kind: AgentCustomStreamEventKind,
    emission_key: str,
) -> str:
    """Build a deterministic UUID string for one scoped progress signal."""
    if not identity_scope:
        logger.error("Custom stream progress identity requires an identity scope")
        raise ValueError("identity_scope is required")
    if not isinstance(event_kind, AgentCustomStreamEventKind):
        logger.error("Custom stream progress identity requires an event kind")
        raise TypeError("event_kind must be an AgentCustomStreamEventKind")
    if not emission_key:
        logger.error("Custom stream progress identity requires an emission key")
        raise ValueError("emission_key is required")

    return str(
        uuid5(
            AGENT_CUSTOM_STREAM_NAMESPACE,
            f"{identity_scope}:{event_kind.value}:{emission_key}",
        )
    )


def publish_custom_stream_event(
    writer: StreamWriter,
    event: AgentCustomStreamEventBase,
) -> None:
    """Publish one typed custom stream event as JSON-compatible data."""
    writer(event.model_dump(mode="json"))
