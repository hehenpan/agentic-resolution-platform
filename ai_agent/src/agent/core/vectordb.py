"""Vector database interfaces and Qdrant implementation."""

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from qdrant_client.models import Distance, PointStruct, VectorParams

from agent.core.config import settings
from agent.core.logger import logger
from agent.core.qdrant import get_async_qdrant_client


class RAGFileVectorPayload(BaseModel):
    """Represent metadata stored with an embedded RAG file chunk."""

    file_id: int = Field(description="Source file ID for the embedded chunk.")
    file_name: str = Field(description="Source file name for citation display.")
    file_size: int = Field(description="Source file size in bytes.")
    file_owner_id: int = Field(description="User ID that owns the source file.")
    file_tenant_id: int = Field(description="Tenant ID that owns the source file.")
    text: str = Field(description="Raw text content embedded into this vector.")
    extra_meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata stored with the vector payload.",
    )
    extra_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional execution context stored with the vector payload.",
    )


class VectorPoint(BaseModel):
    """Represent a database-agnostic vector database record."""

    id: int | str | UUID = Field(description="Unique point ID in the vector store.")
    vector: list[float] = Field(description="Embedding vector values for the point.")
    payload: BaseModel | dict[str, Any] = Field(
        description="Structured payload stored alongside the vector."
    )


class VectorSearchResult(BaseModel):
    """Represent a database-agnostic vector search result."""

    id: int | str | UUID = Field(description="Matched vector point ID.")
    score: float = Field(description="Similarity score returned by the vector store.")
    payload: dict[str, Any] = Field(
        description="Payload returned with the matched vector point."
    )


class VectorDB(ABC):
    """Define the vector database operations used by the agent service."""

    @abstractmethod
    async def upsert(self, collection_name: str, points: list[VectorPoint]) -> None:
        """Insert or update points in a collection."""

    @abstractmethod
    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int,
    ) -> list[VectorSearchResult]:
        """Return the closest points in a collection."""


class QdrantVectorDB(VectorDB):
    """Implement vector storage and retrieval with Qdrant."""

    async def upsert(self, collection_name: str, points: list[VectorPoint]) -> None:
        """Insert or update points, creating the collection when required."""
        client = await get_async_qdrant_client()

        if not await client.collection_exists(collection_name):
            await client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=settings.EMBEDDING_DIM,
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

        await client.upsert(
            collection_name=collection_name,
            points=qdrant_points,
        )

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int,
    ) -> list[VectorSearchResult]:
        """Search a Qdrant collection for the closest points."""
        try:
            client = await get_async_qdrant_client()
            if not await client.collection_exists(collection_name):
                logger.warning(
                    "Collection {} does not exist in Qdrant; returning empty search results.",
                    collection_name,
                )
                return []
            response = await client.query_points(
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
        except Exception as error:
            logger.warning(
                "Failed to search Qdrant collection {}: {}",
                collection_name,
                error,
            )
            return []


def get_vector_db() -> VectorDB:
    """Create the configured vector database implementation."""
    return QdrantVectorDB()
