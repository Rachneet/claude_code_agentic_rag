from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator, Callable, Generator

import httpx
from langsmith import traceable

from app.config import settings
from app.llm.base import LLMProvider

_SENTINEL = object()


def _next_or_sentinel(gen):
    """Wrapper that returns a sentinel instead of raising StopIteration."""
    try:
        return next(gen)
    except StopIteration:
        return _SENTINEL


def _convert_tools(tools: list[dict]) -> list[dict]:
    """Wrap provider-agnostic tool defs into OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": tool,
        }
        for tool in tools
    ]


class OpenRouterProvider(LLMProvider):
    """OpenRouter provider using raw httpx (OpenAI-compatible API)."""

    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.model = settings.openrouter_model
        self.base_url = settings.openrouter_base_url.rstrip("/")

    @property
    def supports_tools(self) -> bool:
        return True

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @traceable(name="openrouter_chat_completion", run_type="llm")
    def chat_completion(
        self,
        messages: list[dict],
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"] or ""

    def _stream_sync(
        self,
        payload: dict,
    ) -> Generator[str, None, None]:
        """Sync SSE streaming generator — runs in a thread."""
        with httpx.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=120.0,
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[len("data: "):]
                if data_str.strip() == "[DONE]":
                    break
                chunk = json.loads(data_str)
                delta = chunk["choices"][0].get("delta", {})
                content = delta.get("content")
                if content:
                    yield content

    async def chat_completion_stream(
        self,
        messages: list[dict],
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        loop = asyncio.get_event_loop()
        gen = self._stream_sync(payload)

        while True:
            token = await loop.run_in_executor(None, _next_or_sentinel, gen)
            if token is _SENTINEL:
                break
            yield token

    @traceable(name="openrouter_chat_with_tools", run_type="llm")
    def chat_completion_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "tools": _convert_tools(tools),
        }

        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()

        message = data["choices"][0]["message"]
        result = {"content": None, "tool_calls": None}

        if message.get("tool_calls"):
            result["tool_calls"] = [
                {
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "args": json.loads(tc["function"]["arguments"]),
                }
                for tc in message["tool_calls"]
            ]
        elif message.get("content"):
            result["content"] = message["content"]

        return result

    def format_tool_messages(
        self, tool_calls_response: dict, tool_results: list[dict]
    ) -> list[dict]:
        messages = []
        assistant_tool_calls = []
        for tc in tool_calls_response["tool_calls"]:
            assistant_tool_calls.append(
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(tc["args"]),
                    },
                }
            )
        messages.append({"role": "assistant", "tool_calls": assistant_tool_calls})
        for tc, tr in zip(tool_calls_response["tool_calls"], tool_results):
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": tr["result"],
                }
            )
        return messages

    async def chat_completion_stream_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        tool_executor: Callable,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Streaming with tool calling.

        1. Non-streaming call to detect tool calls
        2. Execute tools
        3. Stream the final response with tool results
        """
        # Step 1: Non-streaming call to check for tool calls
        loop = asyncio.get_event_loop()
        initial = await loop.run_in_executor(
            None,
            lambda: self.chat_completion_with_tools(
                messages, tools, max_tokens, temperature
            ),
        )

        # Step 2: If no tool calls, return content directly
        if not initial.get("tool_calls"):
            if initial.get("content"):
                yield initial["content"]
            return

        # Step 3: Execute tool calls
        tool_results = []
        assistant_tool_calls = []
        for tc in initial["tool_calls"]:
            result = await tool_executor(tc["name"], tc["args"])
            assistant_tool_calls.append(
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(tc["args"]),
                    },
                }
            )
            tool_results.append(
                {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                }
            )

        # Step 4: Build updated conversation with tool results
        updated_messages = list(messages)
        updated_messages.append(
            {"role": "assistant", "tool_calls": assistant_tool_calls}
        )
        updated_messages.extend(tool_results)

        # Step 5: Stream the final response (no tools)
        payload = {
            "model": self.model,
            "messages": updated_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        gen = self._stream_sync(payload)
        while True:
            token = await loop.run_in_executor(None, _next_or_sentinel, gen)
            if token is _SENTINEL:
                break
            yield token
