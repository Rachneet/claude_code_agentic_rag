from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class User(BaseModel):
    id: str


class ThreadCreate(BaseModel):
    title: str = "New Chat"


class ThreadUpdate(BaseModel):
    title: str


class ThreadResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    id: str
    thread_id: str
    role: str
    content: str
    created_at: datetime


class ChatRequest(BaseModel):
    thread_id: str
    message: str

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be empty")
        return v


class DocumentMetadataResponse(BaseModel):
    title: str = ""
    document_type: str = "other"
    topics: list[str] = []
    entities: list[str] = []
    language: str = "en"
    summary: str = ""


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_size: int
    mime_type: str
    status: str
    chunk_count: int
    storage_path: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[DocumentMetadataResponse] = None
    created_at: datetime
    updated_at: datetime
