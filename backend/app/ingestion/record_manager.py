from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field

from langsmith import traceable

from app.db.supabase import supabase

logger = logging.getLogger(__name__)


def compute_content_hash(content: str) -> str:
    """SHA-256 hex digest of chunk content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@dataclass
class ReconciliationResult:
    document_id: str
    user_id: str
    to_insert: list[dict] = field(default_factory=list)
    to_delete: list[str] = field(default_factory=list)  # chunk IDs to delete
    skipped: int = 0


@traceable(name="fetch_existing_chunks", run_type="chain")
def fetch_existing_chunks(document_id: str) -> list[dict]:
    """Fetch id, chunk_index, content_hash for all existing chunks of a document."""
    result = (
        supabase.table("document_chunks")
        .select("id, chunk_index, content_hash")
        .eq("document_id", document_id)
        .execute()
    )
    return result.data


@traceable(name="reconcile_chunks", run_type="chain")
def reconcile_chunks(
    document_id: str,
    user_id: str,
    new_chunks: list[dict],
    embeddings: list[list[float]],
) -> ReconciliationResult:
    """Compare new chunk hashes against existing ones. Returns what to insert/delete.

    Args:
        document_id: The document being processed.
        user_id: Owner of the document.
        new_chunks: List of dicts with content, chunk_index, token_count, metadata, content_hash.
        embeddings: Embeddings corresponding only to chunks that need embedding
                    (ordered to match the new chunks that are NOT skipped).
    """
    existing = fetch_existing_chunks(document_id)
    existing_by_hash: dict[str, dict] = {c["content_hash"]: c for c in existing}

    result = ReconciliationResult(document_id=document_id, user_id=user_id)
    matched_hashes: set[str] = set()
    embedding_idx = 0

    for chunk in new_chunks:
        h = chunk["content_hash"]
        if h in existing_by_hash:
            result.skipped += 1
            matched_hashes.add(h)
        else:
            record = {
                "document_id": document_id,
                "user_id": user_id,
                "content": chunk["content"],
                "chunk_index": chunk["chunk_index"],
                "embedding": embeddings[embedding_idx],
                "token_count": chunk["token_count"],
                "metadata": chunk["metadata"],
                "content_hash": h,
            }
            result.to_insert.append(record)
            embedding_idx += 1

    # Existing hashes not matched by any new chunk are stale
    for h, chunk_record in existing_by_hash.items():
        if h not in matched_hashes:
            result.to_delete.append(chunk_record["id"])

    logger.info(
        f"Reconciliation for {document_id}: "
        f"{len(result.to_insert)} insert, {len(result.to_delete)} delete, {result.skipped} skip"
    )
    return result


@traceable(name="apply_reconciliation", run_type="chain")
def apply_reconciliation(result: ReconciliationResult) -> dict:
    """Execute DB inserts and deletes from reconciliation result."""
    # Delete stale chunks
    if result.to_delete:
        supabase.table("document_chunks").delete().in_("id", result.to_delete).execute()
        logger.info(f"Deleted {len(result.to_delete)} stale chunks for {result.document_id}")

    # Insert new chunks in batches of 50
    inserted = 0
    batch_size = 50
    for i in range(0, len(result.to_insert), batch_size):
        batch = result.to_insert[i : i + batch_size]
        supabase.table("document_chunks").insert(batch).execute()
        inserted += len(batch)

    return {
        "inserted": inserted,
        "deleted": len(result.to_delete),
        "skipped": result.skipped,
    }
