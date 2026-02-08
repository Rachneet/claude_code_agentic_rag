from __future__ import annotations

import logging

import httpx
from langsmith import traceable

from app.config import settings

logger = logging.getLogger(__name__)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


@traceable(name="web_search", run_type="tool")
async def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using Tavily and return formatted results.

    Returns a formatted string of search results with titles, URLs,
    and content snippets. On any error, returns an error message string.
    """
    if not settings.tavily_api_key:
        return "Web search is not configured. Please set TAVILY_API_KEY."

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                TAVILY_SEARCH_URL,
                json={
                    "api_key": settings.tavily_api_key,
                    "query": query,
                    "max_results": max_results,
                    "include_answer": True,
                    "search_depth": "basic",
                },
            )
            response.raise_for_status()
            data = response.json()

        parts = []

        answer = data.get("answer")
        if answer:
            parts.append(f"Summary: {answer}")

        results = data.get("results", [])
        if not results and not answer:
            return "No web search results found."

        for i, result in enumerate(results, 1):
            title = result.get("title", "Untitled")
            url = result.get("url", "")
            content = result.get("content", "")
            parts.append(f"[{i}] {title}\n    URL: {url}\n    {content}")

        return "\n\n".join(parts)

    except httpx.HTTPStatusError as e:
        logger.warning("Tavily API error: %s", e.response.status_code)
        return f"Web search failed: HTTP {e.response.status_code}"
    except Exception:
        logger.warning("Web search error", exc_info=True)
        return "Web search failed due to an unexpected error."
