"""Custom stream event builders for the Policy QA subgraph."""

from enum import Enum

from pydantic import JsonValue
from shared_common.schemas.ai_agent import (
    AgentCustomStreamEventKind,
    AgentProgressStatus,
    AgentProgressStreamEvent,
)

from agent.core.stream_events import build_custom_stream_progress_id


class PolicyQAProgressOperation(str, Enum):
    """Identify Policy QA business operations that can report progress."""

    POLICY_RETRIEVAL = "policy_retrieval"


class PolicyQARetrievalEmissionKey(str, Enum):
    """Identify stable Policy QA retrieval progress emissions."""

    STARTED = "policy_retrieval.started"
    COMPLETED = "policy_retrieval.completed"


def build_policy_retrieval_progress_event(
    *,
    identity_scope: str,
    emission_key: PolicyQARetrievalEmissionKey,
    status: AgentProgressStatus,
    result_count: int | None = None,
) -> AgentProgressStreamEvent:
    """Build one typed progress event for Policy QA retrieval."""
    details: dict[str, JsonValue] = {}
    if result_count is not None:
        details["result_count"] = result_count

    return AgentProgressStreamEvent(
        progress_id=build_custom_stream_progress_id(
            identity_scope=identity_scope,
            event_kind=AgentCustomStreamEventKind.PROGRESS,
            emission_key=emission_key.value,
        ),
        operation=PolicyQAProgressOperation.POLICY_RETRIEVAL.value,
        status=status,
        progress_current=result_count,
        progress_total=None,
        details=details,
    )
