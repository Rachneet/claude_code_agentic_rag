from __future__ import annotations

import logging

import httpx
from langsmith import traceable

from app.config import settings

logger = logging.getLogger(__name__)

_INFERENCE_URL = f"https://router.huggingface.co/hf-inference/models/{settings.reranker_model}"


@traceable(name="rerank_chunks")
def rerank_chunks(
    query: str,
    chunks: list[dict],
    top_k: int | None = None,
) -> list[dict]:
    """Rerank chunks using the HuggingFace Inference API cross-encoder.

    Calls the reranker model with the query and chunk texts, then returns
    chunks sorted by reranker score (descending). On any error, logs a
    warning and returns chunks in their original order.

    If reranking is disabled via settings, returns chunks unchanged.
    """
    if not settings.reranker_enabled:
        return chunks

    if not chunks:
        return chunks

    texts = [c.get("content", "") for c in chunks]

    try:
        response = httpx.post(
            _INFERENCE_URL,
            headers={"Authorization": f"Bearer {settings.hf_token}"},
            json={"query": query, "texts": texts, "truncate": True},
            timeout=30.0,
        )
        response.raise_for_status()
        scores = response.json()  # [{"index": int, "score": float}, ...]

        # Map scores back to chunks
        for item in scores:
            idx = item["index"]
            chunks[idx]["rerank_score"] = item["score"]

        # Sort by rerank_score descending
        ranked = sorted(chunks, key=lambda c: c.get("rerank_score", 0), reverse=True)

        if top_k is not None:
            ranked = ranked[:top_k]

        return ranked

    except Exception:
        logger.warning("Reranker failed, returning original order", exc_info=True)
        return chunks
