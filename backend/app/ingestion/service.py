from __future__ import annotations

import logging

from langsmith import traceable

from app.db.supabase import supabase
from app.ingestion.chunking import chunk_text
from app.ingestion.extractors import extract_text
from app.ingestion.embeddings import generate_embeddings_batch
from app.ingestion.metadata import extract_document_metadata
from app.ingestion.record_manager import (
    apply_reconciliation,
    compute_content_hash,
    fetch_existing_chunks,
    reconcile_chunks,
)

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/html",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def update_document_status(
    doc_id: str, status: str, error_message: str | None = None, chunk_count: int | None = None
):
    """Update document status (triggers Supabase Realtime)."""
    update_data: dict = {"status": status}
    if error_message is not None:
        update_data["error_message"] = error_message
    if chunk_count is not None:
        update_data["chunk_count"] = chunk_count

    supabase.table("documents").update(update_data).eq("id", doc_id).execute()


@traceable(name="process_document", run_type="chain")
def process_document(doc_id: str, user_id: str, storage_path: str, filename: str = "", mime_type: str = "text/plain"):
    """Background task: download file -> chunk -> embed -> store in pgvector -> update status."""
    try:
        # 1. Extract text from file
        update_document_status(doc_id, "extracting")

        # 2. Download file from Supabase Storage
        file_bytes = supabase.storage.from_("documents").download(storage_path)
        text = extract_text(file_bytes, mime_type, filename)

        # 3. Chunk the text
        update_document_status(doc_id, "chunking")
        chunks = chunk_text(text)
        if not chunks:
            update_document_status(doc_id, "failed", error_message="No chunks generated")
            return

        # 3b. Extract document-level metadata via LLM
        doc_metadata = extract_document_metadata(text, filename)
        metadata_dict = doc_metadata.model_dump()

        # Store metadata on the documents row
        supabase.table("documents").update({"metadata": metadata_dict}).eq("id", doc_id).execute()

        # Propagate subset of metadata to each chunk
        chunk_metadata = {
            "document_type": metadata_dict["document_type"],
            "topics": metadata_dict["topics"],
            "title": metadata_dict["title"],
            "language": metadata_dict["language"],
        }

        # 4. Embed and store
        update_document_status(doc_id, "embedding")

        # 4a. Compute content hashes and check against existing chunks
        new_chunks = [
            {
                "content": c.content,
                "chunk_index": c.chunk_index,
                "token_count": c.token_count,
                "metadata": chunk_metadata,
                "content_hash": compute_content_hash(c.content),
            }
            for c in chunks
        ]

        existing = fetch_existing_chunks(doc_id)
        existing_hashes = {c["content_hash"] for c in existing}

        # 5. Only generate embeddings for truly new chunks (key optimization)
        new_only = [c for c in new_chunks if c["content_hash"] not in existing_hashes]

        if new_only:
            embeddings = generate_embeddings_batch([c["content"] for c in new_only])
        else:
            embeddings = []

        # 6. Reconcile: insert new, delete stale, skip unchanged
        reconciliation = reconcile_chunks(doc_id, user_id, new_chunks, embeddings)
        summary = apply_reconciliation(reconciliation)

        # Final chunk count = existing - deleted + inserted
        final_count = len(existing) - summary["deleted"] + summary["inserted"]
        update_document_status(doc_id, "completed", chunk_count=final_count)
        logger.info(
            f"Document {doc_id} processed: {summary['inserted']} inserted, "
            f"{summary['deleted']} deleted, {summary['skipped']} skipped"
        )

    except Exception as e:
        logger.exception(f"Failed to process document {doc_id}")
        update_document_status(doc_id, "failed", error_message=str(e)[:500])
