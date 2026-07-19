"""Shared chat model interface and factory."""

from typing import Any, Protocol

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from agent.core.constants import GEMINI_CHAT_MODEL


class AsyncInvokable(Protocol):
    """Define the asynchronous invocation behavior used by agent graphs."""

    async def ainvoke(self, input: Any, **kwargs: Any) -> Any:
        """Invoke the runnable asynchronously."""
        ...


class ChatLLM(AsyncInvokable, Protocol):
    """Define chat model behavior used by agent graphs."""

    def bind_tools(self, tools: list[Any], **kwargs: Any) -> AsyncInvokable:
        """Return a runnable model configured with callable tool schemas."""
        ...

    def with_structured_output(
        self,
        schema: type[BaseModel],
        **kwargs: Any,
    ) -> AsyncInvokable:
        """Return a runnable constrained by a Pydantic output schema."""
        ...


def get_llm_model() -> ChatLLM:
    """Create the configured chat model."""
    return ChatGoogleGenerativeAI(model=GEMINI_CHAT_MODEL)
