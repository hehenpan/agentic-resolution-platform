"""Tests for projecting agent service requests into LangGraph SDK payloads."""

from pydantic import BaseModel
from shared_common.schemas.ai_agent import (
    AgentCreateRunRequest,
    AgentRAGFileImportRequest,
    AgentResumeCursor,
    AgentResumeRequest,
    AgentTurnRequest,
    HumanInputResponse,
    RAGFileImportPayload,
    UserMessageInput,
)

from ai_agent_sdk.agent_run_input_projector import AgentRunInputProjector


def test_create_run_without_message_projects_no_input() -> None:
    request = AgentCreateRunRequest(
        thread_id="thread-1",
        assistant_id="supervisor_graph",
    )

    assert AgentRunInputProjector.project_create_run_input(request) is None


def test_create_run_with_message_projects_supervisor_input() -> None:
    request = AgentCreateRunRequest(
        thread_id="thread-1",
        assistant_id="supervisor_graph",
        message=UserMessageInput(
            content="Hello",
            metadata={"channel": "support"},
        ),
    )

    result = AgentRunInputProjector.project_create_run_input(request)

    assert isinstance(result, BaseModel)
    assert result.model_dump() == {
        "messages": [
            {
                "role": "user",
                "content": "Hello",
                "additional_kwargs": {"channel": "support"},
            }
        ]
    }


def test_turn_projects_supervisor_input() -> None:
    request = AgentTurnRequest(
        thread_id="thread-1",
        message=UserMessageInput(
            content="What is my order status?",
            metadata={"locale": "en-US"},
        ),
    )

    result = AgentRunInputProjector.project_turn_input(request)

    assert isinstance(result, BaseModel)
    assert result.model_dump() == {
        "messages": [
            {
                "role": "user",
                "content": "What is my order status?",
                "additional_kwargs": {"locale": "en-US"},
            }
        ]
    }


def test_resume_projects_checkpoint_and_command() -> None:
    request = AgentResumeRequest(
        thread_id="thread-1",
        run_id="run-1",
        interrupt_id="interrupt-1",
        resume_cursor=AgentResumeCursor(
            checkpoint_id="checkpoint-1",
            checkpoint_ns="supervisor",
            checkpoint_map={"root": "checkpoint-root"},
        ),
        response=HumanInputResponse(
            schema_id="human_input.get_user.v1",
            response_data={"email": "shopper@example.com"},
        ),
    )

    assert AgentRunInputProjector.project_resume_checkpoint(request) == {
        "thread_id": "thread-1",
        "checkpoint_id": "checkpoint-1",
        "checkpoint_ns": "supervisor",
        "checkpoint_map": {"root": "checkpoint-root"},
    }
    assert AgentRunInputProjector.project_resume_command(request) == {
        "resume": {
            "interrupt-1": {"email": "shopper@example.com"},
        }
    }


def test_rag_file_import_projects_payload_with_json_mode() -> None:
    request = AgentRAGFileImportRequest(
        thread_id="rag-thread-1",
        payload=RAGFileImportPayload(
            file_id=1,
            file_name="policy.txt",
            file_size=5,
            file_owner_id=10,
            file_tenant_id=20,
            file_content=b"hello",
            extra_meta={"source": "unit-test"},
            extra_context={"project": "agent-platform"},
        ),
    )

    result = AgentRunInputProjector.project_rag_file_import_input(request)

    assert result == request.payload.model_dump(mode="json")
    assert result["file_id"] == 1
    assert result["file_content"] == "aGVsbG8="
