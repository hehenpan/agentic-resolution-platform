"""Tests for shared agent domain event contracts."""

from collections.abc import Callable
import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from shared_common.schemas.ai_agent import (
    AgentDomainEvent,
    AgentDomainEventBase,
    AgentError,
    AgentOutput,
    AgentOutputProduced,
    AgentProgressReported,
    AgentProgressStatus,
    AgentResumeCursor,
    AgentRunCompleted,
    AgentRunFailed,
    AgentRunInterrupted,
    AgentSourceType,
    HumanInputRequest,
    HumanInputRequested,
    SourceReference,
    SourcesPart,
    StructuredDataPart,
    TextPart,
)

EVENT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OUTPUT_ID = "bbbbbbbb-bbbb-5bbb-8bbb-bbbbbbbbbbbb"
CREATED_AT = 1_725_000_000

EVENT_MODELS: tuple[type[BaseModel], ...] = (
    AgentDomainEventBase,
    AgentOutputProduced,
    AgentProgressReported,
    HumanInputRequested,
    AgentRunCompleted,
    AgentRunInterrupted,
    AgentError,
    AgentRunFailed,
)


def _event_fields() -> dict[str, object]:
    return {
        "event_id": EVENT_ID,
        "thread_id": "thread-1",
        "sequence": 1,
        "source_sequences": [4, 5],
        "created_at": CREATED_AT,
    }


def _agent_output() -> AgentOutput:
    return AgentOutput(
        output_id=OUTPUT_ID,
        parts=[
            TextPart(text="The policy permits returns within 30 days."),
            StructuredDataPart(
                schema_id="test.structured_data.v1",
                data={"result": "validated"},
            ),
            SourcesPart(
                sources=[
                    SourceReference(
                        source_id="policy-point-1",
                        source_type=AgentSourceType.POLICY_RAG,
                        title="returns.md",
                    )
                ]
            ),
        ],
    )


@pytest.mark.parametrize("model", EVENT_MODELS)
def test_domain_event_fields_have_descriptions(model: type[BaseModel]) -> None:
    missing_descriptions = [
        field_name
        for field_name, field in model.model_fields.items()
        if not field.description
    ]

    assert missing_descriptions == []


def _domain_events() -> list[
    AgentOutputProduced
    | AgentProgressReported
    | HumanInputRequested
    | AgentRunCompleted
    | AgentRunInterrupted
    | AgentRunFailed
]:
    return [
        AgentOutputProduced(
            **_event_fields(),
            output=_agent_output(),
        ),
        AgentProgressReported(
            **_event_fields(),
            operation="policy_retrieval",
            status=AgentProgressStatus.IN_PROGRESS,
            current=1,
            total=3,
            details={"message": "Searching policy documents"},
        ),
        HumanInputRequested(
            **_event_fields(),
            interrupt_id="interrupt-1",
            request=HumanInputRequest(
                prompt="Approve this action?",
                input_schema={
                    "type": "object",
                    "properties": {
                        "approved": {"type": "boolean"},
                    },
                    "required": ["approved"],
                },
                context={"reason": "manual_review"},
                allowed_actions=["approve", "reject"],
            ),
            resume_cursor=AgentResumeCursor(
                checkpoint_id="checkpoint-1",
                checkpoint_ns="policy_qa",
                checkpoint_map={"parent": "checkpoint-parent"},
            ),
        ),
        AgentRunCompleted(
            **_event_fields(),
            output_ids=[OUTPUT_ID],
        ),
        AgentRunInterrupted(
            **_event_fields(),
            interrupt_ids=["interrupt-1"],
        ),
        AgentRunFailed(
            **_event_fields(),
            error=AgentError(
                code="AGENT_EXECUTION_FAILED",
                message="The request could not be completed.",
                retryable=True,
                details={"stage": "policy_retrieval"},
            ),
        ),
    ]


@pytest.mark.parametrize("event", _domain_events())
def test_domain_event_round_trips_through_discriminated_union(
    event: AgentOutputProduced
    | AgentProgressReported
    | HumanInputRequested
    | AgentRunCompleted
    | AgentRunInterrupted
    | AgentRunFailed,
) -> None:
    adapter = TypeAdapter(AgentDomainEvent)

    restored = adapter.validate_json(event.model_dump_json())

    assert restored == event
    assert restored.schema_version == "1"


def test_domain_event_rejects_unknown_kind() -> None:
    adapter = TypeAdapter(AgentDomainEvent)
    payload = {
        **_event_fields(),
        "kind": "agent.unknown",
    }

    with pytest.raises(ValidationError):
        adapter.validate_python(payload)


