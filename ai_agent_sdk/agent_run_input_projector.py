"""Project stable agent run requests into LangGraph SDK payloads."""

from langgraph_sdk.schema import Checkpoint, Command, Input
from pydantic import BaseModel, Field, JsonValue
from shared_common.schemas.ai_agent import (
    AgentCreateRunRequest,
    AgentRAGFileImportRequest,
    AgentResumeRequest,
    AgentTurnRequest,
)


class _AgentUserMessageInput(BaseModel):
    role: str = Field(
        default="user",
        description="LangChain chat role for the submitted message.",
    )
    content: str = Field(description="Plain text content for the user message.")
    additional_kwargs: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Additional LangChain message metadata.",
    )


class _AgentSupervisorInput(BaseModel):
    messages: list[_AgentUserMessageInput] = Field(
        description="Messages submitted to the supervisor graph."
    )


class AgentRunInputProjector:
    """Project stable agent service requests into LangGraph SDK payloads."""

    @staticmethod
    def project_create_run_input(
        request: AgentCreateRunRequest,
    ) -> Input | None:
        """Project an optional create-run message into LangGraph input."""
        if request.message is None:
            return None
        return _AgentSupervisorInput(
            messages=[
                _AgentUserMessageInput(
                    content=request.message.content,
                    additional_kwargs=request.message.metadata,
                )
            ]
        )

    @staticmethod
    def project_turn_input(
        request: AgentTurnRequest,
    ) -> Input:
        """Project an ordinary turn request into supervisor graph input."""
        return _AgentSupervisorInput(
            messages=[
                _AgentUserMessageInput(
                    content=request.message.content,
                    additional_kwargs=request.message.metadata,
                )
            ]
        )

    @staticmethod
    def project_resume_checkpoint(
        request: AgentResumeRequest,
    ) -> Checkpoint:
        """Project resume cursor information into a LangGraph checkpoint."""
        cursor = request.resume_cursor
        return {
            "thread_id": request.thread_id,
            "checkpoint_id": cursor.checkpoint_id,
            "checkpoint_ns": cursor.checkpoint_ns,
            "checkpoint_map": cursor.checkpoint_map,
        }

    @staticmethod
    def project_resume_command(
        request: AgentResumeRequest,
    ) -> Command:
        """Project a human input response into a LangGraph resume command."""
        return {
            "resume": {
                request.interrupt_id: request.response.response_data,
            }
        }

    @staticmethod
    def project_rag_file_import_input(
        request: AgentRAGFileImportRequest,
    ) -> Input:
        """Project a RAG file import request into file ingest graph input."""
        return request.payload.model_dump(mode="json")
