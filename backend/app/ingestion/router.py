import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile

from app.auth.dependencies import get_current_user
from app.db.supabase import supabase
from app.ingestion.service import ALLOWED_MIME_TYPES, MAX_FILE_SIZE, process_document
from app.models.schemas import DocumentResponse, User

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Map file extensions to MIME types for fallback detection
_EXT_TO_MIME = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".csv": "text/csv",
    ".json": "application/json",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".html": "text/html",
    ".htm": "text/html",
}


def _resolve_mime_type(file: UploadFile) -> str:
    """Resolve MIME type, falling back to extension-based detection."""
    if file.content_type and file.content_type in ALLOWED_MIME_TYPES:
        return file.content_type
    # Fallback: detect from file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    return _EXT_TO_MIME.get(ext, file.content_type or "application/octet-stream")


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
):
    # Validate file type (with extension fallback)
    mime_type = _resolve_mime_type(file)
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: .txt, .md, .csv, .json, .pdf, .docx, .html",
        )

    # Read and validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")

    if not content:
        raise HTTPException(status_code=400, detail="File is empty.")

    # Check for existing document with the same filename (enables record manager dedup)
    existing = (
        supabase.table("documents")
        .select("id, storage_path")
        .eq("user_id", user.id)
        .eq("filename", file.filename)
        .execute()
    )

    if existing.data:
        # Reuse existing document record
        doc = existing.data[0]
        doc_id = doc["id"]
        storage_path = doc["storage_path"]

        # Delete old file from storage (best-effort), then upload new version
        try:
            supabase.storage.from_("documents").remove([storage_path])
        except Exception:
            pass

        supabase.storage.from_("documents").upload(
            path=storage_path,
            file=content,
            file_options={"content-type": mime_type},
        )

        # Reset document status for reprocessing
        result = (
            supabase.table("documents")
            .update(
                {
                    "file_size": len(content),
                    "mime_type": mime_type,
                    "status": "pending",
                    "error_message": None,
                }
            )
            .eq("id", doc_id)
            .execute()
        )
    else:
        # New document: generate ID and storage path
        doc_id = str(uuid.uuid4())
        storage_path = f"{user.id}/{doc_id}/{file.filename}"

        supabase.storage.from_("documents").upload(
            path=storage_path,
            file=content,
            file_options={"content-type": mime_type},
        )

        result = (
            supabase.table("documents")
            .insert(
                {
                    "id": doc_id,
                    "user_id": user.id,
                    "filename": file.filename,
                    "file_size": len(content),
                    "mime_type": mime_type,
                    "status": "pending",
                    "storage_path": storage_path,
                }
            )
            .execute()
        )

    # Start background processing (record manager handles chunk dedup)
    background_tasks.add_task(process_document, doc_id, user.id, storage_path, file.filename, mime_type)

    return result.data[0]


@router.get("", response_model=list[DocumentResponse])
async def list_documents(user: User = Depends(get_current_user)):
    result = (
        supabase.table("documents")
        .select("*")
        .eq("user_id", user.id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    user: User = Depends(get_current_user),
):
    result = (
        supabase.table("documents")
        .select("*")
        .eq("id", document_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")
    return result.data[0]


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    user: User = Depends(get_current_user),
):
    # Fetch document to get storage path
    result = (
        supabase.table("documents")
        .select("*")
        .eq("id", document_id)
        .eq("user_id", user.id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = result.data[0]

    # Delete from storage
    if doc.get("storage_path"):
        try:
            supabase.storage.from_("documents").remove([doc["storage_path"]])
        except Exception:
            pass  # Storage deletion is best-effort

    # Delete document record (cascades to chunks)
    supabase.table("documents").delete().eq("id", document_id).eq("user_id", user.id).execute()
