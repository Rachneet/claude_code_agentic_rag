from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from langsmith import traceable

from app.config import settings
from app.db.supabase import supabase
from app.ingestion.embeddings import generate_embedding
from app.ingestion.reranker import rerank_chunks

logger = logging.getLogger(__name__)


@traceable(name="vector_search", run_type="retriever")
def _vector_search(
    query: str,
    user_id: str,
    threshold: float = 0.3,
    count: int = 5,
    metadata_filter: dict | None = None,
) -> list[dict]:
    """Semantic similarity search via pgvector."""
    query_embedding = generate_embedding(query)

    rpc_params = {
        "query_embedding": query_embedding,
        "match_user_id": user_id,
        "match_threshold": threshold,
        "match_count": count,
        "metadata_filter": metadata_filter,
    }

    result = supabase.rpc("match_document_chunks", rpc_params).execute()
    return result.data or []


@traceable(name="fulltext_search", run_type="retriever")
def _fulltext_search(
    query: str,
    user_id: str,
    count: int = 5,
    metadata_filter: dict | None = None,
) -> list[dict]:
    """Full-text search via PostgreSQL tsvector."""
    rpc_params = {
        "query_text": query,
        "match_user_id": user_id,
        "match_count": count,
        "metadata_filter": metadata_filter,
    }

    result = supabase.rpc("match_document_chunks_fts", rpc_params).execute()
    return result.data or []


def _reciprocal_rank_fusion(result_lists: list[list[dict]], k: int = 60) -> list[dict]:
    """Merge multiple ranked lists using Reciprocal Rank Fusion.

    score(d) = sum(1 / (k + rank_i)) for each list where d appears.
    Deduplicates by chunk id.
    """
    scores: dict[str, float] = {}
    chunk_map: dict[str, dict] = {}

    for result_list in result_lists:
        for rank, chunk in enumerate(result_list):
            chunk_id = chunk["id"]
            scores[chunk_id] = scores.get(chunk_id, 0) + 1.0 / (k + rank + 1)
            if chunk_id not in chunk_map:
                chunk_map[chunk_id] = chunk

    # Attach RRF score and sort descending
    fused = []
    for chunk_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        chunk = chunk_map[chunk_id]
        chunk["rrf_score"] = score
        fused.append(chunk)

    return fused


@traceable(name="search_documents", run_type="retriever")
def search_documents(
    query: str,
    user_id: str,
    threshold: float = 0.3,
    count: int = 5,
    metadata_filter: dict | None = None,
    search_strategy: str = "auto",
) -> list[dict]:
    """Search documents using vector, full-text, or hybrid strategy.

    Args:
        query: Search query text.
        user_id: User ID for RLS filtering.
        threshold: Minimum similarity threshold (vector search only).
        count: Number of results to return.
        metadata_filter: Optional jsonb containment filter.
        search_strategy: "auto" (uses config), "vector", or "hybrid".
    """
    use_hybrid = search_strategy == "hybrid" or (
        search_strategy == "auto" and settings.hybrid_search_enabled
    )

    if use_hybrid:
        # Fetch extra candidates from each source for better fusion/reranking
        fetch_count = count * 2

        with ThreadPoolExecutor(max_workers=2) as executor:
            vector_future = executor.submit(
                _vector_search, query, user_id, threshold, fetch_count, metadata_filter
            )
            fts_future = executor.submit(
                _fulltext_search, query, user_id, fetch_count, metadata_filter
            )

            vector_results = vector_future.result()
            fts_results = fts_future.result()

        # Fuse with RRF
        chunks = _reciprocal_rank_fusion([vector_results, fts_results])
    else:
        # Vector-only (pre-Module 7 behavior)
        chunks = _vector_search(query, user_id, threshold, count, metadata_filter)

    # Rerank top candidates (no-op if reranker is disabled)
    chunks = rerank_chunks(query, chunks, top_k=count)

    # If reranker was disabled and we fetched extra for hybrid, trim to count
    if len(chunks) > count:
        chunks = chunks[:count]

    return chunks


def format_retrieval_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a context string for the LLM."""
    if not chunks:
        return ""

    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        # Prefer rerank_score > rrf_score > similarity for display
        score = (
            chunk.get("rerank_score")
            or chunk.get("rrf_score")
            or chunk.get("similarity", 0)
        )
        content = chunk.get("content", "")
        metadata = chunk.get("metadata", {}) or {}
        title = metadata.get("title", "")
        doc_type = metadata.get("document_type", "")

        label = f"Source {i}"
        if title:
            label += f" — {title}"
        if doc_type:
            label += f" [{doc_type}]"

        context_parts.append(f"[{label} (relevance: {score:.2f})]\n{content}")

    return "\n\n---\n\n".join(context_parts)
