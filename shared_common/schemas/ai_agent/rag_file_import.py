"""Schemas for public RAG file import results."""

from typing import Literal

from pydantic import BaseModel, Field


class RAGFileImportResult(BaseModel):
    """Represent one successfully indexed RAG file."""

    file_id: int = Field(
        description="Identifier of the file stored in the RAG vector collection."
    )
    file_name: str = Field(
        min_length=1,
        description="Name of the file stored in the RAG vector collection.",
    )
    status: Literal["success"] = Field(
        default="success",
        description="Successful terminal status of the file import result.",
    )
