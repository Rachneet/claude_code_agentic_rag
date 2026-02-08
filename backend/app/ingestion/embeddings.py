from huggingface_hub import InferenceClient
from langsmith import traceable

from app.config import settings

_embedding_client = InferenceClient(api_key=settings.hf_token)


@traceable(name="generate_embedding", run_type="embedding")
def generate_embedding(text: str) -> list[float]:
    """Generate embedding for a single text using HF Inference API."""
    result = _embedding_client.feature_extraction(
        text,
        model=settings.hf_embedding_model,
    )
    # feature_extraction returns a numpy array — convert to plain list of floats
    return [float(x) for x in result.flatten()]


@traceable(name="generate_embeddings_batch", run_type="embedding")
def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts."""
    results = []
    for text in texts:
        embedding = generate_embedding(text)
        results.append(embedding)
    return results
