from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import StreamingResponse

from app.auth.dependencies import get_current_user
from app.chat.service import stream_chat_response
from app.db.supabase import supabase
from app.models.schemas import (
    ChatRequest,
    MessageResponse,
    ThreadCreate,
    ThreadResponse,
    ThreadUpdate,
    User,
)

router = APIRouter(prefix="/api", tags=["threads"])


@router.get("/threads", response_model=list[ThreadResponse])
async def list_threads(user: User = Depends(get_current_user)):
    result = (
        supabase.table("threads")
        .select("*")
        .eq("user_id", user.id)
        .order("updated_at", desc=True)
        .execute()
    )
    return result.data


@router.post("/threads", response_model=ThreadResponse, status_code=201)
async def create_thread(
    body: ThreadCreate,
    user: User = Depends(get_current_user),
):
    result = (
        supabase.table("threads")
        .insert({"user_id": user.id, "title": body.title})
        .execute()
    )
    return result.data[0]


@router.patch("/threads/{thread_id}", response_model=ThreadResponse)
async def update_thread(
    thread_id: str,
    body: ThreadUpdate,
    user: User = Depends(get_current_user),
):
    result = (
        supabase.table("threads")
        .update({"title": body.title})
        .eq("id", thread_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Thread not found")
    return result.data[0]


@router.delete("/threads/{thread_id}", status_code=204)
async def delete_thread(
    thread_id: str,
    user: User = Depends(get_current_user),
):
    result = (
        supabase.table("threads")
        .delete()
        .eq("id", thread_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Thread not found")


@router.get("/threads/{thread_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    thread_id: str,
    user: User = Depends(get_current_user),
):
    thread = (
        supabase.table("threads")
        .select("id")
        .eq("id", thread_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not thread.data:
        raise HTTPException(status_code=404, detail="Thread not found")

    result = (
        supabase.table("messages")
        .select("*")
        .eq("thread_id", thread_id)
        .order("created_at", desc=False)
        .execute()
    )
    return result.data


@router.post("/chat")
async def chat(
    body: ChatRequest,
    user: User = Depends(get_current_user),
):
    thread = (
        supabase.table("threads")
        .select("id")
        .eq("id", body.thread_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not thread.data:
        raise HTTPException(status_code=404, detail="Thread not found")

    return StreamingResponse(
        stream_chat_response(body.thread_id, body.message, user),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
