from abc import ABC, abstractmethod
from typing import AsyncGenerator


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

    async def chat_completion_stream_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        tool_executor: callable,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Streaming completion with tool calling.

        Detects tool calls, executes them via tool_executor,
        then streams the final response.
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not support tool calling")
