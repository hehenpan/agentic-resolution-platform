"""Tests for the public agent output envelope and content parts."""

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from shared_common.schemas.ai_agent import (
    AgentOutput,
    AgentOutputPart,
    AgentOutputPartKind,
    AgentOutputSchemaId,
    AgentSourceType,
    RAGFileImportResult,
    SourceReference,
    SourcesPart,
    StructuredDataPart,
    TextPart,
    UnixTimestamp,
)

OUTPUT_MODELS: tuple[type[BaseModel], ...] = (
    TextPart,
    StructuredDataPart,
    SourceReference,
    SourcesPart,
    AgentOutput,
    RAGFileImportResult,
)


@pytest.mark.parametrize("model", OUTPUT_MODELS)
def test_agent_output_fields_have_descriptions(model: type[BaseModel]) -> None:
    missing_descriptions = [
        field_name
        for field_name, field in model.model_fields.items()
        if not field.description
    ]

    assert missing_descriptions == []


@pytest.mark.parametrize(
    "part",
    [
        TextPart(text="The relevant policy was found."),
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
def test_agent_output_part_validates_each_supported_kind(
    part: TextPart | StructuredDataPart | SourcesPart,
) -> None:
    adapter = TypeAdapter(AgentOutputPart)

    validated = adapter.validate_python(part.model_dump(mode="json"))

    assert validated == part


def test_agent_output_part_rejects_unknown_discriminator() -> None:
    adapter = TypeAdapter(AgentOutputPart)

    with pytest.raises(ValidationError):
        adapter.validate_python({"kind": "artifact", "uri": "result.csv"})


def test_agent_output_round_trips_heterogeneous_parts() -> None:
    output = AgentOutput(
        output_id="0f79ea87-f196-5bd7-89f7-1e5d55221de2",
        parts=[
            TextPart(text="The policy permits returns within 30 days."),
            StructuredDataPart(
                schema_id="test.structured_data.v1",
                data={"result": {"status": "validated"}},
            ),
            SourcesPart(
                sources=[
                    SourceReference(
                        source_id="policy-point-1",
                        source_type=AgentSourceType.POLICY_RAG,
                        title="returns.md",
                        attributes={
                            "score": 0.92,
                            "text": "Returns are accepted within 30 days.",
                        },
                    )
                ]
            ),
        ],
    )

    restored = AgentOutput.model_validate_json(output.model_dump_json())

    assert restored == output
    assert [part.kind for part in restored.parts] == [
        AgentOutputPartKind.TEXT,
        AgentOutputPartKind.STRUCTURED_DATA,
        AgentOutputPartKind.SOURCES,
    ]


def test_structured_data_part_preserves_unregistered_schema() -> None:
    part = StructuredDataPart(
        schema_id="test.future_payload.v1",
        data={"future_field": "preserved"},
    )

    assert part.schema_id == "test.future_payload.v1"
    assert part.data == {"future_field": "preserved"}


def test_rag_file_import_schema_id_is_stable() -> None:
    assert (
        AgentOutputSchemaId.RAG_FILE_IMPORT_RESULT_V1.value
        == "rag.file_import.result.v1"
    )


def test_source_attributes_reject_non_json_value() -> None:
    with pytest.raises(ValidationError):
        SourceReference(
            source_id="policy-point-1",
            source_type=AgentSourceType.POLICY_RAG,
            attributes={"invalid": object()},
        )


def test_source_reference_rejects_unknown_source_type() -> None:
    with pytest.raises(ValidationError):
        SourceReference(
            source_id="unknown-source",
            source_type="database",
        )


@pytest.mark.parametrize("timestamp", [0, 1, 1_725_000_000])
def test_unix_timestamp_accepts_non_negative_integer(timestamp: int) -> None:
    adapter = TypeAdapter(UnixTimestamp)

    assert adapter.validate_python(timestamp) == timestamp


@pytest.mark.parametrize("timestamp", [-1, 1.5, "1725000000", True])
def test_unix_timestamp_rejects_invalid_value(timestamp: object) -> None:
    adapter = TypeAdapter(UnixTimestamp)

    with pytest.raises(ValidationError):
        adapter.validate_python(timestamp)
