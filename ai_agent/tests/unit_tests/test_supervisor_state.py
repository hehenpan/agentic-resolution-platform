"""Tests for supervisor state reducers and subgraph boundaries."""

from shared_common.schemas.ai_agent import AgentOutput, TextPart

from agent.supervisor.state import merge_agent_outputs


def _output(output_id: str, text: str) -> AgentOutput:
    return AgentOutput(
        output_id=output_id,
        parts=[TextPart(text=text)],
    )


def test_merge_agent_outputs_deduplicates_by_output_id() -> None:
    first = _output(
        "11111111-1111-5111-8111-111111111111",
        "First version",
    )
    replacement = _output(
        "11111111-1111-5111-8111-111111111111",
        "Replacement version",
    )
    second = _output(
        "22222222-2222-5222-8222-222222222222",
        "Second output",
    )

    merged = merge_agent_outputs([first], [replacement, second])

    assert [output.output_id for output in merged] == [
        first.output_id,
        second.output_id,
    ]
    assert merged[0].parts[0].text == "Replacement version"


def test_merge_agent_outputs_does_not_mutate_inputs() -> None:
    first = _output(
        "11111111-1111-5111-8111-111111111111",
        "First output",
    )
    second = _output(
        "22222222-2222-5222-8222-222222222222",
        "Second output",
    )
    existing = [first]
    updates = [second]

    merge_agent_outputs(existing, updates)

    assert existing == [first]
    assert updates == [second]


def test_merge_agent_outputs_validates_serialized_updates() -> None:
    output = _output(
        "11111111-1111-5111-8111-111111111111",
        "Serialized output",
    )

    merged = merge_agent_outputs([], [output.model_dump(mode="json")])

    assert merged == [output]
