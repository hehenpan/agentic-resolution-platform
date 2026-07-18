"""Tests for Policy QA public output mapping."""

import pytest
from langchain_core.messages import AIMessage
from langgraph.runtime import ExecutionInfo, Runtime
from shared_common.schemas.ai_agent import AgentSourceType, SourcesPart, TextPart

from agent.core.logger import logger
from agent.supervisor.policy_qa.nodes import build_response
from agent.supervisor.policy_qa.outputs import build_policy_qa_output
from agent.supervisor.policy_qa.state import (
    BuildResponseUpdate,
    PolicyChunk,
    PolicyQAState,
)

IDENTITY_SCOPE = "task-1"


def _policy_chunk() -> PolicyChunk:
    return PolicyChunk(
        point_id=42,
        score=0.92,
        file_name="returns.md",
        text="Returns are accepted within 30 days.",
        payload={
            "file_name": "returns.md",
            "text": "Returns are accepted within 30 days.",
            "section": "eligibility",
        },
    )


def _runtime(task_id: str = IDENTITY_SCOPE) -> Runtime[None]:
    return Runtime(
        execution_info=ExecutionInfo(
            checkpoint_id="checkpoint-1",
            checkpoint_ns="",
            task_id=task_id,
        )
    )


def test_policy_qa_output_maps_text_and_policy_sources() -> None:
    draft = "The customer may return the product within 30 days."

    output = build_policy_qa_output(
        identity_scope=IDENTITY_SCOPE,
        text=draft,
        policy_chunks=[_policy_chunk()],
    )

    assert len(output.parts) == 2
    text_part = output.parts[0]
    sources_part = output.parts[1]
    assert isinstance(text_part, TextPart)
    assert text_part.text == draft
    assert isinstance(sources_part, SourcesPart)
    assert len(sources_part.sources) == 1

    source = sources_part.sources[0]
    assert source.source_id == "42"
    assert source.source_type == AgentSourceType.POLICY_RAG
    assert source.title == "returns.md"
    assert source.attributes == {
        "score": 0.92,
        "text": "Returns are accepted within 30 days.",
        "payload": {
            "file_name": "returns.md",
            "text": "Returns are accepted within 30 days.",
            "section": "eligibility",
        },
    }


def test_policy_qa_output_keeps_draft_only_in_text_part() -> None:
    draft = "A polished policy response."

    output = build_policy_qa_output(
        identity_scope=IDENTITY_SCOPE,
        text=draft,
        policy_chunks=[_policy_chunk()],
    )

    assert isinstance(output.parts[0], TextPart)
    assert output.parts[0].text == draft
    assert isinstance(output.parts[1], SourcesPart)
    assert draft not in output.parts[1].model_dump_json()


def test_policy_qa_output_supports_empty_sources() -> None:
    output = build_policy_qa_output(
        identity_scope=IDENTITY_SCOPE,
        text="No relevant policy was found.",
        policy_chunks=[],
    )

    assert isinstance(output.parts[1], SourcesPart)
    assert output.parts[1].sources == []


@pytest.mark.anyio
async def test_build_response_reuses_output_id_for_compatibility_message() -> None:
    state = PolicyQAState(
        draft="The customer may return the product within 30 days.",
        policy_chunks=[_policy_chunk()],
    )

    raw_update = await build_response(state, _runtime())
    update = BuildResponseUpdate.model_validate(raw_update)

    response = AIMessage.model_validate(raw_update["messages"][0])
    assert response.id is not None
    assert response.id == update.outputs[0].output_id
    assert response.response_metadata["policy_chunks"]
    assert isinstance(update.outputs[0].parts[0], TextPart)
    assert update.outputs[0].parts[0].text == state.draft


@pytest.mark.anyio
async def test_build_response_logs_and_fails_without_task_id() -> None:
    messages: list[str] = []
    sink_id = logger.add(messages.append, format="{level}:{message}")

    try:
        with pytest.raises(RuntimeError, match="requires a task ID"):
            await build_response(PolicyQAState(), _runtime(""))
    finally:
        logger.remove(sink_id)

    assert any(
        message.strip() == "ERROR:Policy response generation requires a graph task ID"
        for message in messages
    )
