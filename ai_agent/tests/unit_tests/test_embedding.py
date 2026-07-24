"""Tests for the configured Gemini embedding adapter."""

import pytest

from agent.core import embedding
from agent.core.constants import (
    GEMINI_EMBEDDING_DIM,
    GEMINI_EMBEDDING_MODEL,
)


class FakeGoogleGenerativeAIEmbeddings:
    """Capture provider configuration without calling the external API."""

    def __init__(
        self,
        *,
        model: str,
        output_dimensionality: int,
    ) -> None:
        self.model = model
        self.output_dimensionality = output_dimensionality

    async def aembed_query(self, text: str) -> list[float]:
        return [float(len(text))]


def test_get_embedding_model_uses_configured_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        embedding,
        "GoogleGenerativeAIEmbeddings",
        FakeGoogleGenerativeAIEmbeddings,
    )

    model = embedding.get_embedding_model()

    assert isinstance(model, embedding.GeminiEmbeddingModel)
    assert model.embeddings.model == GEMINI_EMBEDDING_MODEL
    assert model.embeddings.model == "models/gemini-embedding-001"
    assert model.embeddings.output_dimensionality == GEMINI_EMBEDDING_DIM
    assert model.embeddings.output_dimensionality == 3072
