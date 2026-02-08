from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Callable, Generator

from google import genai
from google.genai import types
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


def _convert_messages(messages: list[dict]) -> tuple[str | None, list[types.Content]]:
    """Convert universal message format to Gemini format.

    Returns (system_instruction, contents).
    Gemini handles system instructions separately and uses 'model' instead of 'assistant'.
    Handles tool call messages (assistant with tool_calls) and tool result messages (role=tool).
    """
    system_instruction = None
    contents = []

    for msg in messages:
        role = msg["role"]

        if role == "system":
            system_instruction = msg.get("content", "")
            continue

        # Assistant message with tool calls
        if role == "assistant" and "tool_calls" in msg:
            parts = []
            for tc in msg["tool_calls"]:
                func = tc.get("function", {})
                args = func.get("arguments", "{}")
                if isinstance(args, str):
                    import json
                    args = json.loads(args)
                parts.append(types.Part.from_function_call(
                    name=func.get("name", ""),
                    args=args,
                ))
            contents.append(types.Content(role="model", parts=parts))
            continue

        # Tool result message
        if role == "tool":
            content_str = msg.get("content", "")
            # Find the tool name from the preceding assistant message's tool_calls
            tool_name = ""
            tool_call_id = msg.get("tool_call_id", "")
            # Look back through messages to find the matching tool call name
            for prev_msg in messages:
                if prev_msg.get("role") == "assistant" and "tool_calls" in prev_msg:
                    for tc in prev_msg["tool_calls"]:
                        if tc.get("id") == tool_call_id:
                            tool_name = tc.get("function", {}).get("name", "")
                            break
            contents.append(types.Content(
                role="user",
                parts=[types.Part.from_function_response(
                    name=tool_name,
                    response={"result": content_str},
                )],
            ))
            continue

        # Regular text message
        text = msg.get("content", "")
        gemini_role = "model" if role == "assistant" else "user"
        contents.append(types.Content(role=gemini_role, parts=[types.Part(text=text)]))

    return system_instruction, contents


class GeminiProvider(LLMProvider):
    """Google Gemini provider using the google-genai SDK."""

    def __init__(self):
        self.client = genai.Client(api_key=settings.google_api_key)
        self.model = settings.gemini_model

    @property
    def supports_tools(self) -> bool:
        return True

    @traceable(name="gemini_chat_completion", run_type="llm")
    def chat_completion(
        self,
        messages: list[dict],
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        system_instruction, contents = _convert_messages(messages)

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=max_tokens,
            temperature=temperature,
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )
        return response.text or ""

    def _generate_stream_sync(
        self,
        contents: list[types.Content],
        config: types.GenerateContentConfig,
    ) -> Generator[str, None, None]:
        """Sync streaming generator — runs in a thread."""
        response = self.client.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=config,
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text

    async def chat_completion_stream(
        self,
        messages: list[dict],
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        system_instruction, contents = _convert_messages(messages)

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=max_tokens,
            temperature=temperature,
        )

        loop = asyncio.get_event_loop()
        gen = self._generate_stream_sync(contents, config)

        while True:
            token = await loop.run_in_executor(None, _next_or_sentinel, gen)
            if token is _SENTINEL:
                break
            yield token

    @traceable(name="gemini_chat_with_tools", run_type="llm")
    def chat_completion_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> dict:
        """Non-streaming completion with tool calling.

        Returns dict with 'content' and/or 'tool_calls'.
        """
        system_instruction, contents = _convert_messages(messages)

        # Convert tool definitions to Gemini format
        gemini_tools = types.Tool(function_declarations=tools)

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=max_tokens,
            temperature=temperature,
            tools=[gemini_tools],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )

        result = {"content": None, "tool_calls": None}

        # Check for function calls in response
        if response.function_calls:
            result["tool_calls"] = [
                {"id": f"call_{i}", "name": fc.name, "args": dict(fc.args)}
                for i, fc in enumerate(response.function_calls)
            ]
        elif response.text:
            result["content"] = response.text

        return result

    def format_tool_messages(
        self, tool_calls_response: dict, tool_results: list[dict]
    ) -> list[dict]:
        import json as json_mod

        messages = []
        assistant_tool_calls = []
        for tc in tool_calls_response["tool_calls"]:
            assistant_tool_calls.append(
                {
                    "id": tc.get("id", "call_0"),
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": json_mod.dumps(tc["args"]),
                    },
                }
            )
        messages.append({"role": "assistant", "tool_calls": assistant_tool_calls})
        for tc, tr in zip(tool_calls_response["tool_calls"], tool_results):
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.get("id", "call_0"),
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
        system_instruction, contents = _convert_messages(messages)
        gemini_tools = types.Tool(function_declarations=tools)

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=max_tokens,
            temperature=temperature,
            tools=[gemini_tools],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        # Step 1: Non-streaming call to check for tool calls
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            ),
        )

        # Step 2: If no tool calls, stream directly
        if not response.function_calls:
            if response.text:
                yield response.text
            return

        # Step 3: Execute tool calls
        tool_results = []
        for fc in response.function_calls:
            result = await tool_executor(fc.name, fc.args)
            tool_results.append(
                types.Part.from_function_response(
                    name=fc.name,
                    response={"result": result},
                )
            )

        # Step 4: Build updated conversation with tool results
        contents.append(response.candidates[0].content)
        contents.append(types.Content(role="user", parts=tool_results))

        # Step 5: Stream the final response (no tools this time)
        stream_config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            max_output_tokens=max_tokens,
            temperature=temperature,
        )

        gen = self._generate_stream_sync(contents, stream_config)
        while True:
            token = await loop.run_in_executor(None, _next_or_sentinel, gen)
            if token is _SENTINEL:
                break
            yield token
