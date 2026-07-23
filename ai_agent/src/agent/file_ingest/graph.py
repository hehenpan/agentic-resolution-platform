"""File Ingest graph assembly."""

from langgraph.graph import END, START, StateGraph

from agent.core.checkpoint import get_checkpointer
from agent.core.config import settings
from agent.file_ingest.nodes import (
    FileIngestNodeNames,
    build_file_ingest_output,
    store_in_vector_db,
    vectorize_content,
)
from agent.file_ingest.state import (
    FileIngestGraphNames,
    FileIngestOutput,
    FileIngestState,
)

builder = StateGraph(
    FileIngestState,
    output_schema=FileIngestOutput,
)
builder.add_node(FileIngestNodeNames.VECTORIZE_CONTENT, vectorize_content)
builder.add_node(FileIngestNodeNames.STORE_IN_VECTOR_DB, store_in_vector_db)
builder.add_node(
    FileIngestNodeNames.BUILD_FILE_INGEST_OUTPUT,
    build_file_ingest_output,
)

builder.add_edge(START, FileIngestNodeNames.VECTORIZE_CONTENT)
builder.add_edge(
    FileIngestNodeNames.VECTORIZE_CONTENT,
    FileIngestNodeNames.STORE_IN_VECTOR_DB,
)
builder.add_edge(
    FileIngestNodeNames.STORE_IN_VECTOR_DB,
    FileIngestNodeNames.BUILD_FILE_INGEST_OUTPUT,
)
builder.add_edge(FileIngestNodeNames.BUILD_FILE_INGEST_OUTPUT, END)

memory = get_checkpointer(settings.DB_FILE)

file_ingest_graph = builder.compile(
    name=FileIngestGraphNames.FILE_INGEST.value,
    checkpointer=memory,
)
