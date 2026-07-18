"""Stable LangGraph assistant identifiers used by AI Agent clients."""

from enum import Enum


class AgentAssistantId(str, Enum):
    """Identify LangGraph assistants exposed by the AI Agent service."""

    SUPERVISOR = "supervisor_graph"
    FILE_INGEST = "file_ingester"
