"""Utilities for reading LangChain conversation messages."""

from collections.abc import Sequence

from langchain_core.messages import BaseMessage, HumanMessage

from agent.core.logger import logger


def require_latest_human_message_text(
    messages: Sequence[BaseMessage],
) -> str:
    """Return the latest non-empty human message text."""
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            text = message.text.strip()
            if text:
                return text

    logger.error("A non-empty HumanMessage is required")
    raise ValueError("A non-empty HumanMessage is required")


from typing import Any, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def extract_tool_call(
    message: Any,
    tool_model: Type[T],
) -> tuple[T | None, str | None]:
    """Extract tool call arguments and ID matching the tool model class name."""
    if not hasattr(message, "tool_calls") or not message.tool_calls:
        return None, None
    for tc in message.tool_calls:
        if tc["name"] == tool_model.__name__:
            parsed_args = tool_model.model_validate(tc["args"])
            return parsed_args, tc.get("id")
    return None, None

