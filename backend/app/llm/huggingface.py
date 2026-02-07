import asyncio
import re
from typing import AsyncGenerator, Generator

from huggingface_hub import InferenceClient
from langsmith import traceable

from app.config import settings

client = InferenceClient(
    provider="auto",
    api_key=settings.hf_token,
)

SYSTEM_PROMPT = (
    "You are a helpful AI assistant. Answer questions clearly and concisely. "
    "If you don't know something, say so honestly. "
    "Do not use <think> tags or show your reasoning process. "
    "Respond directly with your answer."
)


def strip_think_tags(text: str) -> str:
    """Remove <think>...</think> blocks from model output."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


@traceable(name="hf_chat_completion", run_type="llm")
def chat_completion(
    messages: list[dict],
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> str:
    """Non-streaming completion for cases like title generation."""
    response = client.chat_completion(
        model=settings.hf_model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return strip_think_tags(response.choices[0].message.content)


def _chat_completion_stream_sync(
    messages: list[dict],
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> Generator[str, None, None]:
    """Sync streaming generator — runs in a thread."""
    stream = client.chat_completion(
        model=settings.hf_model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


async def chat_completion_stream(
    messages: list[dict],
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> AsyncGenerator[str, None]:
    """Async streaming that yields tokens without blocking the event loop.

    Strips <think>...</think> blocks — buffers tokens inside think tags
    and only yields content outside them.
    """
    loop = asyncio.get_event_loop()
    gen = _chat_completion_stream_sync(messages, max_tokens, temperature)

    inside_think = False
    buffer = ""

    while True:
        try:
            token = await loop.run_in_executor(None, next, gen)
        except StopIteration:
            break

        buffer += token

        # Check for opening <think> tag
        if not inside_think and "<think>" in buffer:
            # Yield everything before the <think> tag
            before = buffer[: buffer.index("<think>")]
            if before:
                yield before
            buffer = buffer[buffer.index("<think>") :]
            inside_think = True

        # Check for closing </think> tag
        if inside_think and "</think>" in buffer:
            after = buffer[buffer.index("</think>") + len("</think>") :]
            buffer = after
            inside_think = False

        # If not inside think tags, yield the buffer
        if not inside_think and buffer and "<" not in buffer:
            yield buffer
            buffer = ""

    # Yield any remaining buffer (outside think tags)
    if buffer and not inside_think:
        cleaned = strip_think_tags(buffer)
        if cleaned:
            yield cleaned
