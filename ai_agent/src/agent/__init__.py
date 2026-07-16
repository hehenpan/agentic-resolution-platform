"""New LangGraph Agent.

This module defines a custom graph.
"""

from agent.example_graph import example_graph
from agent.file_ingest import file_ingest_graph
from agent.supervisor import supervisor_graph

__all__ = ["example_graph", "file_ingest_graph", "supervisor_graph"]
