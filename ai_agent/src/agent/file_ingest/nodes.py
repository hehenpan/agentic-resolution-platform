"""Nodes for the File Ingest graph."""

from enum import Enum
from typing import Any

from langgraph.runtime import Runtime

from agent.core.constants import QDRANT_COLLECTION_RAG
from agent.core.embedding import get_embedding_model
from agent.core.logger import logger
from agent.core.vectordb import RAGFileVectorPayload, VectorPoint, get_vector_db
from agent.file_ingest.outputs import build_rag_file_import_output
from agent.file_ingest.state import (
    BuildFileIngestOutputUpdate,
    FileIngestState,
    StoreInVectorDBUpdate,
    VectorizeContentUpdate,
)


class FileIngestNodeNames(str, Enum):
    """Define node identifiers for the File Ingest graph."""

    VECTORIZE_CONTENT = "vectorize_content"
    STORE_IN_VECTOR_DB = "store_in_vector_db"
    BUILD_FILE_INGEST_OUTPUT = "build_file_ingest_output"


async def vectorize_content(state: FileIngestState) -> dict[str, Any]:
    """Decode file content and generate its embedding vector."""
    logger.info(f"Vectorizing content for file_id: {state.file_id}")
    text = state.file_content.decode("utf-8", errors="ignore")
    embedding_model = get_embedding_model()
    vector = await embedding_model.aembed_query(text)
    update = VectorizeContentUpdate(text=text, vector=vector)
    return update.model_dump(exclude_unset=True)


async def store_in_vector_db(state: FileIngestState) -> dict[str, Any]:
    """Store the generated embedding and metadata in the vector database."""
    if state.text is None or state.vector is None:
        logger.error(
            f"File ingest state is incomplete before vector storage: "
            f"file_id={state.file_id}"
        )
        raise ValueError("File text and embedding vector are required")

    logger.info(
        f"Storing file_id {state.file_id} in vector DB collection "
        f"'{QDRANT_COLLECTION_RAG}'"
    )
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
    point = VectorPoint(
        id=state.file_id,
        vector=state.vector,
        payload=vector_payload,
    )
    db = get_vector_db()
    db.upsert(
        collection_name=QDRANT_COLLECTION_RAG,
        points=[point],
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
