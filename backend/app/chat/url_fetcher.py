from __future__ import annotations

import logging
import re

import httpx
from bs4 import BeautifulSoup
from langsmith import traceable

from app.config import settings

logger = logging.getLogger(__name__)


@traceable(name="fetch_url", run_type="tool")
async def fetch_url(url: str) -> str:
    """Fetch a URL and extract its readable text content.

    Strips scripts, styles, nav, headers, footers. Returns plain text
    truncated to settings.url_fetcher_max_chars. On error, returns an
    error message string.
    """
    try:
        async with httpx.AsyncClient(
            timeout=settings.url_fetcher_timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; RAGBot/1.0)",
                "Accept": "text/html,application/xhtml+xml,text/plain,application/json",
            },
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "")

        # Handle plain text / JSON directly
        if "text/plain" in content_type or "application/json" in content_type:
            text = response.text[: settings.url_fetcher_max_chars]
            return f"Content from {url}:\n\n{text}"

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove non-content elements
        for tag in soup.find_all(
            ["script", "style", "nav", "footer", "header", "aside", "iframe"]
        ):
            tag.decompose()

        # Extract text
        text = soup.get_text(separator="\n", strip=True)

        # Collapse excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Truncate
        if len(text) > settings.url_fetcher_max_chars:
            text = text[: settings.url_fetcher_max_chars] + "\n\n[Content truncated]"

        if not text.strip():
            return f"No readable text content found at {url}"

        # Extract page title if available
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        header = f"Content from {url}"
        if title:
            header += f" ({title})"

        return f"{header}:\n\n{text}"

    except httpx.HTTPStatusError as e:
        return f"Failed to fetch URL: HTTP {e.response.status_code}"
    except httpx.TimeoutException:
        return f"Failed to fetch URL: request timed out after {settings.url_fetcher_timeout}s"
    except httpx.InvalidURL:
        return f"Invalid URL: {url}"
    except Exception:
        logger.warning("URL fetch error for %s", url, exc_info=True)
        return f"Failed to fetch URL: unexpected error."
