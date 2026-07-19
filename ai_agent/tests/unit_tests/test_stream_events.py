"""Tests for typed custom stream event publishing helpers."""

from uuid import UUID

import pytest
from shared_common.schemas.ai_agent import (
    AgentCustomStreamEventKind,
    AgentProgressStatus,
    AgentProgressStreamEvent,
)

from agent.core.stream_events import (
    build_custom_stream_progress_id,
    publish_custom_stream_event,
)

IDENTITY_SCOPE_ONE = "task-1"
IDENTITY_SCOPE_TWO = "task-2"
EMISSION_KEY_STARTED = "policy_retrieval.started"


def test_build_custom_stream_progress_id_is_stable() -> None:
    first = build_custom_stream_progress_id(
        identity_scope=IDENTITY_SCOPE_ONE,
        event_kind=AgentCustomStreamEventKind.PROGRESS,
        emission_key=EMISSION_KEY_STARTED,
    )
    replayed = build_custom_stream_progress_id(
        identity_scope=IDENTITY_SCOPE_ONE,
        event_kind=AgentCustomStreamEventKind.PROGRESS,
        emission_key=EMISSION_KEY_STARTED,
    )

    assert replayed == first
    assert UUID(first).version == 5


def test_build_custom_stream_progress_id_changes_for_different_scope() -> None:
    first = build_custom_stream_progress_id(
        identity_scope=IDENTITY_SCOPE_ONE,
        event_kind=AgentCustomStreamEventKind.PROGRESS,
        emission_key=EMISSION_KEY_STARTED,
    )
    second = build_custom_stream_progress_id(
        identity_scope=IDENTITY_SCOPE_TWO,
        event_kind=AgentCustomStreamEventKind.PROGRESS,
        emission_key=EMISSION_KEY_STARTED,
    )

    assert second != first


def test_build_custom_stream_progress_id_changes_for_different_key() -> None:
    first = build_custom_stream_progress_id(
        identity_scope=IDENTITY_SCOPE_ONE,
        event_kind=AgentCustomStreamEventKind.PROGRESS,
        emission_key=EMISSION_KEY_STARTED,
    )
    second = build_custom_stream_progress_id(
        identity_scope=IDENTITY_SCOPE_ONE,
        event_kind=AgentCustomStreamEventKind.PROGRESS,
        emission_key="policy_retrieval.completed",
    )

    assert second != first


def test_build_custom_stream_progress_id_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        build_custom_stream_progress_id(
            identity_scope="",
            event_kind=AgentCustomStreamEventKind.PROGRESS,
            emission_key=EMISSION_KEY_STARTED,
        )

    with pytest.raises(TypeError):
        build_custom_stream_progress_id(
            identity_scope=IDENTITY_SCOPE_ONE,
            event_kind="agent.progress",  # type: ignore[arg-type]
            emission_key=EMISSION_KEY_STARTED,
        )

    with pytest.raises(ValueError):
        build_custom_stream_progress_id(
            identity_scope=IDENTITY_SCOPE_ONE,
            event_kind=AgentCustomStreamEventKind.PROGRESS,
            emission_key="",
        )


def test_publish_custom_stream_event_writes_json_payload() -> None:
    written: list[object] = []
    event = AgentProgressStreamEvent(
        progress_id="progress-1",
        operation="policy_retrieval",
        status=AgentProgressStatus.STARTED,
        progress_current=0,
        progress_total=None,
        details={"result_count": 0},
    )

    publish_custom_stream_event(written.append, event)

    assert written == [event.model_dump(mode="json")]
