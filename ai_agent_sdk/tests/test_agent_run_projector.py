"""Tests for projecting LangGraph stream data into agent domain events."""

import pytest
from shared_common.schemas.ai_agent import (
    AgentDomainEventKind,
    AgentOutputProduced,
    AgentProgressReported,
    AgentRunCompleted,
    AgentRunFailed,
    AgentRunInterrupted,
    HumanInputRequested,
    TextPart,
)

from ai_agent_sdk.agent_run_projector import (
    AgentRunProjector,
    build_event_id,
)

OUTPUT_ID_1 = "11111111-1111-5111-8111-111111111111"
OUTPUT_ID_2 = "22222222-2222-5222-8222-222222222222"
THREAD_ID = "thread-1"
CREATED_AT = 1_725_000_000


def _output(output_id: str, text: str) -> dict[str, object]:
    return {
        "output_id": output_id,
        "parts": [{"kind": "text", "text": text}],
    }


def _projector() -> AgentRunProjector:
    return AgentRunProjector(
        thread_id=THREAD_ID,
        clock=lambda: CREATED_AT,
    )


@pytest.mark.parametrize(
    "event_type",
    [
        "metadata",
        "messages/partial",
        "messages/complete",
        "messages-tuple",
        "events",
        "tasks",
        "debug",
        "unsupported-future-type",
    ],
)
def test_process_discards_unhandled_stream_events(event_type: str) -> None:
    assert (
        _projector().process(
            {"type": event_type, "data": {"ignored": True}},
            source_sequence=0,
        )
        == []
    )


def test_process_can_produce_one_or_multiple_events() -> None:
    one = _projector().process(
        {
            "type": "values",
            "data": {"outputs": [_output(OUTPUT_ID_1, "First answer")]},
        },
        source_sequence=1,
    )
    multiple = _projector().process(
        {
            "type": "updates",
            "data": {
                "arbitrary_transport_key": {
                    "outputs": [
                        _output(OUTPUT_ID_1, "First answer"),
                        _output(OUTPUT_ID_2, "Second answer"),
                    ]
                },
                "another_transport_key": {
                    "type": "progress",
                },
            },
        },
        source_sequence=2,
    )

    assert len(one) == 1
    assert len(multiple) == 2
    assert isinstance(one[0], AgentOutputProduced)
    assert isinstance(multiple[0], AgentOutputProduced)
    assert isinstance(multiple[1], AgentOutputProduced)
    assert multiple[1].output.output_id == OUTPUT_ID_2


def test_output_projection_does_not_depend_on_node_name() -> None:
    first = _projector().process(
        {
            "type": "updates",
            "data": {"node_a": {"outputs": [_output(OUTPUT_ID_1, "Answer")]}},
        },
        source_sequence=4,
    )
    second = _projector().process(
        {
            "type": "updates",
            "data": {"renamed_node": {"outputs": [_output(OUTPUT_ID_1, "Answer")]}},
        },
        source_sequence=4,
    )

    assert first == second


def test_duplicate_output_is_published_once_and_uses_output_id() -> None:
    projector = _projector()
    raw_event = {
        "type": "values",
        "data": {"outputs": [_output(OUTPUT_ID_1, "Answer")]},
    }

    first = projector.process(raw_event, source_sequence=3)
    replayed = projector.process(raw_event, source_sequence=4)

    assert len(first) == 1
    assert first[0].event_id == OUTPUT_ID_1
    assert replayed == []


def test_non_output_event_identity_is_replay_stable() -> None:
    first = build_event_id(
        AgentDomainEventKind.RUN_COMPLETED,
        THREAD_ID,
        "terminal",
    )
    replayed = build_event_id(
        AgentDomainEventKind.RUN_COMPLETED,
        THREAD_ID,
        "terminal",
    )
    different = build_event_id(
        AgentDomainEventKind.RUN_COMPLETED,
        THREAD_ID,
        "different-subject",
    )

    assert first == replayed
    assert first != different


