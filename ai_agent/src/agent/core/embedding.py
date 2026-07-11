from abc import ABC, abstractmethod
from typing import List

class EmbeddingModel(ABC):
    """
    Abstract base class representing an embedding model interface.
    """
    @abstractmethod
    async def aembed_query(self, text: str) -> List[float]:
        """
        Asynchronously generates an embedding vector for a given text.
        """
        pass


class GeminiEmbeddingModel(EmbeddingModel):
    """
    Concrete implementation of EmbeddingModel using Google's Gemini embeddings.
    """
    def __init__(self, model_name: str) -> None:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        self.embeddings = GoogleGenerativeAIEmbeddings(model=model_name)

    async def aembed_query(self, text: str) -> List[float]:
        return await self.embeddings.aembed_query(text)


def get_embedding_model() -> EmbeddingModel:
    """
    Factory helper to retrieve the active embedding model implementation.
    """
    from agent.core.constants import GEMINI_EMBEDDING_MODEL
    return GeminiEmbeddingModel(GEMINI_EMBEDDING_MODEL)
