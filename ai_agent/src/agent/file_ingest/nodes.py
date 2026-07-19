"""Nodes for the File Ingest graph."""

from enum import Enum
from typing import Any

from langgraph.runtime import Runtime

from agent.core.constants import QDRANT_COLLECTION_RAG
from agent.core.embedding import get_embedding_model
from agent.core.logger import logger
from agent.core.vectordb import RAGFileVectorPayload, VectorPoint, get_vector_db
from uuid import UUID, uuid5
from agent.core.splitter import DocumentSplitterFactory
from agent.file_ingest.outputs import build_rag_file_import_output
from agent.file_ingest.state import (
    BuildFileIngestOutputUpdate,
    FileIngestChunk,
    FileIngestState,
    StoreInVectorDBUpdate,
    VectorizeContentUpdate,
)

# Namespace for deterministic chunk UUIDs
INGEST_NAMESPACE = UUID("507db244-9336-55f5-a55f-146301c9b928")


class FileIngestNodeNames(str, Enum):
    """Define node identifiers for the File Ingest graph."""

    VECTORIZE_CONTENT = "vectorize_content"
    STORE_IN_VECTOR_DB = "store_in_vector_db"
    BUILD_FILE_INGEST_OUTPUT = "build_file_ingest_output"


async def vectorize_content(state: FileIngestState) -> dict[str, Any]:
    """Decode file content, split it, and generate embedding vectors for chunks."""
    logger.info(f"Vectorizing content for file_id: {state.file_id}")
    text = state.file_content.decode("utf-8", errors="ignore")

    splitter = DocumentSplitterFactory.get_splitter(state.file_name)
    text_chunks = splitter.split(text, chunk_size=500, chunk_overlap=50)

    embedding_model = get_embedding_model()
    chunks: list[FileIngestChunk] = []

    for index, chunk_text in enumerate(text_chunks):
        try:
            vector = await embedding_model.aembed_query(chunk_text)
            chunks.append(
                FileIngestChunk(
                    chunk_index=index,
                    text=chunk_text,
                    vector=vector,
                )
            )
        except Exception as error:
            logger.error(
                "Failed to generate embedding for chunk index {} of file_id {}: {}",
                index,
                state.file_id,
                error,
            )
            raise

    update = VectorizeContentUpdate(chunks=chunks)
    return update.model_dump(exclude_unset=True)


async def store_in_vector_db(state: FileIngestState) -> dict[str, Any]:
    """Store all generated embedding chunks in the vector database."""
    if not state.chunks:
        logger.error(
            f"File ingest state has no chunks before vector storage: "
            f"file_id={state.file_id}"
        )
        raise ValueError("File chunks are required for storage")

    logger.info(
        f"Storing file_id {state.file_id} with {len(state.chunks)} chunks "
        f"in vector DB collection '{QDRANT_COLLECTION_RAG}'"
    )

    points = []
    for chunk in state.chunks:
        vector_payload = RAGFileVectorPayload(
            file_id=state.file_id,
            file_name=state.file_name,
            file_size=state.file_size,
            file_owner_id=state.file_owner_id,
            file_tenant_id=state.file_tenant_id,
            text=chunk.text,
            extra_meta=state.extra_meta or {},
            extra_context=state.extra_context or {},
        )
        # Generate stable UUID point ID based on file_id and chunk_index
        point_id = str(uuid5(INGEST_NAMESPACE, f"chunk:{state.file_id}:{chunk.chunk_index}"))
        point = VectorPoint(
            id=point_id,
            vector=chunk.vector,
            payload=vector_payload,
        )
        points.append(point)

    db = get_vector_db()
    db.upsert(
        collection_name=QDRANT_COLLECTION_RAG,
        points=points,
    )
    update = StoreInVectorDBUpdate(status="success")
    return update.model_dump(exclude_unset=True)


async def build_file_ingest_output(
    state: FileIngestState,
    runtime: Runtime[None],
) -> dict[str, Any]:
    """Build the public result for a successfully stored RAG file."""
    if state.status != "success":
        logger.error(
            f"File ingest output requires successful vector storage: "
            f"file_id={state.file_id}, status={state.status}"
        )
        raise RuntimeError("File ingest did not complete vector storage")

    execution_info = runtime.execution_info
    if execution_info is None or not execution_info.task_id:
        logger.error("File ingest output generation requires a graph task ID")
        raise RuntimeError("File ingest output generation requires a task ID")

    output = build_rag_file_import_output(
        identity_scope=execution_info.task_id,
        file_id=state.file_id,
        file_name=state.file_name,
    )
    update = BuildFileIngestOutputUpdate(outputs=[output])
    return update.model_dump(exclude_unset=True)
