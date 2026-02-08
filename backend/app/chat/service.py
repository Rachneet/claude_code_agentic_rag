import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator

from langsmith import traceable

logger = logging.getLogger(__name__)


def _current_datetime_context() -> str:
    """Return a short string with the current UTC date/time for system prompts."""
    now = datetime.now(timezone.utc)
    return f"Current date and time (UTC): {now.strftime('%A, %B %d, %Y %I:%M %p')}."

from app.chat.tools import execute_tool, get_enabled_tools
from app.db.supabase import supabase
from app.ingestion.retrieval import format_retrieval_context, search_documents
from app.llm.factory import get_provider
from app.models.schemas import User

def _system_prompt() -> str:
    return (
        f"{_current_datetime_context()} "
        "You are a helpful AI assistant. Answer questions clearly and concisely. "
        "If you don't know something, say so honestly. "
        "Do not use <think> tags or show your reasoning process. "
        "Respond directly with your answer."
    )

def _build_tool_system_prompt() -> str:
    """Build the system prompt dynamically based on enabled tools."""
    tools = get_enabled_tools()
    tool_names = [t["name"] for t in tools]

    base = (
        f"{_current_datetime_context()} "
        "You are a helpful AI assistant with access to several tools. "
        "Use the appropriate tool for each part of the user's question:\n\n"
    )

    tool_instructions = []

    if "search_documents" in tool_names:
        tool_instructions.append(
            "- **search_documents**: Search the user's uploaded documents for relevant information. "
            "Use this first when the question might be answered by their documents."
        )
    if "web_search" in tool_names:
        tool_instructions.append(
            "- **web_search**: Search the web for current or general information. "
            "Use this when the question requires up-to-date info or topics not covered in the user's documents."
        )
    if "fetch_url" in tool_names:
        tool_instructions.append(
            "- **fetch_url**: Fetch and read content from a specific URL. "
            "Use this when the user provides a URL they want you to read or analyze."
        )
    if "calculate" in tool_names:
        tool_instructions.append(
            "- **calculate**: Evaluate mathematical expressions. "
            "Use this for any calculations, unit conversions, or numeric analysis."
        )
    if "get_datetime" in tool_names:
        tool_instructions.append(
            "- **get_datetime**: Get the current date and time. "
            "Use this when the user asks about the current date, time, or needs timezone information."
        )

    base += "\n".join(tool_instructions)
    base += (
        "\n\n"
        "When you use search_documents and find relevant results, cite the sources in your answer. "
        "If no relevant documents are found, try web_search if available, or answer from your "
        "general knowledge and let the user know. "
        "Do not use <think> tags or show your reasoning process. "
        "Respond directly with your answer."
    )

    return base

def _hf_rag_system_prompt(context: str) -> str:
    return (
        f"{_current_datetime_context()} "
        "You are a helpful AI assistant. Answer questions clearly and concisely. "
        "If you don't know something, say so honestly. "
        "Do not use <think> tags or show your reasoning process. "
        "Respond directly with your answer.\n\n"
        "The following context was retrieved from the user's uploaded documents. "
        "Each source includes its document title and type in brackets. "
        "Use this context to inform your answer and cite sources by title when relevant:\n\n"
        f"{context}"
    )


def save_message(thread_id: str, user_id: str, role: str, content: str) -> dict:
    result = (
        supabase.table("messages")
        .insert(
            {
                "thread_id": thread_id,
                "user_id": user_id,
                "role": role,
                "content": content,
            }
        )
        .execute()
    )
    return result.data[0]


def get_thread_messages(thread_id: str) -> list[dict]:
    result = (
        supabase.table("messages")
        .select("role, content")
        .eq("thread_id", thread_id)
        .order("created_at", desc=False)
        .execute()
    )
    return result.data


def update_thread_title(thread_id: str, title: str):
    supabase.table("threads").update({"title": title}).eq(
        "id", thread_id
    ).execute()


def _user_has_documents(user_id: str) -> bool:
    """Check if the user has any completed documents."""
    result = (
        supabase.table("documents")
        .select("id")
        .eq("user_id", user_id)
        .eq("status", "completed")
        .limit(1)
        .execute()
    )
    return len(result.data) > 0


@traceable(name="generate_thread_title", run_type="chain")
def generate_thread_title(user_message: str) -> str:
    provider = get_provider()
    messages = [
        {
            "role": "system",
            "content": (
                "Generate a brief title (max 6 words) for a conversation that "
                "starts with this message. Return only the title, no quotes or extra text. "
                "Do not use <think> tags or show your reasoning process."
            ),
        },
        {"role": "user", "content": user_message},
    ]
    title = provider.chat_completion(messages, max_tokens=30, temperature=0.5)
    title = title.strip().strip('"').strip("'")
    return title if title else "New Chat"


@traceable(name="chat_stream", run_type="chain")
async def stream_chat_response(
    thread_id: str,
    user_message: str,
    user: User,
) -> AsyncGenerator[str, None]:
    provider = get_provider()

    # 1. Save user message
    save_message(thread_id, user.id, "user", user_message)

    # 2. Auto-title on first message
    messages_in_thread = get_thread_messages(thread_id)
    if len(messages_in_thread) == 1:
        try:
            title = generate_thread_title(user_message)
            update_thread_title(thread_id, title)
            logger.info(f"Auto-titled thread {thread_id}: {title}")
        except Exception:
            logger.exception(f"Failed to auto-title thread {thread_id}")

    # 3. Check if user has documents for RAG
    has_documents = _user_has_documents(user.id)

    # 4. Build messages and stream response
    full_response = []

    try:
        enabled_tools = get_enabled_tools()
        has_non_rag_tools = len(enabled_tools) > 1

        if provider.supports_tools and (has_documents or has_non_rag_tools):
            # Tool-calling path: use all enabled tools
            llm_messages = [{"role": "system", "content": _build_tool_system_prompt()}]
            llm_messages.extend(messages_in_thread)

            async def tool_executor(name: str, args: dict) -> str:
                return await execute_tool(name, args, user.id)

            async for token in provider.chat_completion_stream_with_tools(
                llm_messages,
                tools=enabled_tools,
                tool_executor=tool_executor,
            ):
                full_response.append(token)
                yield f"event: token\ndata: {json.dumps({'content': token})}\n\n"

        elif has_documents:
            # HF path: pre-retrieve context, inject into system prompt
            chunks = search_documents(user_message, user.id)
            context = format_retrieval_context(chunks)

            if context:
                system_prompt = _hf_rag_system_prompt(context)
            else:
                system_prompt = _system_prompt()

            llm_messages = [{"role": "system", "content": system_prompt}]
            llm_messages.extend(messages_in_thread)

            async for token in provider.chat_completion_stream(llm_messages):
                full_response.append(token)
                yield f"event: token\ndata: {json.dumps({'content': token})}\n\n"

        else:
            # No documents: standard chat
            llm_messages = [{"role": "system", "content": _system_prompt()}]
            llm_messages.extend(messages_in_thread)

            async for token in provider.chat_completion_stream(llm_messages):
                full_response.append(token)
                yield f"event: token\ndata: {json.dumps({'content': token})}\n\n"

    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"
        return

    # 5. Save assistant message
    assistant_content = "".join(full_response)
    saved_msg = save_message(thread_id, user.id, "assistant", assistant_content)

    yield f"event: done\ndata: {json.dumps({'message_id': saved_msg['id']})}\n\n"
