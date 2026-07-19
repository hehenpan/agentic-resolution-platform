"""State and update models for the File Ingest graph."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field
from shared_common.schemas.ai_agent import AgentOutput, RAGFileImportPayload


class FileIngestGraphNames(str, Enum):
    """Define compiled File Ingest graph identifiers."""

    FILE_INGEST = "file_ingest_graph"


class FileIngestState(RAGFileImportPayload):
    """Represent input and internal state for the File Ingest graph."""

    text: str | None = Field(
        default=None,
        description="Decoded text extracted from the ingested file.",
    )
    vector: list[float] | None = Field(
        default=None,
        description="Embedding vector generated from the extracted text.",
    )
    status: Literal["success"] | None = Field(
        default=None,
        description="File ingest completion status.",
    )
    outputs: list[AgentOutput] = Field(
        default_factory=list,
        description="Domain outputs produced by the File Ingest graph.",
    )


class VectorizeContentUpdate(BaseModel):
    """Represent the state update returned by vectorize_content."""

    text: str = Field(description="Decoded text extracted from file content.")
    vector: list[float] = Field(description="Embedding vector for the decoded text.")


class StoreInVectorDBUpdate(BaseModel):
    """Represent the state update returned by store_in_vector_db."""

    status: Literal["success"] = Field(
        description="Status indicating the vector payload was stored successfully."
    )


class BuildFileIngestOutputUpdate(BaseModel):
    """Represent the state update returned by build_file_ingest_output."""

    outputs: list[AgentOutput] = Field(
        description="Domain outputs produced after file ingest completes."
    )


class FileIngestOutput(BaseModel):
    """Represent the public output returned by the File Ingest graph."""

    outputs: list[AgentOutput] = Field(
        default_factory=list,
        description="Domain outputs returned by the File Ingest graph.",
    )
