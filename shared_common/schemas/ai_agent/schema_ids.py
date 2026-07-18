"""Stable schema identifiers for structured AI Agent outputs."""

from enum import Enum


class AgentOutputSchemaId(str, Enum):
    """Identify versioned structured agent output schemas."""

    RAG_FILE_IMPORT_RESULT_V1 = "rag.file_import.result.v1"
