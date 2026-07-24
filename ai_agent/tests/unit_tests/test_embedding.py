"""Tests for the configured Gemini embedding adapter."""

import pytest

from agent.core import embedding
from agent.core.config import settings


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
    monkeypatch.setattr(settings, "EMBEDDING_MODEL", "models/test-embedding")
    monkeypatch.setattr(settings, "EMBEDDING_DIM", 128)
    monkeypatch.setattr(
        embedding,
        "GoogleGenerativeAIEmbeddings",
        FakeGoogleGenerativeAIEmbeddings,
    )

    model = embedding.get_embedding_model()

    assert isinstance(model, embedding.GeminiEmbeddingModel)
    assert model.embeddings.model == settings.EMBEDDING_MODEL
    assert model.embeddings.model == "models/test-embedding"
    assert model.embeddings.output_dimensionality == settings.EMBEDDING_DIM
    assert model.embeddings.output_dimensionality == 128