def test_progress_normalizes_sources_and_has_stable_identity() -> None:
    raw_event = {
        "type": "custom",
        "data": {
            "type": "progress",
            "operation": "policy_retrieval",
            "status": "in_progress",
            "current": 1,
            "total": 3,
            "source_sequences": [9, 7, 9],
            "details": {"message": "Searching"},
        },
    }

    first = _projector().process(raw_event, source_sequence=8)
    replayed = _projector().process(raw_event, source_sequence=8)

    assert first == replayed
    assert len(first) == 1
    assert isinstance(first[0], AgentProgressReported)
    assert first[0].source_sequences == [7, 8, 9]


def test_progress_without_source_sequence_is_not_published() -> None:
    events = _projector().process(
        {
            "type": "custom",
            "data": {
                "type": "progress",
                "operation": "policy_retrieval",
                "status": "started",
            },
        }
    )

    assert events == []


def test_finalize_publishes_unseen_output_without_rewriting_content() -> None:
    projector = _projector()
    events = projector.finalize(
        {
            "values": {"outputs": [_output(OUTPUT_ID_1, "Original answer")]},
            "interrupts": [],
            "checkpoint": {
                "thread_id": THREAD_ID,
                "checkpoint_id": "checkpoint-1",
                "checkpoint_ns": "",
                "checkpoint_map": {},
            },
        }
    )

    assert len(events) == 2
    assert isinstance(events[0], AgentOutputProduced)
    assert isinstance(events[0].output.parts[0], TextPart)
    assert events[0].output.parts[0].text == "Original answer"
    assert isinstance(events[1], AgentRunCompleted)
    assert events[1].output_ids == [OUTPUT_ID_1]
    assert projector.finalize({"values": {}, "interrupts": []}) == []


def test_finalize_interrupted_run_publishes_request_and_terminal() -> None:
    projector = _projector()
    events = projector.finalize(
        {
            "values": {},
            "checkpoint": {
                "thread_id": THREAD_ID,
                "checkpoint_id": "checkpoint-1",
                "checkpoint_ns": "supervisor",
                "checkpoint_map": {"root": "checkpoint-root"},
            },
            "interrupts": [
                {
                    "id": "interrupt-1",
                    "value": {
                        "prompt": "Approve this action?",
                        "input_schema": {"type": "boolean"},
                        "allowed_actions": ["approve", "reject"],
                    },
                }
            ],
        }
    )

    assert len(events) == 2
    assert isinstance(events[0], HumanInputRequested)
    assert events[0].resume_cursor.checkpoint_id == "checkpoint-1"
    assert isinstance(events[1], AgentRunInterrupted)
    assert events[1].interrupt_ids == ["interrupt-1"]


def test_fail_publishes_one_safe_terminal_event() -> None:
    projector = _projector()

    events = projector.fail(RuntimeError("secret provider details"))

    assert len(events) == 1
    assert isinstance(events[0], AgentRunFailed)
    assert events[0].error.code == "AGENT_RUN_FAILED"
    assert "secret" not in events[0].error.message
    assert projector.fail(RuntimeError("again")) == []


def test_terminal_paths_are_mutually_exclusive() -> None:
    completed = _projector()
    interrupted = _projector()
    failed = _projector()

    completed_events = completed.finalize({"values": {}, "interrupts": []})
    interrupted_events = interrupted.finalize(
        {
            "values": {},
            "checkpoint": {"checkpoint_id": "checkpoint-1"},
            "interrupts": [
                {
                    "id": "interrupt-1",
                    "value": {
                        "prompt": "Confirm",
                        "input_schema": {"type": "boolean"},
                    },
                }
            ],
        }
    )
    failed_events = failed.fail(RuntimeError("failed"))

    assert sum(isinstance(item, AgentRunCompleted) for item in completed_events) == 1
    assert (
        sum(isinstance(item, AgentRunInterrupted) for item in interrupted_events) == 1
    )
    assert sum(isinstance(item, AgentRunFailed) for item in failed_events) == 1


def test_metadata_and_checkpoint_events_update_internal_context_only() -> None:
    projector = AgentRunProjector(thread_id=THREAD_ID, clock=lambda: CREATED_AT)

    assert projector.process({"type": "metadata", "data": {}}) == []
    assert (
        projector.process(
            {
                "type": "checkpoints",
                "data": {
                    "config": {
                        "configurable": {
                            "checkpoint_id": "checkpoint-1",
                            "checkpoint_ns": "supervisor",
                            "checkpoint_map": {},
                        }
                    }
                },
            }
        )
        == []
    )
