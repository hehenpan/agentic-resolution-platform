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

    text: str | None = None
    vector: list[float] | None = None
    status: Literal["success"] | None = None
    outputs: list[AgentOutput] = Field(default_factory=list)


class VectorizeContentUpdate(BaseModel):
    """Represent the state update returned by vectorize_content."""

    text: str
    vector: list[float]


class StoreInVectorDBUpdate(BaseModel):
    """Represent the state update returned by store_in_vector_db."""

    status: Literal["success"]


class BuildFileIngestOutputUpdate(BaseModel):
    """Represent the state update returned by build_file_ingest_output."""

    outputs: list[AgentOutput]


class FileIngestOutput(BaseModel):
    """Represent the public output returned by the File Ingest graph."""

    outputs: list[AgentOutput] = Field(default_factory=list)
