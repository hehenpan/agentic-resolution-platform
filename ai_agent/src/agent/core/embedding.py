"""Shared embedding model interface and factory."""

from abc import ABC, abstractmethod

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from agent.core.constants import (
    GEMINI_EMBEDDING_DIM,
    GEMINI_EMBEDDING_MODEL,
)


class EmbeddingModel(ABC):
    """Define the asynchronous query embedding interface."""

    @abstractmethod
    async def aembed_query(self, text: str) -> list[float]:
        """Generate an embedding vector for the supplied text."""
        ...


class GeminiEmbeddingModel(EmbeddingModel):
    """Generate embeddings with Google's Gemini embedding API."""

    def __init__(
        self,
        model_name: str,
        output_dimensionality: int,
    ) -> None:
        """Initialize the provider adapter with an explicit vector dimension."""
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=model_name,
            output_dimensionality=output_dimensionality,
        )

    async def aembed_query(self, text: str) -> list[float]:
        """Generate a query embedding through the provider adapter."""
        return await self.embeddings.aembed_query(text)


def get_embedding_model() -> EmbeddingModel:
    """Create the configured embedding model."""
    return GeminiEmbeddingModel(
        model_name=GEMINI_EMBEDDING_MODEL,
        output_dimensionality=GEMINI_EMBEDDING_DIM,
    )
