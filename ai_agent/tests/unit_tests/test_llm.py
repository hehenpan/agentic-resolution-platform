from typing import Any

from agent.core import llm
from agent.core.constants import GEMINI_CHAT_MODEL


class FakeGoogleGenerativeAI:
    def __init__(self, model: str) -> None:
        self.model = model

    async def ainvoke(self, input: Any, **kwargs: Any) -> Any:
        return input


def test_get_llm_model_creates_configured_model(monkeypatch) -> None:
    monkeypatch.setattr(
        llm,
        "ChatGoogleGenerativeAI",
        FakeGoogleGenerativeAI,
    )

    first_model = llm.get_llm_model()
    second_model = llm.get_llm_model()

    assert isinstance(first_model, FakeGoogleGenerativeAI)
    assert first_model.model == GEMINI_CHAT_MODEL
    assert second_model is not first_model
