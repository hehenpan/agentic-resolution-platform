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
