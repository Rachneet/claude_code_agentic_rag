from __future__ import annotations

from app.agents.base import BaseAgent
from app.chat.tools import (
    CALCULATOR_TOOL,
    SEARCH_DOCUMENTS_TOOL,
    URL_FETCHER_TOOL,
    WEB_SEARCH_TOOL,
)
from app.config import settings


class ResearchAgent(BaseAgent):
    name = "research_agent"

    def get_system_prompt(self) -> str:
        return (
            "You are a Research Agent. Your task is to thoroughly research a question "
            "by searching through the user's documents and the web.\n\n"
            "Strategy:\n"
            "1. Break the question into sub-queries if it is complex\n"
            "2. Search the user's documents first for relevant information\n"
            "3. Search the web for additional context, recent data, or missing information\n"
            "4. Fetch specific URLs if search results point to useful pages\n"
            "5. Use the calculator for any numeric analysis\n"
            "6. Synthesize ALL findings into a comprehensive, well-structured answer\n\n"
            "Important:\n"
            "- Always cite your sources (document titles, URLs)\n"
            "- If documents and web sources conflict, note the discrepancy\n"
            "- Provide a thorough answer — you are the expert researcher\n"
            "- Do not use <think> tags or show your reasoning process"
        )

    def get_tools(self) -> list[dict]:
        tools = [SEARCH_DOCUMENTS_TOOL]
        if settings.tools_web_search_enabled and settings.tavily_api_key:
            tools.append(WEB_SEARCH_TOOL)
        if settings.tools_url_fetcher_enabled:
            tools.append(URL_FETCHER_TOOL)
        if settings.tools_calculator_enabled:
            tools.append(CALCULATOR_TOOL)
        return tools
