from __future__ import annotations

import json
import logging
import os
import re
from enum import Enum
from typing import Literal

from langsmith import traceable
from pydantic import BaseModel, Field

from app.llm.factory import get_provider

logger = logging.getLogger(__name__)


class DocumentMetadata(BaseModel):
    title: str = Field(description="Document title")
    document_type: Literal[
        "article", "report", "tutorial", "notes", "email", "code", "data", "other"
    ] = Field(description="Type of document")
    topics: list[str] = Field(
        description="3-5 main topics covered", min_length=1, max_length=5
    )
    entities: list[str] = Field(
        description="Key named entities (people, orgs, products, technologies)"
    )
    language: str = Field(description="ISO 639-1 language code (e.g. 'en')")
    summary: str = Field(description="2-3 sentence summary of the document")


EXTRACTION_SYSTEM_PROMPT = """You are a metadata extraction assistant. Analyze the provided document text and extract structured metadata.

Return ONLY a JSON object with these fields:
- "title": string — the document title (infer from content/filename if not explicit)
- "document_type": string — one of: "article", "report", "tutorial", "notes", "email", "code", "data", "other"
- "topics": array of strings — 3-5 main topics covered in the document
- "entities": array of strings — key named entities (people, organizations, products, technologies)
- "language": string — ISO 639-1 language code (e.g. "en", "de", "fr")
- "summary": string — 2-3 sentence summary of the document

Return ONLY valid JSON, no markdown formatting, no explanation."""


def _fallback_metadata(filename: str) -> DocumentMetadata:
    """Return minimal valid metadata when extraction fails."""
    name = os.path.splitext(filename)[0] if filename else "Untitled"
    return DocumentMetadata(
        title=name,
        document_type="other",
        topics=["general"],
        entities=[],
        language="en",
        summary=f"Document: {filename}",
    )


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences from LLM output."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


@traceable(name="extract_document_metadata", run_type="chain")
def extract_document_metadata(text: str, filename: str) -> DocumentMetadata:
    """Extract structured metadata from document text using LLM.

    Calls the configured LLM provider with the first 4000 chars of the document.
    Falls back to minimal metadata on any error.
    """
    try:
        # Use first 4000 chars to stay within context limits
        excerpt = text[:4000]

        messages = [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Filename: {filename}\n\nDocument text:\n{excerpt}",
            },
        ]

        provider = get_provider()
        raw = provider.chat_completion(
            messages, temperature=0.1, max_tokens=512
        )

        # Clean and parse
        cleaned = _strip_code_fences(raw)
        data = json.loads(cleaned)
        metadata = DocumentMetadata.model_validate(data)
        logger.info(f"Extracted metadata for '{filename}': type={metadata.document_type}, topics={metadata.topics}")
        return metadata

    except Exception:
        logger.exception(f"Metadata extraction failed for '{filename}', using fallback")
        return _fallback_metadata(filename)
