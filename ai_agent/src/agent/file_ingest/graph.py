from langgraph.graph import StateGraph
from agent.core.checkpoint import LazyAsyncSqliteSaver
from agent.core.config import settings
from agent.file_ingest.state import FileIngestState
from agent.file_ingest.nodes import vectorize_content, store_in_vector_db, FileIngestNodes

# Define and assemble the StateGraph using the node name enum
builder = StateGraph(FileIngestState)
builder.add_node(FileIngestNodes.VECTORIZE_CONTENT, vectorize_content)
builder.add_node(FileIngestNodes.STORE_IN_VECTOR_DB, store_in_vector_db)

builder.add_edge("__start__", FileIngestNodes.VECTORIZE_CONTENT)
builder.add_edge(FileIngestNodes.VECTORIZE_CONTENT, FileIngestNodes.STORE_IN_VECTOR_DB)
builder.add_edge(FileIngestNodes.STORE_IN_VECTOR_DB, "__end__")

# Initialize SQLite database checkpointer
memory = LazyAsyncSqliteSaver(settings.DB_FILE)

# Compile the final graph
file_ingest_graph = builder.compile(
    name="file ingest graph",
    checkpointer=memory
)
