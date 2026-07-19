"""Requests accepted by AI Agent service operations."""

from pydantic import BaseModel, Field, JsonValue

from shared_common.schemas.ai_agent.human_input import (
    AgentResumeCursor,
    HumanInputResponse,
)


class UserMessageInput(BaseModel):
    """Represent one user message submitted to the agent service."""

    content: str = Field(description="Plain text content submitted by the user.")
    metadata: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Optional user message metadata forwarded to the agent run.",
    )


class AgentTurnRequest(BaseModel):
    """Request one ordinary turn in an existing agent thread."""

    thread_id: str = Field(description="Agent thread ID for the conversation.")
    message: UserMessageInput = Field(
        description="User message payload for this agent turn."
    )


class AgentResumeRequest(BaseModel):
    """Request resumption of an interrupted agent execution stage."""

    thread_id: str = Field(description="Agent thread ID that owns the interrupt.")
    interrupt_id: str = Field(description="LangGraph interrupt ID to resume.")
    resume_cursor: AgentResumeCursor = Field(
        description="Checkpoint cursor used to resume the interrupted run."
    )
    response: HumanInputResponse = Field(
        description="Human response payload used as the resume value."
    )


class RAGFileImportPayload(BaseModel):
    """Request ingestion of one file into the agent RAG store."""

    file_id: int = Field(..., description="Unique file ID")
    file_name: str = Field(..., description="Name of the file")
    file_size: int = Field(..., description="Size of the file in bytes")
    file_owner_id: int = Field(..., description="File owner user ID")
    file_tenant_id: int = Field(..., description="File tenant ID")
    file_content: bytes = Field(..., description="File content")
    extra_meta: dict[str, JsonValue] | None = Field(
        default_factory=dict,
        description="Additional metadata context",
    )
    extra_context: dict[str, JsonValue] | None = Field(
        default_factory=dict,
        description="Additional execution context",
    )


class AgentRAGFileImportRequest(BaseModel):
    """Request one observable RAG file import operation."""

    thread_id: str = Field(
        min_length=1,
        description="LangGraph thread dedicated to this file import operation.",
    )
    payload: RAGFileImportPayload = Field(
        description="File content and metadata submitted to the File Ingest graph."
    )
