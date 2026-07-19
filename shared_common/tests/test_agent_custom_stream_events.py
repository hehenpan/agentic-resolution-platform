"""Tests for typed custom stream event schemas."""

import pytest
from pydantic import ValidationError
from shared_common.schemas.ai_agent import (
    AgentCustomStreamEventKind,
    AgentProgressStatus,
    AgentProgressStreamEvent,
)


def _progress_payload() -> dict[str, object]:
    return {
        "kind": AgentCustomStreamEventKind.PROGRESS.value,
        "schema_version": "1",
        "progress_id": "progress-1",
        "operation": "policy_retrieval",
        "status": AgentProgressStatus.STARTED.value,
        "progress_current": 1,
        "progress_total": 3,
        "details": {"result_count": 3},
    }


def test_progress_custom_stream_event_round_trips_as_json() -> None:
    event = AgentProgressStreamEvent.model_validate(_progress_payload())

    dumped = event.model_dump(mode="json")
    replayed = AgentProgressStreamEvent.model_validate(dumped)

    assert replayed == event
    assert dumped["kind"] == AgentCustomStreamEventKind.PROGRESS.value
    assert dumped["status"] == AgentProgressStatus.STARTED.value


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("kind", "agent.unknown"),
        ("progress_id", ""),
        ("operation", ""),
        ("status", "unknown"),
    ],
)
def test_progress_custom_stream_event_rejects_invalid_required_fields(
    field_name: str,
    value: object,
) -> None:
    payload = _progress_payload()
    payload[field_name] = value

    with pytest.raises(ValidationError):
        AgentProgressStreamEvent.model_validate(payload)


@pytest.mark.parametrize("field_name", ["progress_current", "progress_total"])
def test_progress_custom_stream_event_rejects_negative_progress(
    field_name: str,
) -> None:
    payload = _progress_payload()
    payload[field_name] = -1

    with pytest.raises(ValidationError):
        AgentProgressStreamEvent.model_validate(payload)


@pytest.mark.parametrize("field_name", ["progress_current", "progress_total"])
def test_progress_custom_stream_event_rejects_non_strict_int_progress(
    field_name: str,
) -> None:
    payload = _progress_payload()
    payload[field_name] = "1"

    with pytest.raises(ValidationError):
        AgentProgressStreamEvent.model_validate(payload)


def test_progress_custom_stream_event_rejects_non_json_details() -> None:
    payload = _progress_payload()
    payload["details"] = {"bad": object()}

    with pytest.raises(ValidationError):
        AgentProgressStreamEvent.model_validate(payload)


def test_progress_custom_stream_event_fields_have_descriptions() -> None:
    for field in AgentProgressStreamEvent.model_fields.values():
        assert field.description
