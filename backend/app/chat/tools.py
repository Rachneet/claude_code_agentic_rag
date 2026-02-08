from __future__ import annotations

import logging

from app.config import settings
from app.ingestion.retrieval import format_retrieval_context, search_documents

logger = logging.getLogger(__name__)

# --- Tool declarations (Gemini-compatible function declaration format) ---

SEARCH_DOCUMENTS_TOOL = {
    "name": "search_documents",
    "description": (
        "Search the user's uploaded documents for information relevant to their question. "
        "Use this tool when the user asks about topics that might be covered in their documents. "
        "You can optionally filter by document type or topic to narrow results."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to find relevant document chunks.",
            },
            "document_type": {
                "type": "string",
                "description": (
                    "Optional filter by document type. "
                    "One of: article, report, tutorial, notes, email, code, data, other."
                ),
            },
            "topic": {
                "type": "string",
                "description": "Optional filter by topic. Matches documents tagged with this topic.",
            },
            "search_strategy": {
                "type": "string",
                "description": "Search strategy: 'auto' (default), 'vector', or 'hybrid'.",
                "enum": ["auto", "vector", "hybrid"],
            },
        },
        "required": ["query"],
    },
}

WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": (
        "Search the web for current information. Use this when the user's question "
        "requires up-to-date information not likely found in their uploaded documents, "
        "such as recent news, current events, live data, or topics outside the documents' scope."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to find information on the web.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 5, max: 10).",
            },
        },
        "required": ["query"],
    },
}

CALCULATOR_TOOL = {
    "name": "calculate",
    "description": (
        "Evaluate a mathematical expression. Supports arithmetic (+, -, *, /, //, %, **), "
        "comparisons, and math functions (sqrt, log, log10, sin, cos, tan, ceil, floor, "
        "factorial, abs, round, min, max). Constants: pi, e. "
        "Use this for any calculations, unit conversions, or numeric analysis."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The mathematical expression to evaluate (e.g., 'sqrt(144) + 3 * pi').",
            },
        },
        "required": ["expression"],
    },
}

URL_FETCHER_TOOL = {
    "name": "fetch_url",
    "description": (
        "Fetch and read the content of a web page or URL. Use this when the user provides "
        "a specific URL they want you to read, summarize, or answer questions about. "
        "Returns the extracted text content of the page."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The full URL to fetch (must start with http:// or https://).",
            },
        },
        "required": ["url"],
    },
}

DATETIME_TOOL = {
    "name": "get_datetime",
    "description": (
        "Get the current date, time, and timestamp. Use this when the user asks about "
        "the current date or time, or needs time-related information for any timezone."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "timezone_name": {
                "type": "string",
                "description": (
                    "IANA timezone name (e.g., 'UTC', 'America/New_York', 'Europe/London', "
                    "'Asia/Tokyo'). Defaults to 'UTC'."
                ),
            },
        },
        "required": ["timezone_name"],
    },
}


def get_enabled_tools() -> list[dict]:
    """Build the tools list based on config flags.

    search_documents is always included (core RAG tool).
    Other tools are included only if their feature flag is enabled.
    """
    tools = [SEARCH_DOCUMENTS_TOOL]

    if settings.tools_web_search_enabled and settings.tavily_api_key:
        tools.append(WEB_SEARCH_TOOL)
    if settings.tools_calculator_enabled:
        tools.append(CALCULATOR_TOOL)
    if settings.tools_url_fetcher_enabled:
        tools.append(URL_FETCHER_TOOL)
    if settings.tools_datetime_enabled:
        tools.append(DATETIME_TOOL)

    return tools


# Backward-compatible module-level list
RAG_TOOLS = get_enabled_tools()


async def execute_tool(tool_name: str, args: dict, user_id: str) -> str:
    """Execute a tool call and return the result as a string."""
    try:
        if tool_name == "search_documents":
            query = args.get("query", "")

            metadata_filter: dict | None = None
            doc_type = args.get("document_type")
            topic = args.get("topic")

            if doc_type or topic:
                metadata_filter = {}
                if doc_type:
                    metadata_filter["document_type"] = doc_type
                if topic:
                    metadata_filter["topics"] = [topic]

            search_strategy = args.get("search_strategy", "auto")
            chunks = search_documents(
                query, user_id, metadata_filter=metadata_filter, search_strategy=search_strategy
            )
            if not chunks:
                return "No relevant documents found."
            return format_retrieval_context(chunks)

        elif tool_name == "web_search":
            from app.chat.web_search import web_search

            query = args.get("query", "")
            max_results = min(args.get("max_results", 5), 10)
            return await web_search(query, max_results=max_results)

        elif tool_name == "calculate":
            from app.chat.calculator import calculate

            expression = args.get("expression", "")
            return await calculate(expression)

        elif tool_name == "fetch_url":
            from app.chat.url_fetcher import fetch_url

            url = args.get("url", "")
            return await fetch_url(url)

        elif tool_name == "get_datetime":
            from app.chat.datetime_tool import get_datetime

            timezone_name = args.get("timezone_name", "UTC")
            return await get_datetime(timezone_name)

        else:
            return f"Unknown tool: {tool_name}"

    except Exception as e:
        logger.exception("Tool execution error (%s)", tool_name)
        return f"Tool error ({tool_name}): {e}"
