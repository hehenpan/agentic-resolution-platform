from abc import ABC, abstractmethod
from typing import Any, List, Union
from pydantic import BaseModel, Field

class RAGFileVectorPayload(BaseModel):
    """
    Schema representing the metadata payload stored in the vector database.
    Does not contain heavy binary fields (file_content) or runtime statuses.
    """
    file_id: int
    file_name: str
    file_size: int
    file_owner_id: int
    file_tenant_id: int
    text: str
    extra_meta: dict[str, Any] = Field(default_factory=dict)
    extra_context: dict[str, Any] = Field(default_factory=dict)


class VectorPoint(BaseModel):
    """
    A database-agnostic model representing a vector database record.
    Supports either a generic dictionary or a Pydantic model as payload.
    """
    id: Union[int, str]
    vector: List[float]
    payload: Union[BaseModel, dict[str, Any]]


class VectorDB(ABC):
    """
    Abstract base class representing the vector database interface.
    """
    @abstractmethod
    def upsert(self, collection_name: str, points: List[VectorPoint]) -> None:
        """
        Inserts or updates points in the specified collection.
        Automatically creates the collection if it does not exist.
        """
        pass


class QdrantVectorDB(VectorDB):
    """
    Concrete implementation of VectorDB using Qdrant client.
    """
    def upsert(self, collection_name: str, points: List[VectorPoint]) -> None:
        from qdrant_client.models import Distance, VectorParams, PointStruct
        from agent.core.qdrant import get_qdrant_client
        from agent.core.constants import GEMINI_EMBEDDING_DIM
        
        client = get_qdrant_client()
        
        # Automatically check and create collection if it doesn't exist
        if not client.collection_exists(collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=GEMINI_EMBEDDING_DIM, distance=Distance.COSINE),
            )
            
        qdrant_points = [
            PointStruct(
                id=p.id,
                vector=p.vector,
                payload=p.payload.model_dump() if isinstance(p.payload, BaseModel) else p.payload
            )
            for p in points
        ]
        
        client.upsert(
            collection_name=collection_name,
            points=qdrant_points
        )


def get_vector_db() -> VectorDB:
    """
    Factory method to retrieve the active singleton VectorDB implementation.
    """
    # Currently defaults to Qdrant, but can load different providers based on configuration
    return QdrantVectorDB()
