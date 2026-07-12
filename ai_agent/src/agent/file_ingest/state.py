from typing import Optional, List
from pydantic import BaseModel
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


class VectorizeOutput(BaseModel):
    """
    Pydantic schema to strictly constrain the output of the vectorize_content node.
    """
    text: str
    vector: List[float]


class StoreVectorDBOutput(BaseModel):
    """
    Pydantic schema to strictly constrain the output of the store_in_vector_db node.
    """
    status: str
