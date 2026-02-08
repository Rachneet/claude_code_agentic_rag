import re

from pydantic import BaseModel


class TextChunk(BaseModel):
    content: str
    chunk_index: int
    token_count: int
    metadata: dict = {}


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token for English)."""
    return max(1, len(text) // 4)


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> list[TextChunk]:
    """Split text into overlapping chunks with sentence boundary awareness.

    Uses character-based chunking, splitting at sentence boundaries
    (`. `, `! `, `? `, `\\n\\n`) when possible.
    """
    if not text.strip():
        return []

    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+|\n\n+', text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks = []
    current_chunk = ""
    chunk_index = 0

    for sentence in sentences:
        # If adding this sentence would exceed chunk_size
        if current_chunk and len(current_chunk) + len(sentence) + 1 > chunk_size:
            chunks.append(
                TextChunk(
                    content=current_chunk.strip(),
                    chunk_index=chunk_index,
                    token_count=_estimate_tokens(current_chunk.strip()),
                )
            )
            chunk_index += 1

            # Overlap: keep the tail of the current chunk
            if chunk_overlap > 0 and len(current_chunk) > chunk_overlap:
                current_chunk = current_chunk[-chunk_overlap:]
            else:
                current_chunk = ""

        if current_chunk:
            current_chunk += " " + sentence
        else:
            current_chunk = sentence

        # Handle very long sentences that exceed chunk_size on their own
        while len(current_chunk) > chunk_size:
            split_point = chunk_size
            chunks.append(
                TextChunk(
                    content=current_chunk[:split_point].strip(),
                    chunk_index=chunk_index,
                    token_count=_estimate_tokens(current_chunk[:split_point].strip()),
                )
            )
            chunk_index += 1
            current_chunk = current_chunk[split_point - chunk_overlap:] if chunk_overlap > 0 else current_chunk[split_point:]

    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append(
            TextChunk(
                content=current_chunk.strip(),
                chunk_index=chunk_index,
                token_count=_estimate_tokens(current_chunk.strip()),
            )
        )

    return chunks
