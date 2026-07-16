"""Vector database interfaces and Qdrant implementation."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from qdrant_client.models import Distance, PointStruct, VectorParams

from agent.core.constants import GEMINI_EMBEDDING_DIM
from agent.core.qdrant import get_qdrant_client


class RAGFileVectorPayload(BaseModel):
    """Represent metadata stored with an embedded RAG file chunk."""

    file_id: int
    file_name: str
    file_size: int
    file_owner_id: int
    file_tenant_id: int
    text: str
    extra_meta: dict[str, Any] = Field(default_factory=dict)
    extra_context: dict[str, Any] = Field(default_factory=dict)


class VectorPoint(BaseModel):
    """Represent a database-agnostic vector database record."""

    id: int | str | UUID
    vector: list[float]
    payload: BaseModel | dict[str, Any]


class VectorSearchResult(BaseModel):
    """Represent a database-agnostic vector search result."""

    id: int | str | UUID
    score: float
    payload: dict[str, Any]


class VectorDB(ABC):
    """Define the vector database operations used by the agent service."""

    @abstractmethod
    def upsert(self, collection_name: str, points: list[VectorPoint]) -> None:
        """Insert or update points in a collection."""

    @abstractmethod
    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int,
    ) -> list[VectorSearchResult]:
        """Return the closest points in a collection."""


class QdrantVectorDB(VectorDB):
    """Implement vector storage and retrieval with Qdrant."""

    def upsert(self, collection_name: str, points: list[VectorPoint]) -> None:
        """Insert or update points, creating the collection when required."""
        client = get_qdrant_client()

        if not client.collection_exists(collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=GEMINI_EMBEDDING_DIM,
                    distance=Distance.COSINE,
                ),
            )

        qdrant_points = [
            PointStruct(
                id=point.id,
                vector=point.vector,
                payload=(
                    point.payload.model_dump()
                    if isinstance(point.payload, BaseModel)
                    else point.payload
                ),
            )
            for point in points
        ]

        client.upsert(
            collection_name=collection_name,
            points=qdrant_points,
        )

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int,
    ) -> list[VectorSearchResult]:
        """Search a Qdrant collection for the closest points."""
        response = get_qdrant_client().query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit,
        )
        return [
            VectorSearchResult(
                id=point.id,
                score=point.score,
                payload=point.payload or {},
            )
            for point in response.points
        ]


def get_vector_db() -> VectorDB:
    """Create the configured vector database implementation."""
    return QdrantVectorDB()
