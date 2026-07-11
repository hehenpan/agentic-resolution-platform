from typing import Optional, List, Dict, Any
from langgraph.graph import StateGraph
from agent.core.checkpoint import LazyAsyncSqliteSaver
from agent.core.config import settings
from agent.core.logger import logger
from agent.core.constants import QDRANT_COLLECTION_RAG
from agent.core.vectordb import get_vector_db, VectorPoint, RAGFileVectorPayload
from agent.core.embedding import get_embedding_model
from shared_common.schemas_ai_agent import RAGFileImportPayload

class FileIngestState(RAGFileImportPayload):
    """
    LangGraph state schema for the file ingestion workflow.
    Inherits payload fields from RAGFileImportPayload and adds 
    intermediate/output state variables.
    """
    text: Optional[str] = None
    vector: Optional[List[float]] = None
    status: Optional[str] = None


async def vectorize_content(state: FileIngestState) -> Dict[str, Any]:
    """
    Asynchronously decodes the file contents and generates a high-dimensional 
    embedding vector via the abstract EmbeddingModel.
    """
    logger.info(f"Vectorizing content for file_id: {state.file_id}")
    
    file_content = state.file_content
    if not isinstance(file_content, bytes):
        if isinstance(file_content, str):
            text = file_content
        else:
            text = str(file_content)
    else:
        text = file_content.decode("utf-8", errors="ignore")
        
    embedding_model = get_embedding_model()
    vector = await embedding_model.aembed_query(text)
    
    return {"text": text, "vector": vector}


async def store_in_vector_db(state: FileIngestState) -> Dict[str, Any]:
    """
    Stores the generated embedding vector and metadata payload inside the 
    vector database via the abstract VectorDB client.
    """
    logger.info(f"Storing file_id {state.file_id} in vector DB collection '{QDRANT_COLLECTION_RAG}'")
    
    db = get_vector_db()
    
    # Instantiate Pydantic model for type-safe metadata
    vector_payload = RAGFileVectorPayload(
        file_id=state.file_id,
        file_name=state.file_name,
        file_size=state.file_size,
        file_owner_id=state.file_owner_id,
        file_tenant_id=state.file_tenant_id,
        text=state.text,
        extra_meta=state.extra_meta or {},
        extra_context=state.extra_context or {},
    )
    
    # Pass the Pydantic instance directly as the payload
    point = VectorPoint(
        id=state.file_id,
        vector=state.vector,
        payload=vector_payload
    )
    
    db.upsert(
        collection_name=QDRANT_COLLECTION_RAG,
        points=[point]
    )
    
    return {"status": "success"}


# Define and assemble the StateGraph
builder = StateGraph(FileIngestState)
builder.add_node("vectorize_content", vectorize_content)
builder.add_node("store_in_vector_db", store_in_vector_db)

builder.add_edge("__start__", "vectorize_content")
builder.add_edge("vectorize_content", "store_in_vector_db")
builder.add_edge("store_in_vector_db", "__end__")

# Initialize SQLite database checkpointer
memory = LazyAsyncSqliteSaver(settings.DB_FILE)

# Compile the final graph
file_ingest_graph = builder.compile(
    name="file ingest graph",
    checkpointer=memory
)
