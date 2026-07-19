"""State and update models for the File Ingest graph."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field
from shared_common.schemas.ai_agent import AgentOutput, RAGFileImportPayload


class FileIngestGraphNames(str, Enum):
    """Define compiled File Ingest graph identifiers."""

    FILE_INGEST = "file_ingest_graph"


class FileIngestChunk(BaseModel):
    """Represent one semantic chunk of the ingested file."""

    chunk_index: int = Field(
        description="Zero-based index of this chunk within the ingested document."
    )
    text: str = Field(
        description="Raw text segment content of this chunk."
    )
    vector: list[float] = Field(
        description="Embedding vector generated for this chunk's text."
    )


class FileIngestState(RAGFileImportPayload):
    """Represent input and internal state for the File Ingest graph."""

    text: str | None = Field(
        default=None,
        description="[Deprecated] Decoded text extracted from the ingested file. Use chunks instead.",
    )
    vector: list[float] | None = Field(
        default=None,
        description="[Deprecated] Embedding vector generated from the extracted text. Use chunks instead.",
    )
    chunks: list[FileIngestChunk] = Field(
        default_factory=list,
        description="List of semantic chunks and their embedding vectors.",
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

    chunks: list[FileIngestChunk] = Field(
        description="List of vectorized document chunks."
    )


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
