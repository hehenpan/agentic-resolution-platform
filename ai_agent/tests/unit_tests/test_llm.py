from typing import Any

from agent.core import llm
from agent.core.config import settings


class FakeGoogleGenerativeAI:
    def __init__(self, model: str) -> None:
        self.model = model

    async def ainvoke(self, input: Any, **kwargs: Any) -> Any:
        return input


def test_get_llm_model_creates_configured_model(monkeypatch) -> None:
    monkeypatch.setattr(settings, "LLM_CHAT_MODEL", "test-chat-model")
    monkeypatch.setattr(
        llm,
        "ChatGoogleGenerativeAI",
        FakeGoogleGenerativeAI,
    )

    first_model = llm.get_llm_model()
    second_model = llm.get_llm_model()

    assert isinstance(first_model, FakeGoogleGenerativeAI)
    assert first_model.model == settings.LLM_CHAT_MODEL
    assert first_model.model == "test-chat-model"
    assert second_model is not first_model
