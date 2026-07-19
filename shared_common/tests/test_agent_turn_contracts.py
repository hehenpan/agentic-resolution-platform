"""Tests for ordinary turn and interrupted-run resume contracts."""

import pytest
from pydantic import BaseModel, ValidationError

from shared_common.schemas.ai_agent import (
    AgentRAGFileImportRequest,
    AgentResumeCursor,
    AgentResumeRequest,
    AgentTurnRequest,
    HumanInputRequest,
    HumanInputResponse,
    RAGFileImportPayload,
    UserMessageInput,
)

HUMAN_INPUT_MODELS: tuple[type[BaseModel], ...] = (
    HumanInputRequest,
    AgentResumeCursor,
    HumanInputResponse,
)


@pytest.mark.parametrize("model", HUMAN_INPUT_MODELS)
def test_human_input_fields_have_descriptions(model: type[BaseModel]) -> None:
    missing_descriptions = [
        field_name
        for field_name, field in model.model_fields.items()
        if not field.description
    ]

    assert missing_descriptions == []


def test_agent_turn_request_round_trips() -> None:
    request = AgentTurnRequest(
        thread_id="thread-1",
        message=UserMessageInput(
            content="What is the return policy?",
            metadata={"channel": "customer_service", "priority": 1},
        ),
    )

    restored = AgentTurnRequest.model_validate_json(request.model_dump_json())

    assert restored == request


def test_follow_up_turn_reuses_same_thread_contract() -> None:
    first_turn = AgentTurnRequest(
        thread_id="thread-1",
        message=UserMessageInput(content="What is the return policy?"),
    )
    follow_up_turn = AgentTurnRequest(
        thread_id=first_turn.thread_id,
        message=UserMessageInput(content="What if the item was opened?"),
    )

    assert follow_up_turn.thread_id == first_turn.thread_id


@pytest.mark.parametrize(
    "payload",
    [
        {"message": {"content": "Missing thread"}},
        {"thread_id": "thread-1"},
        {"thread_id": "thread-1", "message": {}},
    ],
)
def test_agent_turn_request_rejects_missing_required_fields(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        AgentTurnRequest.model_validate(payload)


def test_agent_turn_request_rejects_non_json_metadata() -> None:
    with pytest.raises(ValidationError):
        AgentTurnRequest(
            thread_id="thread-1",
            message=UserMessageInput(
                content="What is the return policy?",
                metadata={"invalid": object()},
            ),
        )


def test_agent_resume_request_round_trips() -> None:
    request = AgentResumeRequest(
        thread_id="thread-1",
        interrupt_id="interrupt-1",
        resume_cursor=AgentResumeCursor(
            checkpoint_id="checkpoint-1",
            checkpoint_ns="policy_qa",
            checkpoint_map={"parent": "checkpoint-parent"},
        ),
        response=HumanInputResponse(
            schema_id="human_input.approve_action.v1",
            response_data={
                "approved": True,
                "note": "Proceed with the request.",
            }
        ),
    )

    restored = AgentResumeRequest.model_validate_json(request.model_dump_json())

    assert restored == request


@pytest.mark.parametrize(
    "payload",
    [
        {
            "interrupt_id": "interrupt-1",
            "resume_cursor": {"checkpoint_id": "checkpoint-1"},
            "response": {"data": True},
        },
        {
            "thread_id": "thread-1",
            "resume_cursor": {"checkpoint_id": "checkpoint-1"},
            "response": {"data": True},
        },
        {
            "thread_id": "thread-1",
            "interrupt_id": "interrupt-1",
            "response": {"data": True},
        },
        {
            "thread_id": "thread-1",
            "interrupt_id": "interrupt-1",
            "resume_cursor": {"checkpoint_id": "checkpoint-1"},
        },
    ],
)
def test_agent_resume_request_rejects_missing_required_fields(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        AgentResumeRequest.model_validate(payload)


def test_agent_resume_request_rejects_non_json_response() -> None:
    with pytest.raises(ValidationError):
        AgentResumeRequest(
            thread_id="thread-1",
            interrupt_id="interrupt-1",
            resume_cursor=AgentResumeCursor(checkpoint_id="checkpoint-1"),
            response=HumanInputResponse(
                schema_id="human_input.approve_action.v1",
                response_data=object(),
            ),
        )


def test_resume_cursor_uses_safe_defaults() -> None:
    cursor = AgentResumeCursor(checkpoint_id="checkpoint-1")

    assert cursor.checkpoint_ns == ""
    assert cursor.checkpoint_map == {}


def test_rag_file_import_request_round_trips() -> None:
    request = AgentRAGFileImportRequest(
        thread_id="rag-import:1:operation-1",
        payload=RAGFileImportPayload(
            file_id=1,
            file_name="policy.md",
            file_size=6,
            file_owner_id=2,
            file_tenant_id=3,
            file_content=b"policy",
        ),
    )

    restored = AgentRAGFileImportRequest.model_validate_json(
        request.model_dump_json()
    )

    assert restored == request


def test_rag_file_import_request_rejects_empty_thread_id() -> None:
    with pytest.raises(ValidationError):
        AgentRAGFileImportRequest(
            thread_id="",
            payload=RAGFileImportPayload(
                file_id=1,
                file_name="policy.md",
                file_size=6,
                file_owner_id=2,
                file_tenant_id=3,
                file_content=b"policy",
            ),
        )


def test_rag_file_import_request_fields_have_descriptions() -> None:
    assert all(
        field.description
        for field in AgentRAGFileImportRequest.model_fields.values()
    )
