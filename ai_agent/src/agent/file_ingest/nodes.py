from enum import Enum
from agent.core.logger import logger
from agent.core.constants import QDRANT_COLLECTION_RAG
from agent.core.vectordb import get_vector_db, VectorPoint, RAGFileVectorPayload
from agent.core.embedding import get_embedding_model
from agent.file_ingest.state import FileIngestState, VectorizeOutput, StoreVectorDBOutput

class FileIngestNodes(str, Enum):
    """
    Enum defining the unique string identifiers for each node in the file ingest graph.
    """
    VECTORIZE_CONTENT = "vectorize_content"
    STORE_IN_VECTOR_DB = "store_in_vector_db"


async def vectorize_content(state: FileIngestState) -> VectorizeOutput:
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
    
    return VectorizeOutput(text=text, vector=vector)


async def store_in_vector_db(state: FileIngestState) -> StoreVectorDBOutput:
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
    
    return StoreVectorDBOutput(status="success")
