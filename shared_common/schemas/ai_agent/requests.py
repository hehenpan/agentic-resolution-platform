"""Requests accepted by AI Agent service operations."""

from pydantic import BaseModel, Field, JsonValue

from shared_common.schemas.ai_agent.enums import AgentRunStatus
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
    run_id: str | None = Field(
        default=None,
        description="Optional pre-created LangGraph run ID. If omitted, created implicitly.",
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
    run_id: str | None = Field(
        default=None,
        description="Optional pre-created LangGraph run ID. If omitted, created implicitly.",
    )


class AgentCreateRunRequest(BaseModel):
    """Request explicit creation of a background agent run."""

    thread_id: str = Field(
        min_length=1,
        description="LangGraph thread ID that will execute the run.",
    )
    assistant_id: str = Field(
        default="supervisor_graph",
        description="Assistant/Graph identifier to execute (e.g. 'supervisor_graph').",
    )
    message: UserMessageInput | None = Field(
        default=None,
        description="Optional initial user message to trigger the run immediately.",
    )


class AgentCreateRunResponse(BaseModel):
    """Response returned after creating an agent run."""

    run_id: str = Field(
        min_length=1,
        description="Generated unique LangGraph run ID.",
    )
    thread_id: str = Field(
        min_length=1,
        description="LangGraph thread ID associated with the run.",
    )
    status: AgentRunStatus = Field(
        description="Initial status of the created run (e.g. 'pending', 'running').",
    )



class AgentJoinStreamRequest(BaseModel):
    """Request joining an active or completed run stream by run_id."""

    thread_id: str = Field(
        min_length=1,
        description="LangGraph thread ID that owns the run.",
    )
    run_id: str = Field(
        min_length=1,
        description="Active or target LangGraph run ID to stream from.",
    )


class AgentGetStateEventsRequest(BaseModel):
    """Request historical domain events projected from thread state."""

    thread_id: str = Field(
        min_length=1,
        description="LangGraph thread ID to query state for.",
    )
    run_id: str | None = Field(
        default=None,
        description="Optional run_id to attach to projected historical events.",
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


class AgentListRunsRequest(BaseModel):
    """Request listing of runs associated with a thread."""

    thread_id: str = Field(
        min_length=1,
        description="LangGraph thread ID to query runs for.",
    )


class AgentRunObject(BaseModel):
    """Represent an individual agent run's status and metadata."""

    run_id: str = Field(
        min_length=1,
        description="LangGraph run ID.",
    )
    thread_id: str = Field(
        min_length=1,
        description="LangGraph thread ID associated with the run.",
    )
    status: AgentRunStatus = Field(
        description="Current status of the run (e.g. 'pending', 'running', 'success', 'error', 'interrupted').",
    )
    metadata: dict[str, JsonValue] = Field(
        default_factory=dict,
        description="Optional metadata associated with the run.",
    )



class AgentListRunsResponse(BaseModel):
    """Response containing the list of agent runs for a thread."""

    runs: list[AgentRunObject] = Field(
        default_factory=list,
        description="List of agent runs on the thread.",
    )

