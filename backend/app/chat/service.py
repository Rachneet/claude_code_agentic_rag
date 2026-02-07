import json
from typing import AsyncGenerator

from langsmith import traceable

from app.db.supabase import supabase
from app.llm.huggingface import SYSTEM_PROMPT, chat_completion, chat_completion_stream
from app.models.schemas import User


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


@traceable(name="generate_thread_title", run_type="chain")
def generate_thread_title(user_message: str) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "Generate a brief title (max 6 words) for a conversation that "
                "starts with this message. Return only the title, no quotes or extra text."
            ),
        },
        {"role": "user", "content": user_message},
    ]
    title = chat_completion(messages, max_tokens=30, temperature=0.5)
    return title.strip().strip('"').strip("'")


@traceable(name="chat_stream", run_type="chain")
async def stream_chat_response(
    thread_id: str,
    user_message: str,
    user: User,
) -> AsyncGenerator[str, None]:
    # 1. Save user message
    save_message(thread_id, user.id, "user", user_message)

    # 2. Auto-title on first message
    messages_in_thread = get_thread_messages(thread_id)
    if len(messages_in_thread) == 1:
        try:
            title = generate_thread_title(user_message)
            update_thread_title(thread_id, title)
        except Exception:
            pass

    # 3. Build messages with system prompt
    llm_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    llm_messages.extend(messages_in_thread)

    # 4. Stream LLM response
    full_response = []
    try:
        async for token in chat_completion_stream(llm_messages):
            full_response.append(token)
            yield f"event: token\ndata: {json.dumps({'content': token})}\n\n"
    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"
        return

    # 5. Save assistant message
    assistant_content = "".join(full_response)
    saved_msg = save_message(thread_id, user.id, "assistant", assistant_content)

    yield f"event: done\ndata: {json.dumps({'message_id': saved_msg['id']})}\n\n"
