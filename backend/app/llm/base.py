from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Callable


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def chat_completion(
        self,
        messages: list[dict],
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        """Non-streaming completion (e.g. for title generation)."""
        ...

    @property
    def supports_tools(self) -> bool:
        """Whether this provider supports tool calling."""
        return False

    @abstractmethod
    async def chat_completion_stream(
        self,
        messages: list[dict],
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Async streaming that yields tokens."""
        ...

    def chat_completion_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> dict:
        """Non-streaming completion with tool calling support.

        Returns dict with 'content' and/or 'tool_calls' keys.
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not support tool calling")

    def format_tool_messages(
        self,
        tool_calls_response: dict,
        tool_results: list[dict],
    ) -> list[dict]:
        """Format tool call + result messages for appending to conversation.

        Args:
            tool_calls_response: Dict from chat_completion_with_tools with 'tool_calls' list.
            tool_results: List of {"name": str, "result": str} dicts.

        Returns:
            List of message dicts (assistant tool-call message + tool result messages).
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not support tool message formatting")

    async def chat_completion_stream_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        tool_executor: Callable,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Streaming completion with tool calling.

        Detects tool calls, executes them via tool_executor,
        then streams the final response.
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not support tool calling")
