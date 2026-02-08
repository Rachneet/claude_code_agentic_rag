from __future__ import annotations

import logging

from langsmith import traceable

from app.config import settings
from app.llm.factory import get_provider

logger = logging.getLogger(__name__)

# Agent tool names — used by the recursion guard
AGENT_TOOL_NAMES = {"research_agent", "docqa_agent", "planner_agent"}


class BaseAgent:
    """Base class for sub-agents with a multi-turn ReAct loop.

    Subclasses define:
      - name: agent identifier
      - get_system_prompt(): instructions for the agent's behavior
      - get_tools(): list of tool declarations the agent can use
    """

    name: str = "base_agent"
    max_iterations: int | None = None  # None = use settings default

    def get_system_prompt(self) -> str:
        raise NotImplementedError

    def get_tools(self) -> list[dict]:
        raise NotImplementedError

    @traceable(name="agent_run", run_type="chain")
    async def run(self, task: str, user_id: str) -> str:
        """Execute the agent's ReAct loop.

        Args:
            task: The task/query from the outer LLM.
            user_id: For scoping search_documents to user's docs.

        Returns:
            Final answer string.
        """
        from app.chat.tools import execute_tool_for_agent

        provider = get_provider()
        max_iter = self.max_iterations or settings.agent_max_iterations
        tools = self.get_tools()

        messages: list[dict] = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": task},
        ]

        for iteration in range(max_iter):
            logger.info("[%s] iteration %d/%d", self.name, iteration + 1, max_iter)

            response = provider.chat_completion_with_tools(
                messages=messages,
                tools=tools,
                max_tokens=settings.agent_max_tokens,
                temperature=0.3,
            )

            # If LLM returned content (no tool calls), we're done
            if response.get("content") and not response.get("tool_calls"):
                return response["content"]

            # If no tool calls AND no content, something went wrong
            if not response.get("tool_calls"):
                return "Agent could not generate a response."

            # Execute all tool calls
            tool_results = []
            for tc in response["tool_calls"]:
                logger.info("[%s] calling tool=%s", self.name, tc["name"])
                result = await execute_tool_for_agent(tc["name"], tc["args"], user_id)
                tool_results.append({"name": tc["name"], "result": result})

            # Format and append to conversation
            new_messages = provider.format_tool_messages(response, tool_results)
            messages.extend(new_messages)

        # Max iterations reached — ask LLM for a final answer without tools
        messages.append(
            {
                "role": "user",
                "content": (
                    "You have reached the maximum number of steps. "
                    "Please provide your best answer now based on what you have gathered so far."
                ),
            }
        )
        return provider.chat_completion(
            messages, max_tokens=settings.agent_max_tokens, temperature=0.3
        )