@pytest.mark.parametrize(
    "required_field",
    ["event_id", "thread_id", "sequence", "created_at"],
)
def test_domain_event_rejects_missing_envelope_field(
    required_field: str,
) -> None:
    adapter = TypeAdapter(AgentDomainEvent)
    payload = AgentRunCompleted(
        **_event_fields(),
        output_ids=[OUTPUT_ID],
    ).model_dump(mode="json")
    del payload[required_field]

    with pytest.raises(ValidationError):
        adapter.validate_python(payload)


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("event_id", ""),
        ("thread_id", ["invalid-thread"]),
    ],
)
def test_domain_event_rejects_invalid_envelope_field_type(
    field_name: str,
    invalid_value: object,
) -> None:
    payload = {
        **_event_fields(),
        field_name: invalid_value,
        "output_ids": [],
    }

    with pytest.raises(ValidationError):
        AgentRunCompleted.model_validate(payload)


def test_domain_event_rejects_payload_for_different_kind() -> None:
    adapter = TypeAdapter(AgentDomainEvent)
    payload = {
        **_event_fields(),
        "kind": "agent.output_produced",
        "output_ids": [str(OUTPUT_ID)],
    }

    with pytest.raises(ValidationError):
        adapter.validate_python(payload)


@pytest.mark.parametrize("sequence", [-1, 1.5, "1", True])
def test_domain_event_rejects_invalid_sequence(sequence: object) -> None:
    payload = {
        **_event_fields(),
        "sequence": sequence,
        "output_ids": [],
    }

    with pytest.raises(ValidationError):
        AgentRunCompleted.model_validate(payload)


def test_domain_event_rejects_negative_source_sequence() -> None:
    payload = {
        **_event_fields(),
        "source_sequences": [1, -1],
        "output_ids": [],
    }

    with pytest.raises(ValidationError):
        AgentRunCompleted.model_validate(payload)


@pytest.mark.parametrize("created_at", [-1, 1.5, "1725000000", True])
def test_domain_event_rejects_invalid_created_at(created_at: object) -> None:
    payload = {
        **_event_fields(),
        "created_at": created_at,
        "output_ids": [],
    }

    with pytest.raises(ValidationError):
        AgentRunCompleted.model_validate(payload)


def test_output_produced_preserves_heterogeneous_parts() -> None:
    adapter = TypeAdapter(AgentDomainEvent)
    event = AgentOutputProduced(
        **_event_fields(),
        output=_agent_output(),
    )

    restored = adapter.validate_json(event.model_dump_json())

    assert isinstance(restored, AgentOutputProduced)
    assert isinstance(restored.output.parts[0], TextPart)
    assert isinstance(restored.output.parts[1], StructuredDataPart)
    assert isinstance(restored.output.parts[2], SourcesPart)


def test_human_input_request_and_resume_cursor_round_trip() -> None:
    event = HumanInputRequested(
        **_event_fields(),
        interrupt_id="interrupt-1",
        request=HumanInputRequest(
            prompt="Provide a reason.",
            input_schema={"type": "string"},
            context={"order_id": "order-1"},
            allowed_actions=["submit"],
        ),
        resume_cursor=AgentResumeCursor(
            checkpoint_id="checkpoint-1",
            checkpoint_map={"root": "checkpoint-root"},
        ),
    )

    restored = HumanInputRequested.model_validate_json(event.model_dump_json())

    assert restored == event
    assert restored.resume_cursor.checkpoint_ns == ""


@pytest.mark.parametrize(
    "event_factory",
    [
        lambda: AgentProgressReported(
            **_event_fields(),
            operation="policy_retrieval",
            status=AgentProgressStatus.STARTED,
            details={"invalid": object()},
        ),
        lambda: HumanInputRequested(
            **_event_fields(),
            interrupt_id="interrupt-1",
            request=HumanInputRequest(
                prompt="Provide input.",
                input_schema={"invalid": object()},
            ),
            resume_cursor=AgentResumeCursor(checkpoint_id="checkpoint-1"),
        ),
        lambda: AgentRunFailed(
            **_event_fields(),
            error=AgentError(
                code="FAILED",
                message="Failed safely.",
                details={"invalid": object()},
            ),
        ),
    ],
)
def test_domain_event_json_fields_reject_non_json_values(
    event_factory: Callable[[], object],
) -> None:
    with pytest.raises(ValidationError):
        event_factory()


def test_domain_event_defaults_source_sequences() -> None:
    event = AgentRunCompleted(
        event_id=EVENT_ID,
        thread_id="thread-1",
        sequence=0,
        created_at=CREATED_AT,
    )

    assert event.source_sequences == []
    assert event.output_ids == []
